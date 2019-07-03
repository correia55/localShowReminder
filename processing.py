from enum import Enum

import urllib.request
import urllib.error
import urllib.parse
import json
import datetime
import re

import flask_bcrypt as fb
from sqlalchemy.exc import IntegrityError

import configuration


class ReminderType(Enum):
    DB = 0
    IMDB = 1


class ComparisonType(Enum):
    EQUALS = 0
    BIGGER = 1
    SMALLER = 2


def list_to_json(list_of_objects):
    """Create a list with the result of to_dict for each element."""

    result = []

    for o in list_of_objects:
        result.append(o.to_dict())

    return result


def get_channel_list(ignore_hd=True):
    """
    Make a request for the channel list and add them to the db.

    :param ignore_hd: true when we're supposed to ignore HD channels.
    """

    print('Get channel list!')

    # Request the list of channels
    channels_json = urllib.request.urlopen(
        'https://tvnetvoz.vodafone.pt/sempre-consigo/datajson/epg/channels.jsp').read()

    # Parse the list of channels from the request
    channels = json.loads(channels_json)['result']['channels']

    # Add the list of channels to the database
    for c in channels:
        if not ignore_hd or 'HD' not in c['name']:
            channel = configuration.models.Channel(c['id'], c['name'].strip())

            configuration.session.add(channel)

    configuration.session.commit()


def clear_show_list():
    """Delete entries with more than 7 days old, from the DB."""

    print('Clear show list!')

    today_start = datetime.datetime.now()
    today_start.replace(hour=0, minute=0, second=0)

    configuration.session.query(configuration.models.Show).filter(
        configuration.models.Show.date_time < today_start - datetime.timedelta(7)).delete()
    configuration.session.commit()


def update_show_list():
    """Make a request for the show list and update the DB."""

    print('Updating show list...')

    # Get list of all channels from the db
    db_channels = configuration.session.query(configuration.models.Channel).all()

    # If the list of channels in the db is empty
    if not db_channels:
        get_channel_list()

        db_channels = configuration.session.query(configuration.models.Channel).all()

    # Get the date of the last update
    db_last_update = configuration.session.query(configuration.models.LastUpdate).first()

    # If this is the first update set yesterday's date as the last update
    if db_last_update is None:
        db_last_update = configuration.models.LastUpdate(datetime.date.today() - datetime.timedelta(1))

        configuration.session.add(db_last_update)

    # For each day until six days from today
    while db_last_update.date < datetime.date.today() + datetime.timedelta(6):
        db_last_update.date += datetime.timedelta(1)

        # Create the shows' info request url
        shows_url = 'https://tvnetvoz.vodafone.pt/sempre-consigo/epg.do?action=getPrograms&chanids='

        first = True

        for c in db_channels:
            if first:
                first = False
                shows_url += str(c.pid)
            else:
                shows_url += ',' + str(c.pid)

        shows_url += '&day=' + db_last_update.date.strftime('%Y-%m-%d')

        print(shows_url)

        # Get the shows info for our list of channels
        shows_json = urllib.request.urlopen(shows_url).read()

        # Parse the list of channels from the request
        channels = json.loads(shows_json)['result']['channels']

        for c in channels:
            channel_shows = c['programList']
            channel_id = configuration.session.query(configuration.models.Channel).filter(
                configuration.models.Channel.pid == c['id']).first().id

            for s in channel_shows:
                program_title = s['programTitle']
                pos = program_title.find(':T')

                # If it's referent to a show from a different day
                if s['date'] != db_last_update.date.strftime('%d-%m-%Y'):
                    continue

                # If it is an episode of a series
                if pos != -1:
                    show_title = program_title[:pos]
                    show_rem = program_title[pos + 2:].split()

                    show_season = int(show_rem[0])

                    # Some shows seem to be missing the episode info
                    try:
                        show_episode = int(show_rem[1][3:])
                    except:
                        print(program_title)
                        show_episode = 0
                else:
                    show_title = program_title
                    show_season = 0
                    show_episode = 0

                show_datetime = db_last_update.date.strftime('%Y-%m-%d ') + s['startTime']

                # Remove the last character in order to find the results for both SD and HD
                if s['serid'] is not None:
                    series_id = s['serid'][:-1]
                else:
                    series_id = None

                # Remove the first character in order to find the results for both SD and HD
                pid = s['pid'][1:]

                # Add the show to the db
                show = configuration.models.Show(pid, series_id, show_title, show_season, show_episode,
                                                 s['programDetails'], show_datetime, s['duration'], channel_id)

                configuration.session.add(show)

        configuration.session.commit()

    print('Update show lists is complete!')


