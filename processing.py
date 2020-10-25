import datetime
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from enum import Enum

import flask_bcrypt as fb
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import authentication
import auxiliary
import configuration
import models
import process_emails
import response_models
from response_models import ShowReminder


class ComparisonType(Enum):
    EQUALS = 0
    BIGGER = 1
    SMALLER = 2


class ChangeType(Enum):
    NEW_EMAIL = 'change_email'
    INCLUDE_ADULT_CHANNELS = 'include_adult_channels'
    NEW_PASSWORD = 'new_password'
    LANGUAGE = 'language'


def list_to_json(list_of_objects):
    """Create a list with the result of to_dict for each element."""

    result = []

    for o in list_of_objects:
        result.append(o.to_dict())

    return result


def clear_show_list(session):
    """Delete entries with more than 7 days old, from the DB."""

    today_start = datetime.datetime.now()
    today_start.replace(hour=0, minute=0, second=0)

    session.query(models.Show).filter(
        models.Show.date_time < today_start - datetime.timedelta(7)).delete()
    session.commit()

    print('Shows list cleared!')


def search_show_information_by_type(search_text: str, show_type: str, language: str):
    """
    Uses trakt and omdb to search for shows, of a given type, using a given search text.

    :param search_text: the search text introduced by the user.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :param language: the language of interest.
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

    is_movie = show_type == 'movie'

    for s in shows:
        imdb_id = s[show_type]['ids']['imdb']

        show_dict = {'is_movie': is_movie, 'show_title': s[show_type]['title'], 'show_year': s[show_type]['year'],
                     'show_image': 'N/A', 'show_slug': s[show_type]['ids']['slug'],
                     'show_overview': s[show_type]['overview'], 'language': s[show_type]['language'],
                     'available_translations': s[show_type]['available_translations']}

        # Get the translation of the overview
        if language != s[show_type]['language']:
            available_translations = s[show_type]['available_translations']

            if language in available_translations:
                translated_overview = get_translated_overview(s[show_type]['ids']['slug'], show_type, language)

                if translated_overview is not None:
                    show_dict['show_overview'] = translated_overview

        # Check if we can get the poster
        if imdb_id is None or configuration.omdb_key is None:
            results.append(show_dict)
            continue

        show_json = urllib.request.urlopen(
            'http://www.omdbapi.com/?apikey=%s&i=%s' % (configuration.omdb_key, s[show_type]['ids']['imdb'])).read()

        # Parse the show from the request
        show = json.loads(show_json)

        # When the omdb can't find the information
        if show['Response'] == 'False':
            results.append(show_dict)
            continue

        show_dict['show_image'] = show['Poster']

        results.append(show_dict)

    return results


def search_show_information(search_text: str, is_movie: bool, language: str):
    """
    Uses trakt and omdb to search for shows using a given search text.

    :param search_text: the search text introduced by the user.
    :param is_movie: if it is a movie.
    :param language: the language.

    :return: the list of results.
    """

    results = []

    if is_movie is None or not is_movie:
        results += search_show_information_by_type(search_text, 'show', language)

    if is_movie is None or is_movie:
        results += search_show_information_by_type(search_text, 'movie', language)

    return results


def get_translated_overview(trakt_slug: str, show_type: str, language: str):
    """
    Get the translated overview of a show.

    :param trakt_slug: the selected title.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :param language: the language of the translation.
    :return: the translated overview.
    """

    translations_request = urllib.request.Request(
        'https://api.trakt.tv/%ss/%s/translations/%s' % (show_type, trakt_slug, language))
    translations_request.add_header('trakt-api-key', configuration.trakt_key)

    try:
        translations_json = urllib.request.urlopen(translations_request).read()
    except urllib.error.HTTPError:
        print('Slug was not found!')
        return None

    # Parse the list of translations from the request
    translations = json.loads(translations_json)

    for t in translations:
        if t['overview'] != '':
            return t['overview']

    return None


def get_titles_trakt(trakt_slug, trakt_name, trakt_show_language, trakt_available_translations, show_type):
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the trakt API.

    :param trakt_slug: the selected title.
    :param trakt_name: the name of the show.
    :param trakt_show_language: the main language of the show.
    :param trakt_available_translations: the available translations for the show.
    :param show_type: 'show' for tv shows and 'movie' for movies.
    :return: the various possible titles.
    """

    # If there are no translations, return the original name
    if 'en' not in trakt_available_translations and 'pt' not in trakt_available_translations:
        return [trakt_name]

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
    results.add(trakt_name)

    for t in translations:
        if t['title'] is None:
            continue

        if t['language'] == 'en' or t['language'] == 'pt' or t['language'] == trakt_show_language:
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


