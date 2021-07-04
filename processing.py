import datetime
import time
from enum import Enum
from typing import List, Tuple, Mapping, Optional

import flask_bcrypt as fb
import sqlalchemy.orm

import authentication
import auxiliary
import configuration
import db_calls
import external_authentication
import models
import process_emails
import response_models
import tmdb_calls


class ComparisonType(Enum):
    EQUALS = 0
    BIGGER = 1
    SMALLER = 2


class ChangeType(Enum):
    NEW_EMAIL = 'change_email'
    INCLUDE_ADULT_CHANNELS = 'include_adult_channels'
    NEW_PASSWORD = 'new_password'
    LANGUAGE = 'language'
    EXCLUDED_CHANNELS = 'excluded_channels'


def get_hash(text: str) -> str:
    """
    Get the hash of a text, ensuring the result is a string.
    (Some versions of flask_bcrypt's function return bytes, while others return string)

    :param text: the input text.
    :return: the resulting hash.
    """

    text_hash = fb.generate_password_hash(text, configuration.bcrypt_rounds)

    if isinstance(text_hash, bytes):
        return text_hash.decode()
    else:
        return text_hash


def clear_show_list(session):
    """Delete entries with more than x days old, from the DB."""

    today_start = datetime.datetime.utcnow()
    today_start.replace(hour=0, minute=0, second=0, microsecond=0)

    session.query(models.ShowSession).filter(
        models.ShowSession.date_time < today_start - datetime.timedelta(configuration.show_sessions_validity_days)) \
        .delete()

    db_calls.commit(session)


def search_show_information(session: sqlalchemy.orm.Session, search_text: str, is_movie: bool, language: str,
                            show_adult: bool) -> Tuple[bool, List[dict]]:
    """
    Uses tmdb to search for shows, of a given type, using a given search text.

    :param session: the db session.
    :param search_text: the search text introduced by the user.
    :param is_movie: if the show is a movie.
    :param language: the language of interest.
    :param show_adult: whether to show adult results or not.
    :return: a tuple with a boolean (whether there are more results or not) and the list of results.
    """

    if language == 'pt':
        language_country = 'pt-PT'
    else:
        language_country = 'en-US'

    results = []

    # Search Trakt using the text
    trakt_shows = []
    pages = 1
    i = 1
    total_nb_pages = 1

    # Combine the results from all the pages
    while i < (pages + 1):
        total_nb_pages, trakt_shows_page = tmdb_calls.search_shows_by_text(session, search_text, is_movie=is_movie,
                                                                           page=i, show_adult=show_adult)

        # Get the new total of pages
        pages = min(configuration.tmdb_max_mb_pages, total_nb_pages)

        trakt_shows.extend(trakt_shows_page)
        i += 1

    for s in trakt_shows:
        show_dict = {'is_movie': s.is_movie, 'show_title': s.title, 'show_year': s.year, 'trakt_id': s.id,
                     'show_overview': s.overview, 'language': s.original_language}

        if s.poster_path:
            show_dict['show_image'] = s.poster_path
        else:
            show_dict['show_image'] = 'N/A'

        # Get the translations of the overview and title
        if language != s.original_language:
            tmdb_translations = tmdb_calls.get_show_translations(session, s.id, s.is_movie)

            for transl in tmdb_translations:
                if transl.language_country == language_country and transl.overview != '':
                    show_dict['show_overview'] = transl.overview

                    if transl.title != '':
                        show_dict['show_title'] = transl.title

                    break

        results.append(show_dict)

    return total_nb_pages > configuration.tmdb_max_mb_pages, results


