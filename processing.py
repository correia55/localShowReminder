from enum import Enum
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import urllib.request
import urllib.error
import urllib.parse
import json
import datetime
import re
import flask_bcrypt as fb

import models
import configuration
import auxiliary
from response_models import ShowReminder


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


def clear_show_list():
    """Delete entries with more than 7 days old, from the DB."""

    print('Clear show list!')

    today_start = datetime.datetime.now()
    today_start.replace(hour=0, minute=0, second=0)

    configuration.session.query(models.Show).filter(
        models.Show.date_time < today_start - datetime.timedelta(7)).delete()
    configuration.session.commit()


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
        'https://api.trakt.tv/search/%s?extended=full&query=%s' % (show_type, urllib.parse.quote(search_text)))
    shows_request.add_header('trakt-api-key', configuration.trakt_key)

    shows_json = urllib.request.urlopen(shows_request).read()

    # Parse the list of shows from the request
    shows = json.loads(shows_json)

    is_show = show_type == 'show'

    for s in shows:
        imdb_id = s[show_type]['ids']['imdb']

        show_dict = {'is_show': is_show, 'show_title': s[show_type]['title'], 'show_year': s[show_type]['year'],
                     'show_image': 'N/A', 'show_slug': s[show_type]['ids']['slug'],
                     'show_overview': s[show_type]['overview']}

        if imdb_id is None or configuration.omdb_key is None:
            results.append(show_dict)
            continue

        show_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=%s&i=%s' % (configuration.omdb_key, s[show_type]['ids']['imdb'])).read()

        # Parse the show from the request
        show = json.loads(show_json)

        # When the omdb can't find the information
        if not show['Response']:
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


def get_titles_trakt(trakt_slug, show_type):
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the trakt API.

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


def get_titles_db(trakt_slug):
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the DB.

    :param trakt_slug: the selected title.
    :return: the various possible titles.
    """

    return configuration.session.query(models.TraktTitle).filter(models.TraktTitle.trakt_id == trakt_slug).all()


def search_db(search_list, complete_title=False, below_date=None, show_season=None, show_episode=None,
              search_adult=False):
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param search_list: the list of texts to search for in the DB.
    :param complete_title: true when we don't want to accept any other words.
    :param below_date: a date below to limit the search.
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :return: results of the search in the DB.
    """

    results = dict()

    for search_text in search_list:
        print('Original search text: %s' % search_text)

        unaccented_text = auxiliary.strip_accents(search_text)

        # Split the search text into a list of words
        search_words = re.compile('[^0-9A-Za-z]+').split(unaccented_text)

        print('List of words obtained from the search text: %s' % str(search_words))

        # Create a search pattern to search the DB
        search_pattern = '' if complete_title else '.*'

        for w in search_words:
            if w != '':
                search_pattern += '_%ss?' % w

        if complete_title:
            search_pattern += '_'
        else:
            search_pattern += '_.*'

        print('Search pattern: %s' % search_pattern)

        query = configuration.session.query(models.Show, models.Channel.name) \
            .filter(models.Show.search_title.op('~*')(search_pattern))

        if show_season is not None:
            query = query.filter(models.Show.show_season == show_season)

        if show_episode is not None:
            query = query.filter(models.Show.show_episode == show_episode)

        if not search_adult:
            query = query.filter(models.Channel.adult is not True)

        if below_date is not None:
            query = query.filter(models.Show.date_time > below_date)

        # Filter the channels
        query = query.join(models.Channel)

        db_shows = query.all()

        for s in db_shows:
            show = s[0].to_dict()
            show['channel'] = s[1]

            results[show['id']] = show

    # Create a list from the dictionary of results
    final_results = []

    for r in results.values():
        final_results.append(r)

    return final_results


def get_corresponding_id(imdb_id):
    """
    Get the DB id corresponding to the imdb id.

    :param imdb_id: the imdb id.
    :return: the corresponding DB id.
    """

    show_match = configuration.session.query(models.ShowMatch).filter(
        models.ShowMatch.imdb_id == imdb_id).first()

    if show_match is None:
        return None

    return show_match.show_id


def search_db_id(show_id, is_show, below_date=None, show_season=None, show_episode=None):
    """
    Get the results of the search in the DB, using show id (either series_id or pid).

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param below_date: a date below to limit the search.
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :return: results of the search in the DB.
    """

    if is_show:
        query = configuration.session.query(models.Show).filter(
            models.Show.series_id == show_id)

        if show_season is not None:
            query = query.filter(models.Show.show_season == show_season)

        if show_episode is not None:
            query = query.filter(models.Show.show_episode == show_episode)
    else:
        query = configuration.session.query(models.Show).filter(
            models.Show.pid == show_id)

    if below_date is not None:
        query = query.filter(models.Show.date_time > below_date)

    return query.all()


def register_reminder(show_id, is_show, reminder_type: models.ReminderType, show_season, show_episode, user_id):
    """
    Create a reminder for the given data.

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param reminder_type: reminder type.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param user_id: the owner of the reminder.
    """

    show = configuration.session.query(models.ShowReminder) \
        .filter(models.ShowReminder.user_id == user_id) \
        .filter(models.ShowReminder.is_show == is_show) \
        .filter(models.ShowReminder.show_id == show_id).first()

    if not is_show:
        show_season = None
        show_episode = None

    if show is not None:
        return update_reminder(show, show_id, is_show, reminder_type, show_season, show_episode, user_id)

    configuration.session.add(
        models.ShowReminder(show_id, is_show, reminder_type.value, show_season, show_episode, user_id))

    # Add all possible titles for that trakt id to the DB
    if models.ReminderType.TRAKT == reminder_type:
        if is_show:
            show_type = 'show'
        else:
            show_type = 'movie'

        titles = get_titles_trakt(show_id, show_type)

        for t in titles:
            configuration.session.add(models.TraktTitle(show_id, t))

    configuration.session.commit()

    return get_reminders(user_id)


