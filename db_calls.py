import datetime
from typing import Optional, List

import sqlalchemy.orm
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import models
import response_models
from configuration import AVAILABLE_LANGUAGES, AvailableLanguage


def register_channel(session, acronym: str, name: str) -> Optional[models.Channel]:
    """
    Register a channel.

    :param session: the db session.
    :param acronym: the acronym.
    :param name: the name.
    :return: the created channel.
    """

    channel = models.Channel(acronym, name)
    session.add(channel)

    try:
        session.commit()
        return channel
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_channel_id(session: sqlalchemy.orm.Session, id: int) -> Optional[models.Channel]:
    """
    Get the channel with a given id.

    :param session: the db session.
    :param id: the id of the channel.
    :return: the channel.
    """

    return session.query(models.Channel) \
        .filter(models.Channel.id == id) \
        .first()


def get_channel_name(session: sqlalchemy.orm.Session, name: str) -> Optional[models.Channel]:
    """
    Get the channel with a given name.

    :param session: the db session.
    :param name: the name of the channel.
    :return: the channel.
    """

    return session.query(models.Channel) \
        .filter(models.Channel.name == name) \
        .first()


def register_user(session, email: str, password: str, language: str = None) -> Optional[models.User]:
    """
    Register a user.

    :param session: the db session.
    :param email: the email of the user.
    :param password: the password of the user.
    :param language: the language of the user.
    :return: the created user.
    """

    # Set the language for the user
    if language is None or language not in AVAILABLE_LANGUAGES:
        language = AvailableLanguage.PT.value

    user = models.User(email, password, language)
    session.add(user)

    try:
        session.commit()
        return user
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_user_id(session: sqlalchemy.orm.Session, id: int) -> Optional[models.User]:
    """
    Get the user with a given id.

    :param session: the db session.
    :param id: the id of the user.
    :return: the user.
    """

    return session.query(models.User) \
        .filter(models.User.id == id) \
        .first()


def get_user_email(session: sqlalchemy.orm.Session, email: str) -> Optional[models.User]:
    """
    Get the user with a given email.

    :param session: the db session.
    :param email: the email of the user.
    :return: the user.
    """

    return session.query(models.User) \
        .filter(models.User.email == email) \
        .first()


def register_reminder(session: sqlalchemy.orm.Session, show_name: str, trakt_id: int, is_movie: bool,
                      reminder_type: response_models.ReminderType, show_season, show_episode, user_id) \
        -> Optional[models.Reminder]:
    """
    Create a reminder for the given data.

    :param session: the db session.
    :param show_name: the name of the show.
    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :param reminder_type: reminder type.
    :param show_season: show season for the reminder.
    :param show_episode: show episode for the reminder.
    :param user_id: the owner of the reminder.
    """

    reminder = session.query(models.Reminder) \
        .filter(models.Reminder.user_id == user_id) \
        .filter(models.Reminder.is_movie == is_movie) \
        .filter(models.Reminder.show_name == show_name).first()

    # End processing if the reminder already exists
    if reminder is not None:
        return None

    if is_movie:
        show_season = None
        show_episode = None

    reminder = models.Reminder(show_name, trakt_id, is_movie, reminder_type.value, show_season, show_episode, user_id)
    session.add(reminder)

    try:
        session.commit()
        return reminder
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_reminders(session: sqlalchemy.orm.Session) -> List[models.Reminder]:
    """
    Get all reminders.

    :param session: the db session.
    :return: all reminders.
    """

    return session.query(models.Reminder) \
        .all()


def register_alarm(session: sqlalchemy.orm.Session, show_session_id: int, anticipation_minutes: int,
                   user_id: int) -> Optional[models.Alarm]:
    """
    Register an alarm.

    :param session: the db session.
    :param show_session_id: the id of the show session.
    :param anticipation_minutes: the minutes before the show's session for the alarm.
    :param user_id: the id of the user.
    :return: the created alarm.
    """

    alarm = models.Alarm(anticipation_minutes, show_session_id, user_id)
    session.add(alarm)

    try:
        session.commit()
        return alarm
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_alarms(session: sqlalchemy.orm.Session) -> List[models.Alarm]:
    """
    Get all alarms.

    :param session: the db session.
    :return: all alarms.
    """

    return session.query(models.Alarm) \
        .all()


def get_sessions_alarms(session: sqlalchemy.orm.Session) -> List:
    """
    Get all alarms and the corresponding sessions.

    :param session: the db session.
    :return: all alarms and the corresponding sessions.
    """

    return session.query(models.Alarm, models.Show) \
        .filter(models.Alarm.show_id == models.Show.id) \
        .all()