def search_show_information_by_type(search_text, show_type):
    """
    Uses trakt and omdb to search for shows, of a given type, using a given search text.

    :param search_text: the search text introduced by the user.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :return: the list of results.
    """

    results = []

    # Make the request
    shows_request = urllib.request.Request(
        'https://api.trakt.tv/search/%s?query=%s' % (show_type, urllib.parse.quote(search_text)))
    shows_request.add_header('trakt-api-key', configuration.trakt_key)

    shows_json = urllib.request.urlopen(shows_request).read()

    # Parse the list of shows from the request
    shows = json.loads(shows_json)

    is_show = show_type == 'show'

    for s in shows:
        imdb_id = s[show_type]['ids']['imdb']

        show_dict = {'is_show': is_show, 'show_title': s[show_type]['title'], 'show_year': s[show_type]['year'],
                     'show_image': 'N/A', 'show_slug': s[show_type]['ids']['slug']}

        if imdb_id is None or configuration.omdb_key is None:
            results.append(show_dict)
            continue

        show_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=%s&i=%s' % (configuration.omdb_key, s[show_type]['ids']['imdb'])).read()

        # Parse the show from the request
        show = json.loads(show_json)

        # When the omdb can't find the information
        if show['Response']:
            results.append(show_dict)
            continue

        show_dict['show_image'] = show['Poster']

        results.append(show_dict)

    return results


def search_show_information(search_text):
    """
    Uses trakt and omdb to search for shows using a given search text.

    :param search_text: the search text introduced by the user.
    :return: the list of results.
    """

    results = search_show_information_by_type(search_text, 'show')
    results += search_show_information_by_type(search_text, 'movie')

    return results