def update_reminder(show: models.ShowReminder, show_id, is_show, reminder_type: models.ReminderType, show_season,
                    show_episode, user_id):
    """
    Update a reminder with the given data.

    :param show: the show to update, or None.
    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param reminder_type: reminder type.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param user_id: the owner of the reminder.
    """

    if show is None:
        show = configuration.session.query(models.ShowReminder) \
            .filter(models.ShowReminder.user_id == user_id) \
            .filter(models.ShowReminder.show_id == show_id).first()

    show.is_show = is_show
    show.reminder_type = reminder_type.value

    if show.is_show:
        show.show_season = show_season
        show.show_episode = show_episode

    configuration.session.commit()

    return get_reminders(user_id)


def get_reminders(user_id):
    """
    Get a list of reminders for the user who's id is user_id.

    :param user_id: the id of the user.
    :return: a list of reminders for the user who's id is user_id.
    """

    reminders = configuration.session.query(models.ShowReminder) \
        .filter(models.ShowReminder.user_id == user_id).all()

    # Add the possible titles to the reminders sent
    final_reminders = []

    for r in reminders:
        reminder_type = models.ReminderType(r.reminder_type)

        if models.ReminderType.TRAKT == reminder_type:
            db_titles = get_titles_db(r.show_id)

            titles = []

            for t in db_titles:
                titles.append(t.trakt_title)
        else:
            titles = [r.show_id]

        final_reminders.append(ShowReminder(r.show_id, r.is_show, models.ReminderType(r.reminder_type), r.show_season,
                                            r.show_episode, titles))

    return final_reminders


def remove_reminder(reminder_id):
    """
    Delete the reminder with the corresponding id.

    :param reminder_id: the id of the reminder.
    """

    reminder = configuration.session.query(models.ShowReminder).filter(
        models.ShowReminder.id == reminder_id).first()
    configuration.session.delete(reminder)

    configuration.session.commit()


def process_reminders(last_date):
    """
    Process the reminders that exist in the DB.

    :param last_date: the date of the last update.
    """

    reminders = configuration.session.query(models.ShowReminder).all()

    for r in reminders:
        if r.reminder_type == models.ReminderType.DB:
            db_shows = search_db_id(r.show_id, r.is_show, last_date, r.show_season, r.show_episode)
        else:
            db_id = get_corresponding_id(r.show_id)

            if db_id is not None:
                db_shows = search_db_id(db_id, r.is_show, last_date, r.show_season, r.show_episode)
            else:
                titles = get_titles_db(r.show_id)

                user = configuration.session.query(models.User).filter(models.User.id == r.user_id).first()

                search_adult = user.show_adult if user is not None else False

                db_shows = search_db(titles, True, last_date, r.show_season, r.show_episode, search_adult)

        # TODO: Send notification with shows found
        print('Number of shows: %d' % len(db_shows))

        for s in db_shows:
            print(s)


def get_last_update():
    """Get the date of the last update."""

    last_update = configuration.session.query(models.LastUpdate).first()

    if last_update is None:
        return datetime.datetime.now() - datetime.timedelta(days=10)

    return last_update.date


def register_user(email: str, password: str):
    """
    Register a new user.

    :param email: the user's email.
    :param password: the user's password.
    """

    password = fb.generate_password_hash(password, configuration.bcrypt_rounds).decode()

    try:
        configuration.session.add(models.User(email, password))
        configuration.session.commit()
        # TODO: Send registration email
    except (IntegrityError, InvalidRequestError):
        configuration.session.rollback()
        # TODO: Send warning email


def check_login(email: str, password: str):
    """
    Verify with the user's credentials.

    :param email: the user's email.
    :param password: the user's password.
    """

    user = configuration.session.query(models.User).filter(models.User.email == email).first()

    if user is None:
        user_password = None
    else:
        user_password = user.password

    try:
        valid = fb.check_password_hash(user_password, password)
    except TypeError:
        valid = False

    return valid


def get_user_by_email(email: str):
    """
    Get the user corresponding to an email.

    :param email: the user's email.
    """

    user = configuration.session.query(models.User).filter(
        models.User.email == email).first()

    return user


def logout(auth_token: str):
    """
    Logout, by eliminating a token from the DB.

    :param auth_token: the authentication token.
    """

    token = configuration.session.query(models.Token).filter(models.Token.token == auth_token).first()

    if token is not None:
        configuration.session.delete(token)
        configuration.session.commit()


def make_searchable_title(title):
    """
    Remove accents from the title and join words with _ (underscore).

    :param title: the original title.
    :return: the resulting title.
    """

    unaccented_title = auxiliary.strip_accents(title)

    words = re.compile('[^0-9A-Za-z]+').split(unaccented_title)

    return '_' + '_'.join(words) + '_'


def main():
    process_reminders(datetime.date.today() - datetime.timedelta(5))


if __name__ == '__main__':
    main()