def get_titles_db(session, trakt_slug):
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the DB.

    :param session: the db session.
    :param trakt_slug: the selected title.
    :return: the various possible titles.
    """

    return session.query(models.TraktTitle).filter(models.TraktTitle.trakt_id == trakt_slug).all()


def search_db(session, search_list, complete_title=False, below_date=None, show_season=None, show_episode=None,
              search_adult=False):
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param session: the db session.
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

        # Operation for search with regex depending on the dbms
        if 'mysql' in configuration.database_url:
            operation = 'REGEXP'
        else:
            operation = '~*'

        query = session.query(models.Show, models.Channel.name) \
            .filter(models.Show.search_title.op(operation)(search_pattern))

        if show_season is not None:
            query = query.filter(models.Show.season == show_season)

        if show_episode is not None:
            query = query.filter(models.Show.episode == show_episode)

        if not search_adult:
            # Can't use "is" here, it needs to be "=="
            query = query.filter(models.Channel.adult == False)

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


def get_corresponding_id(session, imdb_id):
    """
    Get the DB id corresponding to the imdb id.

    :param session: the db session.
    :param imdb_id: the imdb id.
    :return: the corresponding DB id.
    """

    show_match = session.query(models.ShowMatch).filter(
        models.ShowMatch.imdb_id == imdb_id).first()

    if show_match is None:
        return None

    return show_match.show_id


def search_db_id(session, show_name, is_movie, below_date=None, show_season=None, show_episode=None):
    """
    Get the results of the search in the DB, using show id (either series_id or pid).

    :param session: the db session.
    :param show_name: the name of the show.
    :param is_movie: true if it is a movie.
    :param below_date: a date below to limit the search.
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :return: results of the search in the DB.
    """

    if not is_movie:
        query = session.query(models.Show).filter(
            models.Show.series_id == show_name)

        if show_season is not None:
            query = query.filter(models.Show.season == show_season)

        if show_episode is not None:
            query = query.filter(models.Show.episode == show_episode)
    else:
        query = session.query(models.Show).filter(
            models.Show.pid == show_name)

    if below_date is not None:
        query = query.filter(models.Show.date_time > below_date)

    return query.all()


def register_trakt_titles(session, show_slug, show_name, show_language, show_available_translations, is_movie):
    """
    Register all trakt titles for a show_slug.

    :param session: the db session.
    :param show_slug: the slug that represents this show.
    :param show_name: the movie's original name.
    :param show_language: the main language of the show.
    :param show_available_translations: the available translations for the show.
    :param is_movie: true if it is a movie.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'show'

    titles = get_titles_trakt(show_slug, show_name, show_language, show_available_translations, show_type)

    query = session.query(models.TraktTitle) \
        .filter(models.TraktTitle.trakt_id == show_slug) \
        .filter(models.TraktTitle.is_movie == is_movie)

    for t in titles:
        if t is None:
            continue

        # Only add new entries
        if query.filter(models.TraktTitle.trakt_title == t).first() is None:
            session.add(models.TraktTitle(show_slug, is_movie, t))

    session.commit()


