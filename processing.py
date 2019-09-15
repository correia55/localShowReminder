from enum import Enum
from sqlalchemy.exc import IntegrityError

import urllib.request
import urllib.error
import urllib.parse
import json
import datetime
import re
import flask_bcrypt as fb

import models
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

    results = dict()

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

        query = configuration.session.query(models.Show, models.Channel.name).filter(
            models.Show.show_title.ilike(search_pattern))

        if show_season is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(models.Show.show_season == show_season)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(models.Show.show_season > show_season)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(models.Show.show_season < show_season)

        if show_episode is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(models.Show.show_episode == show_episode)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(models.Show.show_episode > show_episode)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(models.Show.show_episode < show_episode)

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
        query = configuration.session.query(models.Show).filter(
            models.Show.series_id == show_id)

        if show_season is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(models.Show.show_season == show_season)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(models.Show.show_season > show_season)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(models.Show.show_season < show_season)

        if show_episode is not None:
            if comparison_type is None or comparison_type == ComparisonType.EQUALS.value:
                query = query.filter(models.Show.show_episode == show_episode)
            elif comparison_type == ComparisonType.BIGGER.value:
                query = query.filter(models.Show.show_episode > show_episode)
            elif comparison_type == ComparisonType.SMALLER.value:
                query = query.filter(models.Show.show_episode < show_episode)
    else:
        query = configuration.session.query(models.Show).filter(
            models.Show.pid == show_id)

    if below_date is not None:
        query = query.filter(models.Show.date_time > below_date)

    return query.all()


def register_reminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type, user_id):
    """
    Create a reminder for the given data.

    :param show_id: the id to search for.
    :param is_show: true if it is a show.
    :param reminder_type: 0 if it's a DB and 1 otherwise.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param comparison_type: type of comparison for the reminder.
    :param user_id: the owner of the reminder.
    """

    configuration.session.add(
        models.ShowReminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type, user_id))

    configuration.session.commit()


def get_reminders(user_id):
    """
    Get a list of reminders for the user who's id is user_id.

    :param user_id: the id of the user.
    :return: a list of reminders for the user who's id is user_id.
    """

    reminders = configuration.session.query(models.ShowReminder).filter(
        models.ShowReminder.user_id == user_id).all()

    return reminders


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

    return configuration.session.query(models.LastUpdate).first().date


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
    except IntegrityError:
        pass
        # TODO: Send warning email


def check_login(email: str, password: str):
    """
    Verify with the user's credentials.

    :param email: the user's email.
    :param password: the user's password.
    """

    user = configuration.session.query(models.User).filter(
        models.User.email == email).first()

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


def main():
    process_reminders(datetime.date.today() - datetime.timedelta(5))


if __name__ == '__main__':
    main()