def search_sessions_db(session: sqlalchemy.orm.Session, search_list: List[str], is_movie: bool = None,
                       complete_title: bool = False, only_new: bool = False, show_season: int = None,
                       show_episode: int = None, search_adult: bool = False, ignore_with_tmdb_id: bool = False,
                       use_excluded_channels: bool = False, user_id: int = None) \
        -> List[response_models.LocalShowResult]:
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param session: the db session.
    :param search_list: the list of texts to search for in the DB.
    :param is_movie: True if the search is only for movies.
    :param complete_title: true when we don't want to accept any other words.
    :param only_new: search only new shows (updated yesterday).
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param ignore_with_tmdb_id: True if we want to ignore results that have a tmdb id.
    :param use_excluded_channels: take into account the excluded channels of the user.
    :param user_id: the id of the user (only necessary if use_excluded_channels is True).
    :return: results of the search in the DB.
    """

    if only_new:
        below_datetime = get_last_update_alarms_datetime(session)
    else:
        below_datetime = None

    results = dict()

    excluded_channels = []

    if use_excluded_channels and user_id is not None:
        excluded_channels = db_calls.get_user_excluded_channels(session, user_id)

    for search_text in search_list:
        print('Original search text: %s' % search_text)

        if complete_title:
            search_pattern = auxiliary.make_searchable_title(search_text)
        else:
            search_pattern = auxiliary.make_search_pattern(search_text)

        print('Search pattern: %s' % search_pattern)

        db_shows = db_calls.search_show_sessions_data(session, search_pattern, is_movie, show_season, show_episode,
                                                      search_adult, complete_title, below_datetime=below_datetime,
                                                      ignore_with_tmdb_id=ignore_with_tmdb_id)

        for s in db_shows:
            # Skip sessions from excluded channels
            if s[1].id in excluded_channels:
                continue

            show = response_models.LocalShowResult.create_from_show_session(s[0], s[1], s[2])
            results[show.id] = show

    # Create a list from the dictionary of results
    final_results = []

    for r in results.values():
        final_results.append(r)

    return final_results


def search_sessions_db_with_tmdb_id(session: sqlalchemy.orm.Session, tmdb_id: int, only_new: bool = False,
                                    show_season: int = None, show_episode: int = None,
                                    use_excluded_channels: bool = False, user_id: int = None) \
        -> List[response_models.LocalShowResult]:
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param session: the db session.
    :param tmdb_id: the TMDB id.
    :param only_new: search only new shows (updated yesterday).
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param use_excluded_channels: take into account the excluded channels of the user.
    :param user_id: the id of the user (only necessary if use_excluded_channels is True).
    :return: results of the search in the DB.
    """

    if only_new:
        below_datetime = get_last_update_alarms_datetime(session)
    else:
        below_datetime = None

    results = dict()

    db_shows = db_calls.search_show_sessions_data_with_tmdb_id(session, tmdb_id, show_season, show_episode,
                                                               below_datetime=below_datetime)

    excluded_channels = []

    if use_excluded_channels:
        excluded_channels = db_calls.get_user_excluded_channels(session, user_id)

    for s in db_shows:
        # Skip sessions from excluded channels
        if s[1].id in excluded_channels:
            continue

        show = response_models.LocalShowResult.create_from_show_session(s[0], s[1], s[2])
        results[show.id] = show

    # Create a list from the dictionary of results
    final_results = []

    for r in results.values():
        final_results.append(r)

    return final_results


def search_streaming_services_shows_db(session: sqlalchemy.orm.Session, search_list: List[str], is_movie: bool = None,
                                       complete_title: bool = False, only_new: bool = False,
                                       show_season: int = None, show_episode: int = None, search_adult: bool = False,
                                       ignore_with_tmdb_id: bool = False) -> List[response_models.LocalShowResult]:
    """
    Get the results of the search in the DB, using all the texts from the search list.

    :param session: the db session.
    :param search_list: the list of texts to search for in the DB.
    :param is_movie: True if the search is only for movies.
    :param complete_title: true when we don't want to accept any other words.
    :param only_new: search only new shows (updated yesterday).
    :param show_season: to specify a season.
    :param show_episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param ignore_with_tmdb_id: True if we want to ignore results that have a tmdb id.
    :return: results of the search in the DB.
    """

    if only_new:
        below_datetime = get_last_update_alarms_datetime(session)
    else:
        below_datetime = None

    results = dict()

    for search_text in search_list:
        print('Original search text: %s' % search_text)

        if complete_title:
            search_pattern = auxiliary.make_searchable_title(search_text)
        else:
            search_pattern = auxiliary.make_search_pattern(search_text)

        print('Search pattern: %s' % search_pattern)

        db_shows = db_calls.search_streaming_service_shows_data(session, search_pattern, is_movie, show_season,
                                                                show_episode, search_adult, complete_title,
                                                                below_datetime=below_datetime,
                                                                ignore_with_tmdb_id=ignore_with_tmdb_id)

        for s in db_shows:
            show = response_models.LocalShowResult.create_from_streaming_service_show(s[0], s[1], s[2])
            results[show.id] = show

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