def register_reminder(session, show_name: str, is_movie: bool, reminder_type: response_models.ReminderType,
                      show_slug: str, show_season, show_episode, user_id, show_language: str,
                      show_available_translations: [str]):
    """
    Create a reminder for the given data.

    :param session: the db session.
    :param show_name: the name of the show.
    :param is_movie: true if it is a movie.
    :param reminder_type: reminder type.
    :param show_slug: show slug for the reminder.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param user_id: the owner of the reminder.
    :param show_language: the main language of the show.
    :param show_available_translations: the available translations for the show.
    """

    reminder = session.query(models.DBReminder) \
        .filter(models.DBReminder.user_id == user_id) \
        .filter(models.DBReminder.is_movie == is_movie) \
        .filter(models.DBReminder.show_name == show_name).first()

    # End processing if the reminder already exists
    if reminder is not None:
        return False

    if is_movie:
        show_season = None
        show_episode = None

    session.add(
        models.DBReminder(show_name, is_movie, reminder_type.value, show_season, show_episode, user_id, show_slug))

    # Add all possible titles for that trakt id to the DB
    if response_models.ReminderType.DB == reminder_type:
        register_trakt_titles(session, show_slug, show_name, show_language, show_available_translations, is_movie)

    session.commit()

    return True


def update_reminder(session, reminder_id: int, show_season: int, show_episode: int, user_id: int):
    """
    Update a reminder with the given data.
    This only matters when the show is not a movie, so we can update the season and/or episode.

    :param session: the db session.
    :param reminder_id: the id of the corresponding id.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param user_id: the id of the corresponding user.
    """

    # Somehow using the is False does not work
    reminder = session.query(models.DBReminder) \
        .filter(models.DBReminder.user_id == user_id) \
        .filter(models.DBReminder.is_movie == False) \
        .filter(models.DBReminder.id == reminder_id).first()

    # End processing if the reminder does not exist
    if reminder is None:
        return False

    reminder.show_season = show_season
    reminder.show_episode = show_episode

    session.commit()

    return True


def get_reminders(session, user_id):
    """
    Get a list of reminders for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of reminders for the user who's id is user_id.
    """

    if not user_id:
        return []

    reminders = session.query(models.DBReminder) \
        .filter(models.DBReminder.user_id == user_id).all()

    # Add the possible titles to the reminders sent
    final_reminders = []

    for r in reminders:
        reminder_type = response_models.ReminderType(r.reminder_type)

        if response_models.ReminderType.DB == reminder_type:
            db_titles = get_titles_db(session, r.show_slug)

            titles = []

            for t in db_titles:
                titles.append(t.trakt_title)
        else:
            titles = [r.show_name]

        final_reminders.append(ShowReminder(r, titles))

    return final_reminders


def remove_reminder(session, reminder_id, user_id):
    """
    Delete the reminder with the corresponding id.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param user_id: the id of the user.
    """

    reminder = session.query(models.DBReminder) \
        .filter(models.DBReminder.id == reminder_id) \
        .filter(models.DBReminder.user_id == user_id) \
        .first()

    if reminder is not None:
        session.delete(reminder)
        session.commit()


def process_reminders(session, last_date):
    """
    Process the reminders that exist in the DB.

    :param session: the db session.
    :param last_date: the date of the last update.
    """

    reminders = session.query(models.DBReminder).all()

    for r in reminders:
        user = session.query(models.User).filter(models.User.id == r.user_id).first()
        search_adult = user.show_adult if user is not None else False

        if r.reminder_type == response_models.ReminderType.LISTINGS.value:
            db_shows = search_db(session, [r.show_name], True, last_date, r.show_season, r.show_episode, search_adult)
        else:
            db_id = get_corresponding_id(session, r.show_name)

            if db_id is not None:
                db_shows = search_db_id(db_id, r.is_movie, last_date, r.show_season, r.show_episode)
            else:
                titles = auxiliary.get_names_list_from_trakttitles_list(get_titles_db(session, r.show_slug))

                db_shows = search_db(session, titles, True, last_date, r.show_season, r.show_episode, search_adult)

        if len(db_shows) > 0:
            process_emails.set_language(user.language)
            process_emails.send_reminders_email(user.email, db_shows)

    print('Reminders processed!')


def get_last_update(session):
    """
    Get the date of the last update.

    :param session: the db session.
    :return: the date of the last update.
    """

    last_update = session.query(models.LastUpdate).first()

    if last_update is None:
        return datetime.datetime.now() - datetime.timedelta(days=10)

    return last_update.date


