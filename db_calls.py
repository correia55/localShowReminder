import datetime
from typing import Optional, List

import sqlalchemy.orm
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import auxiliary
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


def get_sessions_alarms(session: sqlalchemy.orm.Session) -> List:
    """
    Get all alarms and the corresponding sessions.

    :param session: the db session.
    :return: all alarms and the corresponding sessions.
    """

    return session.query(models.Alarm, models.ShowSession) \
        .filter(models.Alarm.show_id == models.ShowSession.id) \
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


def register_show_session(session: sqlalchemy.orm.Session, season: int, episode: int, date_time: datetime.datetime,
                          channel_id: int, show_id: int, commit: bool = True) -> Optional[models.ShowSession]:
    """
    Register a show session.

    :param commit:
    :param session: the db session.
    :param season: the season of the show session.
    :param episode: the episode of the show session.
    :param date_time: the date and time of the show session.
    :param channel_id: the id of the channel where the show session will take place.
    :param show_id: the id of the corresponding show data (technical).
    :param commit: True it the data should be committed right away.
    :return: the created show session.
    """

    show_session = models.ShowSession(season, episode, date_time, channel_id, show_id)
    session.add(show_session)

    if commit:
        try:
            session.commit()
            return show_session
        except (IntegrityError, InvalidRequestError):
            session.rollback()
            return None
    else:
        return show_session


def get_show_sessions_channel(session: sqlalchemy.orm.Session, channel_id: int) -> List[models.ShowSession]:
    """
    Get a list of sessions of a given channel.

    :param session: the db session.
    :param channel_id: the id of the channel.
    :return: a list of sessions of a given channel.
    """

    return session.query(models.ShowSession) \
        .filter(models.ShowSession.channel_id == channel_id) \
        .all()


def get_show_session(session: sqlalchemy.orm.Session, show_id: int) -> Optional[models.ShowSession]:
    """
    Get the show session with a given id.

    :param session: the db session.
    :param show_id: the id of the show session.
    :return: the show session with a given id.
    """

    return session.query(models.ShowSession) \
        .filter(models.ShowSession.id == show_id) \
        .first()


def search_show_data_by_original_title_and_year(session: sqlalchemy.orm.Session, original_title: str, year: int) -> \
        Optional[models.ShowData]:
    """
    Search for the show data with the same original title and year.

    :param session: the db session.
    :param original_title: the original title of the show.
    :param year: the year of the show's release.
    :return: the show data with that data.
    """

    return session.query(models.ShowData) \
        .filter(models.ShowData.original_title == original_title) \
        .filter(models.ShowData.year == year) \
        .first()


def search_show_data_by_search_title_and_everything_else_empty(session: sqlalchemy.orm.Session, portuguese_title: str) \
        -> Optional[models.ShowData]:
    """
    Search for the show data with the same search title and every other field empty.

    :param session: the db session.
    :param portuguese_title: the portuguese title.
    :return: the show data with that data.
    """

    search_title = auxiliary.make_searchable_title(portuguese_title.strip())

    # Can't use 'is' inside the filters, it needs to be '=='
    return session.query(models.ShowData) \
        .filter(models.ShowData.search_title == search_title) \
        .filter(models.ShowData.original_title == None) \
        .filter(models.ShowData.year == None) \
        .filter(models.ShowData.imdb_id == None) \
        .first()


def register_show_data(session: sqlalchemy.orm.Session, portuguese_title: str, original_title: str = None,
                       duration: int = None, synopsis: str = None, year: int = None, show_type: str = None,
                       director: str = None, cast: str = None, audio_languages: str = None, countries: str = None,
                       age_classification: str = None) -> Optional[models.ShowData]:
    """
    Register an entry of ShowData.

    :param session: the db session.
    :param original_title: the original title.
    :param portuguese_title: the portuguese title.
    :param duration: the duration.
    :param synopsis: the synopsis.
    :param year: the year of the show.
    :param show_type: the type of show (Comedy, thriller, ...).
    :param director: the director of the show.
    :param cast: the cast of the show.
    :param audio_languages: the languages of the audio.
    :param countries: the countries.
    :param age_classification: the age classification.
    :return: the created show data.
    """

    search_title = auxiliary.make_searchable_title(portuguese_title.strip())

    show_data = models.ShowData(search_title, portuguese_title.strip())

    if original_title is not None:
        show_data.original_title = original_title

    if duration is not None:
        show_data.duration = duration

    if synopsis is not None:
        show_data.synopsis = synopsis

    if year is not None:
        show_data.year = year

    if show_type is not None:
        show_data.show_type = show_type

    if director is not None:
        show_data.director = director

    if cast is not None:
        show_data.cast = cast

    if audio_languages is not None:
        show_data.audio_languages = audio_languages

    if countries is not None:
        show_data.countries = countries

    if age_classification is not None:
        show_data.age_classification = age_classification

    session.add(show_data)

    try:
        session.commit()
        return show_data
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def insert_if_missing_show_data(session: sqlalchemy.orm.Session, portuguese_title: str, original_title: str = None,
                                duration: int = None, synopsis: str = None, year: int = None, show_type: str = None,
                                director: str = None, cast: str = None, audio_languages: str = None,
                                countries: str = None, age_classification: str = None) -> Optional[models.ShowData]:
    """
    Check, and return, if there's a matching entry of ShowData and, if not add it.

    :param session: the db session.
    :param original_title: the original title.
    :param portuguese_title: the portuguese title.
    :param duration: the duration.
    :param synopsis: the synopsis.
    :param year: the year of the show.
    :param show_type: the type of show (Comedy, thriller, ...).
    :param director: the director of the show.
    :param cast: the cast of the show.
    :param audio_languages: the languages of the audio.
    :param countries: the countries.
    :param age_classification: the age classification.
    :return: the corresponding show data.
    """

    # Check if there's already an entry with this information
    if original_title is not None and year is not None:
        show_data = search_show_data_by_original_title_and_year(session, original_title, year)
    else:
        show_data = search_show_data_by_search_title_and_everything_else_empty(session, portuguese_title)

    if show_data is not None:
        return show_data

    # If not, then add it
    return register_show_data(session, portuguese_title, original_title, duration, synopsis, year, show_type, director,
                              cast, audio_languages, countries, age_classification)


def commit(session: sqlalchemy.orm.Session) -> bool:
    """
    Commit the session.

    :param session: the db session.
    :return: True if it succeeded.
    """

    try:
        session.commit()
        return True
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return False