def get_show_titles(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) -> List[str]:
    """
    Get all trakt titles for a trakt id.
    And update the DB with the results.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: true if it is a movie.
    :return: the list of titles a show can have.
    """

    show_titles = db_calls.get_show_titles(session, tmdb_id)

    # Titles in the DB are still valid
    if show_titles is not None \
            and show_titles.insertion_datetime + datetime.timedelta(days=configuration.cache_validity_days) \
            > datetime.datetime.utcnow():
        return show_titles.titles.split('|')

    # Collect all titles for a show
    titles = tmdb_calls.collect_titles(session, tmdb_id, is_movie)

    # Create the titles string stored in the DB
    titles_str = ''

    for t in titles:
        if titles_str != '':
            titles_str += '|' + t
        else:
            titles_str = t

    # Create a new entry
    if show_titles is None:
        show_titles = db_calls.register_show_titles(session, tmdb_id, titles_str)
        session.add(show_titles)
    # Update the current entry
    else:
        show_titles.titles = titles_str
        session.commit()

    return titles


def update_alarm(session, alarm_id: int, show_season: int, show_episode: int, user_id: int):
    """
    Update a alarm with the given data.
    This only matters when the show is not a movie, so we can update the season and/or episode.

    :param session: the db session.
    :param alarm_id: the id of the corresponding id.
    :param show_season: show season for the alarm.
    :param show_episode: show episode for the alarm.
    :param user_id: the id of the corresponding user.
    """

    # Somehow using the is False does not work
    alarm = session.query(models.Alarm) \
        .filter(models.Alarm.user_id == user_id) \
        .filter(models.Alarm.is_movie.is_(False)) \
        .filter(models.Alarm.id == alarm_id).first()

    # End processing if the alarm does not exist
    if alarm is None:
        return False

    alarm.show_season = show_season
    alarm.show_episode = show_episode

    session.commit()

    return True


def get_alarms(session, user_id):
    """
    Get a list of alarms for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of alarms for the user who's id is user_id.
    """

    if not user_id:
        return []

    alarms = session.query(models.Alarm) \
        .filter(models.Alarm.user_id == user_id).all()

    # Add the possible titles to the alarms sent
    final_alarms = []

    for r in alarms:
        alarm_type = response_models.AlarmType(r.alarm_type)

        if response_models.AlarmType.DB == alarm_type:
            titles = get_show_titles(session, r.trakt_id, r.is_movie)
        else:
            titles = [r.show_name]

        final_alarms.append(response_models.Alarm(r, titles))

    return final_alarms


def remove_alarm(session, alarm_id, user_id):
    """
    Delete the alarm with the corresponding id.

    :param session: the db session.
    :param alarm_id: the id of the alarm.
    :param user_id: the id of the user.
    """

    alarm = session.query(models.Alarm) \
        .filter(models.Alarm.id == alarm_id) \
        .filter(models.Alarm.user_id == user_id) \
        .first()

    if alarm is not None:
        session.delete(alarm)
        session.commit()


def process_alarms(session: sqlalchemy.orm.Session):
    """
    Process the alarms that exist in the DB.

    :param session: the db session.
    """

    alarms = db_calls.get_alarms(session)

    for a in alarms:
        user = db_calls.get_user_id(session, a.user_id)
        search_adult = user.show_adult if user is not None else False

        if a.alarm_type == response_models.AlarmType.LISTINGS.value:
            titles = [a.show_name]

            db_shows = []
        else:
            titles = get_show_titles(session, a.trakt_id, a.is_movie)

            db_shows = search_sessions_db_with_tmdb_id(session, a.trakt_id, only_new=True, show_season=a.show_season,
                                                       show_episode=a.show_episode, use_excluded_channels=True,
                                                       user_id=user.id)

        db_shows += search_sessions_db(session, titles, a.is_movie, complete_title=True, only_new=True,
                                       show_season=a.show_season, show_episode=a.show_episode,
                                       search_adult=search_adult, use_excluded_channels=True, user_id=user.id,
                                       ignore_with_tmdb_id=True)

        if len(db_shows) > 0:
            process_emails.set_language(user.language)
            process_emails.send_alarms_email(user.email, db_shows)

    # Update the datetime of the last processing of the alarms
    last_update = db_calls.get_last_update(session)
    last_update.alarms_datetime = datetime.datetime.utcnow()
    db_calls.commit(session)