def register_user(session, email: str, password: str, language: str) -> bool:
    """
    Register a new user.

    :param session: the db session.
    :param email: the user's email.
    :param password: the user's password.
    :param language: the user's language of choice.
    """

    password = fb.generate_password_hash(password, configuration.bcrypt_rounds).decode()

    try:
        user = models.User(email, password)

        # Set the language for the user
        if language is not None and language in models.AVAILABLE_LANGUAGES:
            user.language = language

        session.add(user)
        session.commit()

        return send_verification_email(session, user)
    except (IntegrityError, InvalidRequestError) as exception:
        print(exception)

        session.rollback()
        # TODO: Send warning email

        return False


def verify_user(session, verification_token: str):
    """
    Verify a user's account.

    :param session: the db session.
    :param verification_token: the verification token.
    :return: whether the verification was success or not.
    """

    # Validate verification token
    valid, user_id = authentication.validate_token(session, verification_token.encode(),
                                                   authentication.TokenType.VERIFICATION)

    if not valid:
        return False

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    # Check if the user was found
    if user is None:
        return False

    # Set user's account to verified
    user.verified = True

    session.commit()

    return True


def send_verification_email(session, user: models.User):
    """
    Send a verification email.

    :param session: the db session.
    :param user: the user.
    """

    verification_token = authentication.generate_token(session, user.id, authentication.TokenType.VERIFICATION).decode()

    process_emails.set_language(user.language)
    return process_emails.send_verification_email(user.email, verification_token)


def send_deletion_email(session, user_id: str) -> bool:
    """
    Send a verification email.

    :param session: the db session.
    :param user_id: the user id.
    """

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        return False

    deletion_token = authentication.generate_token(session, user.id, authentication.TokenType.DELETION).decode()

    process_emails.set_language(user.language)
    return process_emails.send_deletion_email(user.email, deletion_token)


def send_change_email_old(session, user_id: str) -> bool:
    """
    Send a change email email to the old email.

    :param session: the db session.
    :param user_id: the user id.
    """

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        return False

    change_email_old_token = authentication.generate_token(session, user.id,
                                                           authentication.TokenType.CHANGE_EMAIL_OLD).decode()

    process_emails.set_language(user.language)
    return process_emails.send_change_email_old(user.email, change_email_old_token)


def send_change_email_new(session, change_token_old: str, new_email: str) -> (bool, bool):
    """
    Send a 'Change Email' email to the new email address.

    :param session: the db session.
    :param change_token_old: the change token from the old email address.
    :param new_email: the new email.
    :return: a pair of booleans: the first is the success of the operation and the second is if the motif of the failure
    is that the new email is already at use.
    """

    # Validate the change token from the old email address
    valid, user_id = authentication.validate_token(session, change_token_old.encode(),
                                                   authentication.TokenType.CHANGE_EMAIL_OLD)

    if not valid:
        return False, False

    # Get the user id from the token
    user_id = authentication.get_token_field(change_token_old.encode(), 'user')

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        return False, False

    # Check if the new email is valid
    new_email_user = session.query(models.User).filter(models.User.email == new_email).first()

    if new_email_user is not None:
        return False, True

    changes = {ChangeType.NEW_EMAIL.value: new_email}
    change_email_new_token = authentication.generate_change_token(session, user.id,
                                                                  authentication.TokenType.CHANGE_EMAIL_NEW,
                                                                  changes).decode()

    process_emails.set_language(user.language)
    return process_emails.send_change_email_new(new_email, change_email_new_token, user.email), True


def send_password_recovery_email(session, user_id: str) -> bool:
    """
    Send a recover password email.

    :param session: the db session.
    :param user_id: the user id.
    """

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    if user is None:
        return False

    password_recovery_token = authentication.generate_token(session, user.id,
                                                            authentication.TokenType.PASSWORD_RECOVERY).decode()

    process_emails.set_language(user.language)
    return process_emails.send_password_recovery_email(user.email, password_recovery_token)


def check_login(session, email: str, password: str):
    """
    Verify with the user's credentials.

    :param session: the db session.
    :param email: the user's email.
    :param password: the user's password.
    """

    if not email:
        return False

    user = session.query(models.User).filter(models.User.email == email).first()

    if user is None:
        user_password = None
    else:
        user_password = user.password

    try:
        valid = fb.check_password_hash(user_password, password)
    except (TypeError, ValueError):
        valid = False

    return valid