def get_alarms_user(session: sqlalchemy.orm.Session, user_id: int) -> List[models.Alarm]:
    """
    Get a list of alarms for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of alarms for the user who's id is user_id.
    """

    return session.query(models.Alarm) \
        .filter(models.Alarm.user_id == user_id) \
        .all()


def update_alarm(session: sqlalchemy.orm.Session, alarm_id: int, anticipation_minutes: int, user_id: int) -> bool:
    """
    Update an alarm.

    :param session: the db session.
    :param alarm_id: the id of the alarm.
    :param anticipation_minutes: the minutes before the show's session for the alarm.
    :param user_id: the id of the user.
    :return: True if the operation was a success.
    """

    # Get the alarm
    alarm = session.query(models.Alarm) \
        .filter(models.Alarm.id == alarm_id) \
        .filter(models.Alarm.user_id == user_id) \
        .first()

    # Check if the alarm exists
    if alarm is None:
        return False

    alarm.anticipation_minutes = anticipation_minutes
    session.commit()

    return True


def delete_alarm(session: sqlalchemy.orm.Session, alarm_id: int, user_id: int) -> bool:
    """
    Delete the alarm with the corresponding id.

    :param session: the db session.
    :param alarm_id: the id of the alarm.
    :param user_id: the id of the user.
    :return: True if the operation was a success.
    """

    # Get the alarm
    alarm = session.query(models.Alarm) \
        .filter(models.Alarm.id == alarm_id) \
        .filter(models.Alarm.user_id == user_id) \
        .first()

    if alarm is None:
        return False

    session.delete(alarm)
    session.commit()

    return True


def register_trakt_titles(session: sqlalchemy.orm.Session, trakt_id: int, titles_str: str) -> Optional[
    models.TraktTitles]:
    """
    Register an entry of TraktTitles.

    :param session: the db session.
    :param trakt_id: the trakt id of the show.
    :param titles_str: the string with the list of titles for the show.
    :return: the created TraktTitles.
    """

    trakt_titles = models.TraktTitles(trakt_id, titles_str)
    session.add(trakt_titles)

    try:
        session.commit()
        return trakt_titles
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_trakt_titles(session: sqlalchemy.orm.Session, trakt_id: int) -> models.TraktTitles:
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the DB.

    :param session: the db session.
    :param trakt_id: the trakt id of the show.
    :return: the various possible titles.
    """

    return session.query(models.TraktTitles) \
        .filter(models.TraktTitles.trakt_id == trakt_id) \
        .first()


def register_show_session(session: sqlalchemy.orm.Session, title: str, season: int, episode: int, synopsis: str,
                          date_time: datetime.datetime, duration: int, channel_id: int, search_title: str,
                          original_title: str = None, year: int = None, show_type: str = None, director: str = None,
                          cast: str = None, languages: str = None, countries: str = None,
                          age_classification: str = None, episode_title: str = None) -> Optional[models.ShowSession]:
    """
    Register a show session.

    :param session: the db session.
    :param title: the title of the show.
    :param season: the season of the show session.
    :param episode: the episode of the show session.
    :param synopsis: the synopsis of the show.
    :param date_time: the date and time of the show session.
    :param duration: the duration of the episode.
    :param channel_id: the id of the channel where the show session will take place.
    :param search_title: the title used for searches (technical).
    :param pid: the id of the program.
    :param series_id: the id of the series.
    :param original_title: the original title of the show.
    :param year: the year of the show.
    :param show_type: the type of show.
    :param director: the director of the show.
    :param cast: the cast of the show.
    :param languages: the languages of the show.
    :param countries: the countries of the show.
    :param age_classification: the age classification of the show.
    :param episode_title: the title of the episode of the show session.
    :return: the created show session.
    """

    show_session = models.Show(title, season, episode, synopsis, date_time, duration, channel_id, search_title,
                               original_title, year, show_type, director, cast, languages, countries,
                               age_classification, episode_title)
    session.add(show_session)

    try:
        session.commit()
        return show_session
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_show_sessions_channel(session: sqlalchemy.orm.Session, channel_id: int) -> List[models.Show]:
    """
    Get a list of sessions of a given channel.

    :param session: the db session.
    :param channel_id: the id of the channel.
    :return: a list of sessions of a given channel.
    """

    return session.query(models.Show) \
        .filter(models.Show.channel_id == channel_id) \
        .all()


def get_show_session(session: sqlalchemy.orm.Session, show_id: int) -> Optional[models.Show]:
    """
    Get the show session with a given id.

    :param session: the db session.
    :param show_id: the id of the show session.
    :return: the show session with a given id.
    """

    return session.query(models.Show) \
        .filter(models.Show.id == show_id) \
        .first()
