import datetime
from enum import Enum
from typing import List

import flask_bcrypt as fb
import sqlalchemy.orm

import authentication
import auxiliary
import configuration
import db_calls
import models
import omdb_calls
import process_emails
import response_models
import trakt_calls
from trakt_calls import search_shows_by_text, get_show_translations


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

    session.query(models.ShowSession).filter(
        models.ShowSession.date_time < today_start - datetime.timedelta(7)).delete()
    session.commit()

    print('Shows list cleared!')


def search_show_information(search_text: str, is_movie: bool, language: str):
    """
    Uses trakt and omdb to search for shows using a given search text.

    :param search_text: the search text introduced by the user.
    :param is_movie: if it is a movie.
    :param language: the language.

    :return: the list of results.
    """

    if is_movie is not None:
        return search_show_information_by_type(search_text, is_movie, language)
    else:
        results = search_show_information_by_type(search_text, False, language)
        results += search_show_information_by_type(search_text, True, language)

    return results


def search_show_information_by_type(search_text: str, is_movie: bool, language: str):
    """
    Uses trakt and omdb to search for shows, of a given type, using a given search text.

    :param search_text: the search text introduced by the user.
    :param is_movie: if the show is a movie.
    :param language: the language of interest.
    :return: the list of results.
    """

    results = []

    # Search Trakt using the text
    trakt_shows = search_shows_by_text(search_text, is_movie)

    for s in trakt_shows:
        show_dict = {'is_movie': is_movie, 'show_title': s.title, 'show_year': s.year, 'show_image': 'N/A',
                     'trakt_id': s.id, 'show_overview': s.overview, 'language': s.language}

        # Get the translation of the overview
        if language != s.language:
            if language in s.available_translations:
                trakt_translations = get_show_translations(s.slug, is_movie)

                for transl in trakt_translations:
                    if transl.language == language:
                        show_dict['show_overview'] = transl.overview
                        break

        # Get the poster from Omdb
        omdb_show = omdb_calls.search_show_by_imdb_id(s.imdb_id)

        if omdb_show is None:
            results.append(show_dict)
        else:
            show_dict['show_image'] = omdb_show.poster
            results.append(show_dict)

    return results