def get_user_by_email(session, email: str):
    """
    Get the user corresponding to an email.

    :param session: the db session.
    :param email: the user's email.
    """

    user = session.query(models.User).filter(
        models.User.email == email).first()

    return user


def logout(session, refresh_token: str):
    """
    Logout, by eliminating a token from the DB.

    :param session: the db session.
    :param refresh_token: the refresh token.
    """

    token = session.query(models.Token).filter(models.Token.token == refresh_token).first()

    if token is not None:
        session.delete(token)
        session.commit()


def make_searchable_title(title):
    """
    Remove accents from the title and join words with _ (underscore).

    :param title: the original title.
    :return: the resulting title.
    """

    unaccented_title = auxiliary.strip_accents(title)

    words = re.compile('[^0-9A-Za-z]+').split(unaccented_title)

    return '_' + '_'.join(words) + '_'


def delete_user(session, deletion_token: str):
    """
    Delete a user's account.

    :param session: the db session.
    :param deletion_token: the deletion token.
    :return: whether the deletion was success or not.
    """

    # Validate deletion token
    valid, user_id = authentication.validate_token(session, deletion_token.encode(), authentication.TokenType.DELETION)

    if not valid:
        return False

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    # Check if the user was found
    if user is None:
        return False

    # Delete user
    session.delete(user)
    session.commit()

    return True


def change_user_settings_token(session, change_token: str):
    """
    Change settings from a user's account.

    :param session: the db session.
    :param change_token: the change token.
    :return: whether the deletion was success or not.
    """

    # Validate change token
    valid, user_id = authentication.validate_token(session, change_token.encode(),
                                                   authentication.TokenType.CHANGE_EMAIL_NEW)

    if not valid:
        return False

    # Check for changes
    payload = authentication.get_token_payload(change_token)

    return change_user_settings(session, payload, user_id)


def change_user_settings(session, changes: dict, user_id: str):
    """
    Change the settings that are present in the dictionary.

    :param session: the db session.
    :param changes: the dictionary with the changes to be applied.
    :param user_id: the id of the user.
    :return: True if something has been changed.
    """

    if not user_id:
        return {}

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    # Check if the user was found
    if user is None:
        return False

    something_changed = False

    if ChangeType.NEW_EMAIL.value in changes:
        something_changed = True
        user.email = changes[ChangeType.NEW_EMAIL.value]

    if ChangeType.NEW_PASSWORD.value in changes:
        something_changed = True
        user.password = fb.generate_password_hash(changes[ChangeType.NEW_PASSWORD.value],
                                                  configuration.bcrypt_rounds).decode()

    if ChangeType.INCLUDE_ADULT_CHANNELS.value in changes:
        something_changed = True
        user.show_adult = changes[ChangeType.INCLUDE_ADULT_CHANNELS.value]

    if ChangeType.LANGUAGE.value in changes:
        something_changed = True
        user.language = changes[ChangeType.LANGUAGE.value]

    if not something_changed:
        return False

    try:
        # Commit the changes
        session.commit()
    except:
        session.rollback()
        # TODO: Send warning email

    return True


def recover_password(session, recover_token: str, new_password: str):
    """
    Change the password of the user's account.

    :param session: the db session.
    :param recover_token: the recover token.
    :param new_password: the new password.
    :return: whether the deletion was success or not.
    """

    # Validate change token
    valid, user_id = authentication.validate_token(session, recover_token.encode(),
                                                   authentication.TokenType.PASSWORD_RECOVERY)

    if not valid:
        return False

    # Change the password
    return change_user_settings(session, {ChangeType.NEW_PASSWORD.value: new_password}, user_id)


def get_settings(session, user_id: int):
    """
    Get a list of settings for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of settings for the user who's id is user_id.
    """

    # Get user
    user = session.query(models.User).filter(models.User.id == user_id).first()

    # Check if the user was found
    if user is None:
        return {}

    return {'include_adult_channels': user.show_adult, 'language': user.language}