def get_last_update_alarms_datetime(session: sqlalchemy.orm.Session) -> Optional[datetime.datetime]:
    """
    Get the datetime of the last processing of the alarms.

    :param session: the db session.
    :return: the datetime of the last processing of the alarms.
    """

    last_update = db_calls.get_last_update(session)

    if last_update is None:
        return None

    return last_update.alarms_datetime


def register_user(session, email: str, password: str, language: str) -> bool:
    """
    Register a new user.

    :param session: the db session.
    :param email: the user's email.
    :param password: the user's password.
    :param language: the user's language of choice.
    """

    user = db_calls.register_user(session, email, get_hash(password), language=language)

    if user is not None:
        return send_verification_email(user)
    else:
        # TODO: Send warning email
        return False


def register_external_user(session, email: str, source: str, language: str) -> Optional[models.User]:
    """
    Register a new user, from an external source (such as Google or Facebook).

    :param session: the db session.
    :param email: the user's email.
    :param source: the external source.
    :param language: the user's language of choice.
    :return: the user, when successful.
    """

    # Verify the source
    if source == external_authentication.UserSource.GOOGLE.name:
        account_type = models.AccountType.GOOGLE
    else:
        return None

    # Register the user
    user = db_calls.register_user(session, email, None, language=language, account_type=account_type, verified=True)

    if user is not None:
        return user
    else:
        # TODO: Send warning email
        return None


def verify_user(session, verification_token: str):
    """
    Verify a user's account.

    :param session: the db session.
    :param verification_token: the verification token.
    :return: whether the verification was success or not.
    """

    # Validate verification token
    valid, user_id = authentication.validate_token(verification_token.encode(), authentication.TokenType.VERIFICATION)

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