def search_db(session: sqlalchemy.orm.Session, search_list, complete_title=False, below_date=None, show_season=None,
              show_episode=None,
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

        # Split the search text into a list of words
        search_words = auxiliary.get_words(search_text)

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

        query = session.query(models.ShowSession, models.Channel.name, models.ShowData.portuguese_title) \
            .filter(models.ShowData.search_title.op(operation)(search_pattern))

        if show_season is not None:
            query = query.filter(models.ShowSession.season == show_season)

        if show_episode is not None:
            query = query.filter(models.ShowSession.episode == show_episode)

        if not search_adult:
            # Can't use "is" here, it needs to be "=="
            query = query.filter(models.Channel.adult == False)

        if below_date is not None:
            query = query.filter(models.ShowSession.date_time > below_date)

        # Join channels
        query = query.join(models.Channel)

        # Join show data
        query = query.join(models.ShowData)

        db_shows = query.all()

        for s in db_shows:
            show = s[0].to_dict()
            show['channel'] = s[1]
            show['title'] = s[2]

            results[show['id']] = show

    # Create a list from the dictionary of results
    final_results = []

    for r in results.values():
        final_results.append(r)

    return final_results


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
        query = session.query(models.ShowSession).filter(
            models.ShowSession.series_id == show_name)

        if show_season is not None:
            query = query.filter(models.ShowSession.season == show_season)

        if show_episode is not None:
            query = query.filter(models.ShowSession.episode == show_episode)
    else:
        query = session.query(models.ShowSession).filter(
            models.ShowSession.pid == show_name)

    if below_date is not None:
        query = query.filter(models.ShowSession.date_time > below_date)

    return query.all()


def get_trakt_titles(session: sqlalchemy.orm.Session, trakt_id: int, is_movie: bool) -> List[str]:
    """
    Get all trakt titles for a trakt id.
    And update the DB with the results.

    :param session: the db session.
    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :return: the list of titles a show can have.
    """

    trakt_titles = db_calls.get_trakt_titles(session, trakt_id)

    # Titles in the DB are still valid
    if trakt_titles is not None \
            and trakt_titles.insertion_datetime + datetime.timedelta(
        days=configuration.titles_validity_days) > datetime.datetime.now():
        return trakt_titles.titles.split('|')

    # Collect all titles for a show
    titles = trakt_calls.collect_titles_trakt(trakt_id, is_movie)

    # Create the titles string stored in the DB
    titles_str = ''

    for t in titles:
        if titles_str != '':
            titles_str += '|' + t
        else:
            titles_str = t

    # Create a new entry
    if trakt_titles is None:
        trakt_titles = db_calls.register_trakt_titles(session, trakt_id, titles_str)
        session.add(trakt_titles)
    # Update the current entry
    else:
        trakt_titles.titles = titles_str
        session.commit()

    return titles


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
    reminder = session.query(models.Reminder) \
        .filter(models.Reminder.user_id == user_id) \
        .filter(models.Reminder.is_movie == False) \
        .filter(models.Reminder.id == reminder_id).first()

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

    reminders = session.query(models.Reminder) \
        .filter(models.Reminder.user_id == user_id).all()

    # Add the possible titles to the reminders sent
    final_reminders = []

    for r in reminders:
        reminder_type = response_models.ReminderType(r.reminder_type)

        if response_models.ReminderType.DB == reminder_type:
            titles = get_trakt_titles(session, r.trakt_id, r.is_movie)
        else:
            titles = [r.show_name]

        final_reminders.append(response_models.Reminder(r, titles))

    return final_reminders


def remove_reminder(session, reminder_id, user_id):
    """
    Delete the reminder with the corresponding id.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param user_id: the id of the user.
    """

    reminder = session.query(models.Reminder) \
        .filter(models.Reminder.id == reminder_id) \
        .filter(models.Reminder.user_id == user_id) \
        .first()

    if reminder is not None:
        session.delete(reminder)
        session.commit()


def process_reminders(session: sqlalchemy.orm.Session, last_date: datetime.date):
    """
    Process the reminders that exist in the DB.

    :param session: the db session.
    :param last_date: the date of the last update.
    """

    reminders = db_calls.get_reminders(session)

    for r in reminders:
        user = session.query(models.User).filter(models.User.id == r.user_id).first()
        search_adult = user.show_adult if user is not None else False

        if r.reminder_type == response_models.ReminderType.LISTINGS.value:
            db_shows = search_db(session, [r.show_name], True, last_date, r.show_season, r.show_episode, search_adult)
        else:
            titles = get_trakt_titles(session, r.trakt_id, r.is_movie)
            db_shows = search_db(session, titles, True, last_date, r.show_season, r.show_episode, search_adult)

        if len(db_shows) > 0:
            process_emails.set_language(user.language)
            process_emails.send_reminders_email(user.email, db_shows)

    print('Reminders processed!')


def get_last_update(session) -> datetime.date:
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

    user = db_calls.register_user(session, email, password, language)

    if user is not None:
        return send_verification_email(session, user)
    else:
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


def get_alarms(session, user_id: int) -> List[response_models.Alarm]:
    """
    Get a list of alarms for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of alarms for the user who's id is user_id.
    """

    if not user_id:
        return []

    alarms = db_calls.get_alarms_user(session, user_id)

    final_alarms = []

    for a in alarms:
        final_alarms.append(response_models.Alarm(session, a))

    return final_alarms


def process_alarms(session: sqlalchemy.orm.Session) -> None:
    """
    Process the alarms that exist in the DB, sending an email when the session is within the desired time frame.

    :param session: the db session.
    """

    alarms_sessions = db_calls.get_sessions_alarms(session)

    for a_s in alarms_sessions:
        alarm: models.Alarm = a_s.Alarm
        show_session: models.ShowSession = a_s.ShowSession

        anticipation_hours = alarm.anticipation_minutes / 60

        # If it is time to fire the alarm
        if datetime.datetime.utcnow() + datetime.timedelta(hours=anticipation_hours) > show_session.date_time:
            user = db_calls.get_user_id(session, alarm.user_id)
            channel = db_calls.get_channel_id(session, show_session.channel_id)

            # Add the channel to the session
            show_session.channel = channel.name

            process_emails.set_language(user.language)
            process_emails.send_reminders_email(user.email, [show_session])

            session.delete(alarm)
            session.commit()

    print('Alarms processed!')