def get_titles(trakt_slug, show_type):
    """
    Get the various possible titles for the selected title, in both english and portuguese.

    :param trakt_slug: the selected title.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :return: the various possible titles.
    """

    translations_request = urllib.request.Request('https://api.trakt.tv/%ss/%s/translations' % (show_type, trakt_slug))
    translations_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        translations_json = urllib.request.urlopen(translations_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return []

    # Parse the list of translations from the request
    translations = json.loads(translations_json)

    results = set()

    for t in translations:
        if t['language'] == 'en' or t['language'] == 'pt':
            results.add(t['title'])

    aliases_request = urllib.request.Request('https://api.trakt.tv/%ss/%s/aliases' % (show_type, trakt_slug))
    aliases_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        aliases_json = urllib.request.urlopen(aliases_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return []

    # Parse the list of aliases from the request
    aliases = json.loads(aliases_json)

    for t in aliases:
        if t['country'] == 'us' or t['country'] == 'pt':
            results.add(t['title'])

    return results


def search_db(search_list, only_between=True, below_date=None, show_season=None, show_episode=None,
              comparison_type=None):
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param search_list: the list of texts to search for in the DB.
    :param only_between: true when other characters can only be between words.
    :param below_date: a date below to limit the search.
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param comparison_type: to specify a means of comparison.
    :return: results of the search in the DB.
    """

    results = set()

    for search_text in search_list:
        print('Original search text: %s' % search_text)

        # Split the search text into a list of words
        search_words = re.compile('[^0-9A-Za-zÀ-ÿ.]+').split(search_text)

        print('List of words obtained from the search text: %s' % str(search_words))

        # Create a search pattern to search the DB
        search_pattern = ''

        for w in search_words:
            if w != '':
                if search_pattern == '' and only_between:
                    search_pattern += '%s' % w
                else:
                    search_pattern += '%%%s' % w

        if only_between:
            search_pattern = '%s' % search_pattern
        else:
            search_pattern = '%s%%' % search_pattern

        print('Search pattern: %s' % search_pattern)

        query = configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.show_title.ilike(search_pattern))

        if show_season is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(configuration.models.Show.show_season == show_season)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(configuration.models.Show.show_season > show_season)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(configuration.models.Show.show_season < show_season)

        if show_episode is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(configuration.models.Show.show_episode == show_episode)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(configuration.models.Show.show_episode > show_episode)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(configuration.models.Show.show_episode < show_episode)

        if below_date is not None:
            query = query.filter(configuration.models.Show.date_time > below_date)

        db_shows = query.all()

        for s in db_shows:
            results.add(s)

    return results


def get_corresponding_id(imdb_id):
    """
    Get the DB id corresponding to the imdb id.

    :param imdb_id: the imdb id.
    :return: the corresponding DB id.
    """

    show_match = configuration.session.query(configuration.models.ShowMatch).filter(
        configuration.models.ShowMatch.imdb_id == imdb_id).first()

    return show_match.show_id


def search_db_id(show_id, is_show, below_date=None, show_season=None, show_episode=None, comparison_type=None):
    """
    Get the results of the search in the DB, using show id (either series_id or pid).

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param below_date: a date below to limit the search.
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param comparison_type: to specify a means of comparison.
    :return: results of the search in the DB.
    """

    if is_show:
        query = configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.series_id == show_id)

        if show_season is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(configuration.models.Show.show_season == show_season)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(configuration.models.Show.show_season > show_season)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(configuration.models.Show.show_season < show_season)

        if show_episode is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(configuration.models.Show.show_episode == show_episode)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(configuration.models.Show.show_episode > show_episode)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(configuration.models.Show.show_episode < show_episode)
    else:
        query = configuration.session.query(configuration.models.Show).filter(
            configuration.models.Show.pid == show_id)

    if below_date is not None:
        query = query.filter(configuration.models.Show.date_time > below_date)

    return query.all()


def register_reminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type):
    """
    Create a reminder for the given data.

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param reminder_type: 0 if it's a DB and 1 otherwise.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param comparison_type: type of comparison for the reminder.
    """

    configuration.session.add(
        configuration.models.ShowReminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type))

    configuration.session.commit()


def remove_reminder(reminder_id):
    """
    Delete an id, if the request was sent by the owner.

    :param reminder_id: the id of the reminder.
    """

    reminder = configuration.session.query(configuration.models.ShowReminder).filter(
        configuration.models.ShowReminder.id == reminder_id).first()
    configuration.session.delete(reminder)

    configuration.session.commit()


def process_reminders(last_date):
    """
    Process the reminders that exist in the DB.

    :param last_date: the date of the last update.
    """

    reminders = configuration.session.query(configuration.models.ShowReminder).all()

    for r in reminders:
        if r.reminder_type == ReminderType.DB:
            db_shows = search_db_id(r.show_id, r.is_show, last_date, r.show_season, r.show_episode, r.comparison_type)
        else:
            db_id = get_corresponding_id(r.show_id)

            if db_id is not None:
                db_shows = search_db_id(db_id, r.is_show, last_date, r.show_season, r.show_episode, r.comparison_type)
            else:
                if r.is_show:
                    show_type = 'show'
                else:
                    show_type = 'movie'

                titles = get_titles(r.show_id, show_type)

                db_shows = search_db(titles, True, last_date, r.show_season, r.show_episode, r.comparison_type)

        # TODO: Send notification with shows found
        print('Number of shows: %d' % len(db_shows))

        for s in db_shows:
            print(s)


def get_last_update():
    """Get the date of the last update."""

    return configuration.session.query(configuration.models.LastUpdate).first().date


def register_user(email, password):
    """
    Register a new user.

    :param email: the user's email.
    :param password: the user's password.
    """

    password = fb.generate_password_hash(password, configuration.bcrypt_rounds).decode()

    try:
        configuration.session.add(configuration.models.User(email, password))
        configuration.session.commit()
        # TODO: Send registration email
    except IntegrityError:
        pass
        # TODO: Send warning email


def check_login(email, password):
    """
    Login with the user's credentials.

    :param email: the user's email.
    :param password: the user's password.
    """

    user = configuration.session.query(configuration.models.User).filter(
        configuration.models.User.email == email).first()

    if user is None:
        user_password = None
    else:
        user_password = user.password

    try:
        valid = fb.check_password_hash(user_password, password)
    except TypeError:
        valid = False

    return valid


def main():
    process_reminders(datetime.date.today() - datetime.timedelta(5))


if __name__ == '__main__':
    main()