def send_verification_email(user: models.User):
    """
    Send a verification email.

    :param user: the user.
    """

    verification_token = authentication.generate_token(user.id, authentication.TokenType.VERIFICATION).decode()

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

    deletion_token = authentication.generate_token(user.id, authentication.TokenType.DELETION, session).decode()

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

    change_email_old_token = authentication.generate_token(user.id, authentication.TokenType.CHANGE_EMAIL_OLD,
                                                           session).decode()

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
    valid, user_id = authentication.validate_token(change_token_old.encode(), authentication.TokenType.CHANGE_EMAIL_OLD)

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
    change_email_new_token = authentication.generate_change_token(user.id, authentication.TokenType.CHANGE_EMAIL_NEW,
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

    password_recovery_token = authentication.generate_token(user.id, authentication.TokenType.PASSWORD_RECOVERY,
                                                            session).decode()

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
    valid, user_id = authentication.validate_token(deletion_token.encode(), authentication.TokenType.DELETION)

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
    valid, user_id = authentication.validate_token(change_token.encode(), authentication.TokenType.CHANGE_EMAIL_NEW)

    if not valid:
        return False

    # Check for changes
    payload = authentication.get_token_payload(change_token)

    return change_user_settings(session, payload, user_id)


def change_user_settings(session, changes: Mapping, user_id: int):
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
        user.password = get_hash(changes[ChangeType.NEW_PASSWORD.value])

    if ChangeType.INCLUDE_ADULT_CHANNELS.value in changes:
        something_changed = True
        user.show_adult = changes[ChangeType.INCLUDE_ADULT_CHANNELS.value]

    if ChangeType.LANGUAGE.value in changes:
        something_changed = True
        user.language = changes[ChangeType.LANGUAGE.value]

    if ChangeType.EXCLUDED_CHANNELS.value in changes:
        something_changed = True
        process_excluded_channel_list(session, user_id, changes[ChangeType.EXCLUDED_CHANNELS.value])

    if not something_changed:
        return False

    try:
        # Commit the changes
        session.commit()
    except:
        session.rollback()
        # TODO: Send warning email

    return True


def process_excluded_channel_list(session: sqlalchemy.orm.Session, user_id: int,
                                  excluded_channel_list: List[int]) -> None:
    """
    Update the list of excluded channels of a user.

    :param session: the DB session.
    :param user_id: the id of the user.
    :param excluded_channel_list: the list of excluded channels.
    """

    # Get the current list of excluded channels and turn it into a set
    db_excluded_channel_list = db_calls.get_user_excluded_channels(session, user_id)
    current_excluded_channel_list = set()

    for excluded_channel in db_excluded_channel_list:
        current_excluded_channel_list.add(excluded_channel.channel_id)

    excluded_channel_list = set(excluded_channel_list)

    # There's nothing to do if the current set and the new one are the same
    if current_excluded_channel_list == excluded_channel_list:
        return

    # Otherwise, delete all of the previous entries
    for old_excluded_channel in db_excluded_channel_list:
        session.delete(old_excluded_channel)

    # Otherwise, add all of the new entries
    for excluded_channel in excluded_channel_list:
        db_calls.register_user_excluded_channel(session, user_id, excluded_channel, should_commit=False)

    db_calls.commit(session)


def calculate_score_highlights_week(session: sqlalchemy.orm.Session, year: int, week: int) -> None:
    """
    Calculate the score highlights and save them to the DB.

    :param session: the db session.
    :param year: the year.
    :param week: the week.
    """

    week_start = datetime.date.fromisocalendar(year, week, 1)
    week_end = datetime.date.fromisocalendar(year, week, 7)

    start_datetime = datetime.datetime.combine(week_start, datetime.time(0, 0, 0))
    end_datetime = datetime.datetime.combine(week_end, datetime.time(23, 59, 59))

    # Get the top movies
    shows = db_calls.get_highest_scored_shows_interval(session, start_datetime, end_datetime, True)

    # Get the top tv shows
    shows += db_calls.get_highest_scored_shows_interval(session, start_datetime, end_datetime, False)

    id_list = []

    for s in shows:
        id_list.append(s[1])

    db_calls.register_highlight(session, models.HighlightsType.SCORE, year, week, id_list)


def update_tmdb_data_week(session: sqlalchemy.orm.Session, year: int, week: int) -> None:
    """
    Update the ShowData entries in a week with data from TMDB.

    :param session: the db session.
    :param year: the year.
    :param week: the week.
    """

    week_start = datetime.date.fromisocalendar(year, week, 1)
    week_end = datetime.date.fromisocalendar(year, week, 7)

    start_datetime = datetime.datetime.combine(week_start, datetime.time(0, 0, 0))
    end_datetime = datetime.datetime.combine(week_end, datetime.time(23, 59, 59))

    shows = db_calls.get_shows_interval(session, start_datetime, end_datetime)

    for s in shows:
        if s.is_movie and s.year < 2010:
            continue

        tmdb_show = tmdb_calls.get_show_using_id(session, s.tmdb_id, s.is_movie)

        if tmdb_show:
            s.tmdb_vote_average = tmdb_show.vote_average
            s.tmdb_popularity = tmdb_show.popularity

            time.sleep(0.1)

    db_calls.commit(session)


def recover_password(session: sqlalchemy.orm.Session, recover_token: str, new_password: str):
    """
    Change the password of the user's account.

    :param session: the db session.
    :param recover_token: the recover token.
    :param new_password: the new password.
    :return: whether the deletion was success or not.
    """

    # Validate change token
    valid, user_id = authentication.validate_token(recover_token.encode(), authentication.TokenType.PASSWORD_RECOVERY)

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
    user = db_calls.get_user_id(session, user_id)

    # Check if the user was found
    if user is None:
        return {}

    # Get excluded channel list
    excluded_channel_list = db_calls.get_user_excluded_channels(session, user_id)
    current_excluded_channel_list = []

    for excluded_channel in excluded_channel_list:
        current_excluded_channel_list.append(excluded_channel.channel_id)

    return {'include_adult_channels': user.show_adult, 'language': user.language,
            'excluded_channel_list': current_excluded_channel_list}


def calculate_highlights_week(db_session: sqlalchemy.orm.Session, year: int, week: int):
    """
    Calculate the highlights for the current week and the week after.

    :param db_session: the DB session.
    :param year: the year.
    :param week: the week.
    """

    # Create only if the highlights does not exist
    highlights = db_calls.get_week_highlights(db_session, models.HighlightsType.SCORE, year, week)

    if highlights is None:
        # Update the information on the shows of the week of interest
        update_tmdb_data_week(db_session, year, week)

        # Calculate the highlights
        calculate_score_highlights_week(db_session, year, week)


def calculate_highlights(db_session: sqlalchemy.orm.Session):
    """
    Calculate the highlights for the current week and the week after.

    :param db_session: the DB session.
    """

    # Get the current week
    today = datetime.date.today()
    (year, week, _) = today.isocalendar()

    calculate_highlights_week(db_session, year, week)

    # Then the week after
    if week == 52:
        week = 1
        year = year + 1
    else:
        week = week + 1

    calculate_highlights_week(db_session, year, week)
