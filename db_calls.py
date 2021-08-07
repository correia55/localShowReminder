import datetime
from typing import Optional, List, Tuple

import sqlalchemy.orm
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import auxiliary
import configuration
import models
import response_models


def clear_cache(session: sqlalchemy.orm.Session) -> None:
    """Delete invalid cache entries."""

    session.query(models.Cache).filter(models.Cache.date_time < datetime.date.today() -
                                       datetime.timedelta(days=configuration.cache_validity_days)).delete()
    session.commit()


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


def count_channel_sessions(session: sqlalchemy.orm.Session, channel_id: int):
    """
    Count the number of show sessions that a channel has.

    :param session: the db session.
    :param channel_id: the id of the show channel.
    :return: the count the number of show sessions that a channel has.
    """

    return session.query(models.ShowSession).filter(models.ShowSession.channel_id == channel_id).count()


def delete_reminder(session: sqlalchemy.orm.Session, reminder_id: int, user_id: int) -> bool:
    """
    Delete the reminder with the corresponding id.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param user_id: the id of the user.
    :return: True if the operation was a success.
    """

    # Get the reminder
    reminder = session.query(models.Reminder) \
        .filter(models.Reminder.id == reminder_id) \
        .filter(models.Reminder.user_id == user_id) \
        .first()

    if reminder is None:
        return False

    session.delete(reminder)
    session.commit()

    return True


def get_alarms(session: sqlalchemy.orm.Session) -> List[models.Alarm]:
    """
    Get all alarms.

    :param session: the db session.
    :return: all alarms.
    """

    return session.query(models.Alarm) \
        .all()


def get_cache(session: sqlalchemy.orm.Session, key: str) -> Optional[models.Cache]:
    """
    Get an entry of Cache.

    :param session: the db session.
    :param key: the key that represents a request.
    :return: the corresponding cache entry.
    """

    cache_entry = session.query(models.Cache) \
        .filter(models.Cache.key == key) \
        .first()

    if not cache_entry:
        return None

    current_date = datetime.datetime.utcnow()

    # Check if the entry is still valid
    if current_date > cache_entry.date_time + datetime.timedelta(days=configuration.cache_validity_days):
        session.delete(cache_entry)
        session.commit()

        return None

    return cache_entry


def get_channel_acronym(session: sqlalchemy.orm.Session, acronym: str) -> Optional[models.Channel]:
    """
    Get the channel with a given acronym.

    :param session: the db session.
    :param acronym: the acronym of the channel.
    :return: the channel.
    """

    return session.query(models.Channel) \
        .filter(models.Channel.acronym == acronym) \
        .first()


def get_channel_id(session: sqlalchemy.orm.Session, channel_id: int) -> Optional[models.Channel]:
    """
    Get the channel with a given id.

    :param session: the db session.
    :param channel_id: the id of the channel.
    :return: the channel.
    """

    return session.query(models.Channel) \
        .filter(models.Channel.id == channel_id) \
        .first()


def get_channel_list(session: sqlalchemy.orm.Session) -> List[models.Channel]:
    """
    Get the complete list of channels.

    :param session: the db session.
    :return: the channel list.
    """

    return session.query(models.Channel) \
        .all()


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


def get_epg_channel_list(session: sqlalchemy.orm.Session) -> List[models.Channel]:
    """
    Get the complete list of channels that should be requested to the EPG.

    :param session: the db session.
    :return: the channel list.
    """

    return session.query(models.Channel) \
        .filter(models.Channel.search_epg.is_(True)) \
        .all()


def get_highest_scored_shows_interval(session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                                      end_datetime: datetime.datetime, is_movie: bool) \
        -> List[Tuple[int, int, int]]:
    """
    Get the highest scored shows that have a session in the given interval.

    :param session: the db session.
    :param start_datetime: the start datetime.
    :param end_datetime: the end datetime.
    :param is_movie: whether or not it is a movie.
    :return: the list of shows (each represented by a tuple of the show id, the tmdb id and the vote average).
    """

    return session.query(sqlalchemy.func.distinct(models.ShowSession.show_id), models.ShowData.tmdb_id,
                         models.ShowData.tmdb_vote_average) \
        .filter(models.ShowSession.show_id == models.ShowData.id) \
        .filter(models.ShowSession.date_time >= start_datetime) \
        .filter(models.ShowSession.date_time <= end_datetime) \
        .filter(models.ShowData.is_movie == is_movie) \
        .filter(models.ShowData.tmdb_id.isnot(None)) \
        .order_by(models.ShowData.tmdb_vote_average.desc()) \
        .limit(configuration.score_highlight_counter) \
        .all()


def get_last_update(session: sqlalchemy.orm.Session) -> Optional[models.LastUpdate]:
    """
    Get the last update.

    :param session: the db session.
    :return: the LastUpdate.
    """

    return session.query(models.LastUpdate) \
        .first()


def get_new_shows_interval(session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                           end_datetime: datetime.datetime, is_movie: bool) \
        -> List[Tuple[int, int, datetime.date, int]]:
    """
    Get the new shows in the given interval.

    :param session: the db session.
    :param start_datetime: the start datetime.
    :param end_datetime: the end datetime.
    :param is_movie: whether or not it is a movie.
    :return: the list of shows (each represented by a tuple of the show id, the tmdb id, the premiere date and the
    season).
    """

    return session.query(sqlalchemy.func.distinct(models.ShowSession.show_id), models.ShowData.tmdb_id,
                         models.ShowData.premiere_date, models.ShowData.season_premiere) \
        .filter(models.ShowSession.show_id == models.ShowData.id) \
        .filter(models.ShowSession.date_time >= start_datetime) \
        .filter(models.ShowSession.date_time <= end_datetime) \
        .filter(models.ShowData.is_movie == is_movie) \
        .filter(models.ShowData.tmdb_id.isnot(None)) \
        .filter(models.ShowData.premiere_date >= start_datetime) \
        .filter(models.ShowData.premiere_date <= end_datetime) \
        .limit(configuration.new_highlight_counter) \
        .all()


def get_regex_operation_dbms() -> str:
    """
    Get the name of the operation that compares with regex, based on the current DBMS.

    :return: the name of the operation
    """

    if 'mysql' in configuration.database_url:
        return 'REGEXP'
    else:
        return '~*'


def get_reminder_id_user(session: sqlalchemy.orm.Session, reminder_id: int, user_id: int) -> models.Reminder:
    """
    Get the reminder with the given id, if it is the correct user.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param user_id: the id of the user.
    :return: the reminder.
    """

    return session.query(models.Reminder) \
        .filter(models.Reminder.id == reminder_id) \
        .filter(models.Reminder.user_id == user_id) \
        .first()


def get_reminders(session: sqlalchemy.orm.Session) -> List[models.Reminder]:
    """
    Get all reminders.

    :param session: the db session.
    :return: all reminders.
    """

    return session.query(models.Reminder) \
        .all()


def get_reminders_session(session: sqlalchemy.orm.Session, session_id: int) -> List[models.Reminder]:
    """
    Get a list of reminders for a given session.

    :param session: the db session.
    :param session_id: the id of the session.
    :return: a list of reminders for the user who's id is user_id.
    """

    return session.query(models.Reminder) \
        .filter(models.Reminder.session_id == session_id) \
        .all()


# TODO: IT ISN'T A TUPLE, BUT A sqlalchemy._util._collections.result
def get_reminders_user(session: sqlalchemy.orm.Session, user_id: int) -> List[models.Reminder]:
    """
    Get a list of reminders for the user who's id is user_id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: a list of reminders for the user who's id is user_id.
    """

    return session.query(models.Reminder) \
        .filter(models.Reminder.user_id == user_id) \
        .all()


def get_sessions_reminders(session: sqlalchemy.orm.Session) -> List[Tuple[models.Reminder, models.ShowSession]]:
    """
    Get all reminders and the corresponding sessions.

    :param session: the db session.
    :return: all reminders and the corresponding sessions.
    """

    return session.query(models.Reminder, models.ShowSession) \
        .filter(models.Reminder.session_id == models.ShowSession.id) \
        .all()


def get_show_data_by_tmdb_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) \
        -> Optional[models.ShowData]:
    """
    Get the show data with a given tmdb id.

    :param session: the db session.
    :param tmdb_id: the TMDB id.
    :param is_movie: whether it is a movie
    :return: the show data with that data.
    """

    return session.query(models.ShowData) \
        .filter(models.ShowData.tmdb_id == tmdb_id) \
        .filter(models.ShowData.is_movie == is_movie) \
        .first()


def get_show_data_id(session: sqlalchemy.orm.Session, show_data_id: int) -> Optional[models.ShowData]:
    """
    Get the ShowData with a given id.

    :param session: the db session.
    :param show_data_id: the id of the ShowData.
    :return: the ShowData.
    """

    return session.query(models.ShowData) \
        .filter(models.ShowData.id == show_data_id) \
        .first()


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


def get_show_session_complete(session: sqlalchemy.orm.Session, show_id: int) \
        -> Optional[Tuple[models.ShowSession, models.Channel, models.ShowData]]:
    """
    Get the show session, and all associated data, with a given id.

    :param session: the db session.
    :param show_id: the id of the show session.
    :return: the show session, and all associated data, with a given id.
    """

    query = session.query(models.ShowSession, models.Channel, models.ShowData).filter(models.ShowSession.id == show_id)

    # Join channels
    query = query.join(models.Channel)

    # Join show data
    query = query.join(models.ShowData)

    return query.first()


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


# TODO: IT ISN'T A TUPLE, BUT A sqlalchemy._util._collections.result
def get_show_sessions_show_id(session: sqlalchemy.orm.Session, show_id: int) \
        -> List[models.ShowSession]:
    """
    Get the sessions with a given show id.

    :param session: the db session.
    :param show_id: the show id.
    :return: the list of show sessions.
    """

    return session.query(models.ShowSession) \
        .filter(models.ShowSession.show_id == show_id) \
        .all()


def get_show_titles(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) -> Optional[models.ShowTitles]:
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the DB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: whether or not it is a movie.
    :return: the various possible titles.
    """

    return session.query(models.ShowTitles) \
        .filter(models.ShowTitles.tmdb_id == tmdb_id) \
        .filter(models.ShowTitles.is_movie == is_movie) \
        .first()


def get_shows_interval(session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                       end_datetime: datetime.datetime) \
        -> List[models.ShowData]:
    """
    Get the shows that have a session in a given interval.

    :param session: the db session.
    :param start_datetime: the start datetime.
    :param end_datetime: the end datetime.
    :return: the list of shows.
    """

    return session.query(models.ShowData) \
        .filter(models.ShowSession.show_id == models.ShowData.id) \
        .filter(models.ShowSession.date_time >= start_datetime) \
        .filter(models.ShowSession.date_time <= end_datetime) \
        .filter(models.ShowData.tmdb_id.isnot(None)) \
        .all()


def get_streaming_service_id(session: sqlalchemy.orm.Session, ss_id: int) -> Optional[models.StreamingService]:
    """
    Get the streaming service with a given id.

    :param session: the db session.
    :param ss_id: the id of the streaming service.
    :return: the streaming service.
    """

    return session.query(models.StreamingService) \
        .filter(models.StreamingService.id == ss_id) \
        .first()


def get_streaming_service_show(session: sqlalchemy.orm.Session, show_id: int) -> Optional[models.StreamingServiceShow]:
    """
    Get the streaming service show with a given id.

    :param session: the db session.
    :param show_id: the id of the streaming service show.
    :return: the streaming service show with a given id.
    """

    return session.query(models.StreamingServiceShow) \
        .filter(models.StreamingServiceShow.id == show_id) \
        .first()


def get_token(session: sqlalchemy.orm.Session, token: bytes) -> Optional[models.Token]:
    """
    Get a token.

    :param session: the db session.
    :param token: the token.
    :return: the corresponding token in the DB.
    """

    return session.query(models.Token).filter(models.Token.token == token.decode()).first()


def get_unmatched_show_data(session: sqlalchemy.orm.Session, limit: int) -> List[models.ShowData]:
    """
    Get the first x shows that do not have a TMDB match.

    :param session: the db session.
    :param limit: the limit for the number of shows.
    :return: the list of show data.
    """

    query = session.query(models.ShowData) \
        .filter(models.ShowData.original_title.isnot(None)) \
        .filter(models.ShowData.tmdb_id.is_(None)) \
        .limit(limit)

    return query.all()


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


def get_user_excluded_channels(session: sqlalchemy.orm.Session, user_id: int) -> List[models.UserExcludedChannel]:
    """
    Get a user's excluded channels.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: the list of show data.
    """

    query = session.query(models.UserExcludedChannel) \
        .filter(models.UserExcludedChannel.user_id == user_id)

    return query.all()


def get_user_id(session: sqlalchemy.orm.Session, user_id: int) -> Optional[models.User]:
    """
    Get the user with a given id.

    :param session: the db session.
    :param user_id: the id of the user.
    :return: the user.
    """

    return session.query(models.User) \
        .filter(models.User.id == user_id) \
        .first()


def get_week_highlights(session: sqlalchemy.orm.Session, key: models.HighlightsType, year: int, week: int) \
        -> Optional[models.Highlights]:
    """
    Get the Highlight entry for a given key and week.

    :param session: the db session.
    :param key: the highlight key.
    :param year: the year of interest.
    :param week: the week of interest.
    :return: the Highlight.
    """

    return session.query(models.Highlights) \
        .filter(models.Highlights.key == key.name) \
        .filter(models.Highlights.year == year) \
        .filter(models.Highlights.week == week) \
        .first()


def insert_if_missing_show_data(session: sqlalchemy.orm.Session, localized_title: str, original_title: str = None,
                                duration: int = None, synopsis: str = None, year: int = None, genre: str = None,
                                directors: List[str] = None, cast: str = None, audio_languages: str = None,
                                countries: str = None, age_classification: str = None, subgenre: Optional[str] = None,
                                is_movie: Optional[bool] = None, season: Optional[int] = None,
                                creators: List[str] = None, date_time: datetime.datetime = None) \
        -> [bool, Optional[models.ShowData]]:
    """
    Check, and return, if there's a matching entry of ShowData and, if not add it.

    :param session: the db session.
    :param original_title: the original title.
    :param localized_title: the localized title.
    :param duration: the duration.
    :param synopsis: the synopsis.
    :param year: the year of the show.
    :param genre: the type of show (movie, series, documentary, ...).
    :param directors: the directors of the show.
    :param cast: the cast of the show.
    :param audio_languages: the languages of the audio.
    :param countries: the countries.
    :param age_classification: the age classification.
    :param subgenre: the subgenre of the show (Comedy, thriller, ...).
    :param is_movie: True if it is a movie, False if it is TV.
    :param season: the season of the session from which the data comes from.
    :param creators: the list of creators.
    :param date_time: the date and time of the session.
    :return: a boolean for whether it is a new show or not and the corresponding show data.
    """

    # Check if there's already an entry with this information
    if original_title is not None:
        show_data = search_show_data_by_original_title(session, original_title, is_movie, directors=directors,
                                                       year=year, genre=genre, creators=creators)
    else:
        show_data = search_show_data_by_search_title_and_everything_else_empty(session, localized_title)

    if show_data is not None:
        return False, show_data

    if directors is not None:
        director = ','.join(directors)
    else:
        director = None

    if creators is not None:
        creators = ','.join(creators)

    if not is_movie and season != 1:
        year = None

    # If not, then add it
    return True, register_show_data(session, localized_title, original_title=original_title, duration=duration,
                                    synopsis=synopsis, year=year, genre=genre, director=director,
                                    cast=cast, audio_languages=audio_languages, countries=countries,
                                    age_classification=age_classification, subgenre=subgenre, is_movie=is_movie,
                                    creators=creators, season=season, date_time=date_time)


def register_alarm(session: sqlalchemy.orm.Session, show_name: str, trakt_id: int, is_movie: bool,
                   alarm_type: response_models.AlarmType, show_season, show_episode, user_id) \
        -> Optional[models.Alarm]:
    """
    Create an alarm for the given data.

    :param session: the db session.
    :param show_name: the name of the show.
    :param trakt_id: the trakt id of the show.
    :param is_movie: true if it is a movie.
    :param alarm_type: alarm type.
    :param show_season: show season for the alarm.
    :param show_episode: show episode for the alarm.
    :param user_id: the owner of the alarm.
    """

    if alarm_type == response_models.AlarmType.LISTINGS:
        alarm = session.query(models.Alarm) \
            .filter(models.Alarm.user_id == user_id) \
            .filter(models.Alarm.is_movie == is_movie) \
            .filter(models.Alarm.show_name == show_name).first()
    else:
        alarm = session.query(models.Alarm) \
            .filter(models.Alarm.user_id == user_id) \
            .filter(models.Alarm.trakt_id == trakt_id).first()

    # End processing if the alarm already exists
    if alarm is not None:
        return None

    if is_movie:
        show_season = None
        show_episode = None

    alarm = models.Alarm(show_name, trakt_id, is_movie, alarm_type.value, show_season, show_episode, user_id)
    session.add(alarm)

    try:
        session.commit()
        return alarm
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_cache(session: sqlalchemy.orm.Session, key: str,
                   request_result: str) -> Optional[models.Cache]:
    """
    Register an entry of Cache.

    :param session: the db session.
    :param key: the key that represents a request.
    :param request_result: the result of the request.
    :return: the created cache entry.
    """

    cache_entry = models.Cache(key, request_result)
    session.add(cache_entry)

    try:
        session.commit()
        return cache_entry
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


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


def register_channel_show_data_correction(session: sqlalchemy.orm.Session, channel_id: int, show_id: int,
                                          is_movie: bool, original_title: str, localized_title: str, year: int = None,
                                          directors: List[str] = None, subgenre: str = None,
                                          creators: List[str] = None) -> Optional[models.ChannelShowData]:
    """
    Register a ChannelShowData.
    Ignores the directors and year if the show is not a movie.

    :param session: the db session.
    :param channel_id: the id of the channel.
    :param show_id: the id of the ShowData.
    :param is_movie: whether or not it is a movie.
    :param original_title: the original title.
    :param localized_title: the localized title.
    :param year: the year of the show.
    :param directors: the directors of the show.
    :param subgenre: the subgenre.
    :param creators: the list of creators.
    :return: a boolean for whether it is a new show or not and the corresponding show data.
    """

    channel_show_data = models.ChannelShowData(channel_id, show_id, is_movie, original_title, localized_title)

    if is_movie:
        if directors is not None:
            channel_show_data.directors = ','.join(directors)

        if year is not None:
            channel_show_data.year = year

    if creators is not None:
        channel_show_data.creators = ','.join(creators)

    if subgenre is not None:
        channel_show_data.subgenre = subgenre

    session.add(channel_show_data)

    try:
        session.commit()
        return channel_show_data
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_highlights(session: sqlalchemy.orm.Session, key: models.HighlightsType, year: int, week: int,
                        id_list: [int], season_list: [int] = None) -> Optional[models.Highlights]:
    """
    Register a week's highlight list.

    :param session: the db session.
    :param key: the highlight key.
    :param year: the year of interest.
    :param week: the week of interest.
    :param id_list: the id list.
    :param season_list: the season list - only for NEW.
    :return: the Highlight, if successful.
    """

    if season_list is not None:
        if len(id_list) != len(season_list):
            print("The list of ids and seasons do not have the same size!")

    highlights = models.Highlights(key, year, week, id_list, season_list)
    session.add(highlights)

    try:
        session.commit()
        return highlights
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_reminder(session: sqlalchemy.orm.Session, show_session_id: int, anticipation_minutes: int,
                      user_id: int) -> Optional[models.Reminder]:
    """
    Register a reminder.

    :param session: the db session.
    :param show_session_id: the id of the show session.
    :param anticipation_minutes: the minutes before the show's session for the reminder.
    :param user_id: the id of the user.
    :return: the created reminder.
    """

    reminder = models.Reminder(anticipation_minutes, show_session_id, user_id)
    session.add(reminder)

    try:
        session.commit()
        return reminder
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_show_data(session: sqlalchemy.orm.Session, portuguese_title: str, original_title: str = None,
                       duration: int = None, synopsis: str = None, year: int = None, genre: str = None,
                       director: str = None, cast: str = None, audio_languages: str = None, countries: str = None,
                       age_classification: str = None, subgenre: Optional[str] = None, is_movie: Optional[bool] = None,
                       creators: str = None, season: int = None, date_time: datetime.datetime = None) \
        -> Optional[models.ShowData]:
    """
    Register an entry of ShowData.

    :param session: the db session.
    :param original_title: the original title.
    :param portuguese_title: the portuguese title.
    :param duration: the duration.
    :param synopsis: the synopsis.
    :param year: the year of the show.
    :param genre: the type of show (movie, series, documentary, ...).
    :param director: the director of the show.
    :param cast: the cast of the show.
    :param audio_languages: the languages of the audio.
    :param countries: the countries.
    :param age_classification: the age classification.
    :param subgenre: the subgenre of the show (Comedy, thriller, ...).
    :param is_movie: True if it is a movie, False if it is TV.
    :param creators: the list of creators separated by comma.
    :param season: the season of the session.
    :param date_time: the date and time of the session.
    :return: the created show data.
    """

    search_title = auxiliary.make_searchable_title(portuguese_title.strip())

    show_data = models.ShowData(search_title, portuguese_title.strip())

    # This can only happen in the UTs
    if date_time is not None:
        show_data.premiere_date = date_time.date()
        show_data.season_premiere = season

    if original_title is not None:
        show_data.original_title = original_title

    if year is not None:
        show_data.year = year

    if genre is not None:
        show_data.genre = genre

    if audio_languages is not None:
        show_data.audio_languages = audio_languages

    if countries is not None:
        show_data.countries = countries

    if age_classification is not None:
        show_data.age_classification = age_classification

    if subgenre is not None:
        show_data.subgenre = subgenre

    if is_movie is not None:
        show_data.is_movie = is_movie

    if is_movie is None or is_movie:
        if duration is not None:
            show_data.duration = duration

        if synopsis is not None:
            show_data.synopsis = synopsis

    if creators is not None:
        show_data.creators = creators

    # Even though the cast and director are only fixed for movies
    # we store them temporarily for searching the TMDB
    if director is not None:
        show_data.director = director

    if cast is not None:
        show_data.cast = cast

    session.add(show_data)

    try:
        session.commit()
        return show_data
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_show_session(session: sqlalchemy.orm.Session, season: Optional[int], episode: Optional[int],
                          date_time: datetime.datetime, channel_id: int, show_id: int, audio_language: str = None,
                          extended_cut: bool = False, should_commit: bool = True) -> Optional[models.ShowSession]:
    """
    Register a show session.

    :param session: the db session.
    :param season: the season of the show session.
    :param episode: the episode of the show session.
    :param date_time: the date and time of the show session.
    :param channel_id: the id of the channel where the show session will take place.
    :param show_id: the id of the corresponding show data (technical).
    :param audio_language: the audio language, None when it is the original one.
    :param extended_cut: whether or not this is the extended cut.
    :param should_commit: True it the data should be committed right away.
    :return: the created show session.
    """

    show_session = models.ShowSession(season, episode, date_time, channel_id, show_id, audio_language=audio_language,
                                      extended_cut=extended_cut)
    session.add(show_session)

    if should_commit:
        try:
            session.commit()
            return show_session
        except (IntegrityError, InvalidRequestError):
            session.rollback()
            return None
    else:
        return show_session


def register_show_titles(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool,
                         titles_str: str) -> Optional[models.ShowTitles]:
    """
    Register an entry of ShowTitles.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: whether it is a movie.
    :param titles_str: the string with the list of titles for the show.
    :return: the created ShowTitles.
    """

    show_titles = models.ShowTitles(tmdb_id, is_movie, titles_str)
    session.add(show_titles)

    try:
        session.commit()
        return show_titles
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_streaming_service(session: sqlalchemy.orm.Session, ss_name: str) -> Optional[models.StreamingService]:
    """
    Register a streaming service.

    :param session: the db session.
    :param ss_name: the name of the streaming service.
    :return: the created streaming service.
    """

    streaming_service = models.StreamingService(ss_name)
    session.add(streaming_service)

    try:
        session.commit()
        return streaming_service
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_streaming_service_show(session: sqlalchemy.orm.Session, first_season_available: Optional[int],
                                    last_season_available: Optional[int], original: bool, streaming_service_id: int,
                                    show_id: int, last_season_number_episodes: Optional[int] = None,
                                    should_commit: bool = True) -> Optional[models.StreamingServiceShow]:
    """
    Register a streaming service show.

    :param session: the db session.
    :param first_season_available: the first season available in the streaming service.
    :param last_season_available: the last season available in the streaming service.
    :param original: if this show is original to this streaming service.
    :param streaming_service_id: the id of the streaming service.
    :param show_id: the id of the corresponding show data (technical).
    :param last_season_number_episodes: the number of episodes available in the streaming service.
    :param should_commit: True it the data should be committed right away.
    :return: the created streaming service show.
    """

    if first_season_available is not None:
        if first_season_available > last_season_available:
            print('WARNING: First season must be equals or inferior to the last season!')
            return None

    ss_show = models.StreamingServiceShow(first_season_available, last_season_available, original, show_id,
                                          streaming_service_id, last_season_number_episodes)
    session.add(ss_show)

    if should_commit:
        try:
            session.commit()
            return ss_show
        except (IntegrityError, InvalidRequestError):
            session.rollback()
            return None
    else:
        return ss_show


def register_token(session: sqlalchemy.orm.Session, token: bytes) -> Optional[models.Token]:
    """
    Register a token.

    :param session: the db session.
    :param token: the token.
    :return: the created token.
    """

    token = models.Token(token.decode())
    session.add(token)

    try:
        session.commit()
        return token
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_user(session, email: str, password_hash: Optional[str], language: str = None,
                  account_type: models.AccountType = models.AccountType.EMAIL, verified: bool = False) \
        -> Optional[models.User]:
    """
    Register a user.

    :param session: the db session.
    :param email: the email of the user.
    :param password_hash: the password's hash.
    :param language: the language of the user.
    :param account_type: the account type of the user.
    :param verified: whether or not the user is created as verified.
    :return: the created user.
    """

    # Set the language for the user
    if language is None or language not in configuration.AVAILABLE_LANGUAGES:
        language = configuration.AvailableLanguage.PT.value

    user = models.User(email, password_hash, language, account_type=account_type, verified=verified)
    session.add(user)

    try:
        session.commit()
        return user
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def register_user_excluded_channel(session: sqlalchemy.orm.Session, user_id: int, channel_id: int,
                                   should_commit: bool = True) -> Optional[models.StreamingServiceShow]:
    """
    Register a user excluded channel.

    :param session: the db session.
    :param user_id: the id of the user.
    :param channel_id: the id of the channel.
    :param should_commit: True it the data should be committed right away.
    :return: the created object.
    """

    ss_show = models.UserExcludedChannel(user_id, channel_id)
    session.add(ss_show)

    if should_commit:
        try:
            session.commit()
            return ss_show
        except (IntegrityError, InvalidRequestError):
            session.rollback()
            return None
    else:
        return ss_show


def search_channel_show_data_correction(session: sqlalchemy.orm.Session, channel_id: int, is_movie: bool,
                                        original_title: str, localized_title: str, year: int = None,
                                        directors: List[str] = None, subgenre: str = None, creators: List[str] = None) \
        -> Optional[models.ChannelShowData]:
    """
    Check, and return, if there's a matching entry of a ChannelShowDataCorrection and, if not add it.
    Ignores the directors and year if the show is not a movie.

    :param session: the db session.
    :param channel_id: the id of the channel.
    :param is_movie: whether or not it is a movie.
    :param original_title: the original title.
    :param localized_title: the localized title.
    :param year: the year of the show.
    :param directors: the directors of the show.
    :param subgenre: the subgenre of the show.
    :param creators: the directors of the show.
    :return: the matching ChannelShowDataCorrection.
    """

    query = session.query(models.ChannelShowData) \
        .filter(models.ChannelShowData.channel_id == channel_id) \
        .filter(models.ChannelShowData.is_movie == is_movie) \
        .filter(models.ChannelShowData.original_title == original_title) \
        .filter(models.ChannelShowData.localized_title == localized_title)

    if is_movie:
        if directors is not None:
            query = query.filter(models.ChannelShowData.directors == ','.join(directors))

        if year is not None:
            query = query.filter(models.ChannelShowData.year == year)

    if creators is not None:
        query = query.filter(models.ChannelShowData.creators == ','.join(creators))

    if subgenre is not None:
        query = query.filter(models.ChannelShowData.subgenre == subgenre)

    # Checking if there's more than one match
    results = query.all()

    if len(results) > 0:
        if len(results) > 1:
            print('Warning: There were multiple matches for search_channel_show_data_correction: ' + repr(results[0]))

        return results[0]

    else:
        return None


def search_existing_session(session: sqlalchemy.orm.Session, season: Optional[int], episode: Optional[int],
                            date_time: datetime.datetime, channel_id: int, show_id: int) \
        -> Optional[models.ShowSession]:
    """
    Search if there's already a show session with the same data but whose schedule changed slightly.

    :param session: the db session.
    :param season: the season of the show session.
    :param episode: the episode of the show session.
    :param date_time: the date and time of the show session.
    :param channel_id: the id of the channel where the show session will take place.
    :param show_id: the id of the corresponding show data (technical).
    :return: the existing session.
    """

    start_datetime = date_time - datetime.timedelta(minutes=configuration.same_session_minutes)
    end_datetime = date_time + datetime.timedelta(minutes=configuration.same_session_minutes)

    query = session.query(models.ShowSession) \
        .filter(models.ShowSession.show_id == show_id) \
        .filter(models.ShowSession.season == season) \
        .filter(models.ShowSession.episode == episode) \
        .filter(models.ShowSession.channel_id == channel_id) \
        .filter(models.ShowSession.date_time >= start_datetime) \
        .filter(models.ShowSession.date_time <= end_datetime)

    return query.first()


def search_old_sessions(session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                        end_datetime: datetime.datetime, channels: List[str]) -> List[models.ShowSession]:
    """
    Search sessions that exist within the given interval and were last updated before 1 hour ago.

    :param session: the DB session.
    :param start_datetime: the start of the interval of interest.
    :param end_datetime: the end of the interval of interest.
    :param channels: the set of channels.
    """

    now = datetime.datetime.utcnow() - datetime.timedelta(hours=1)

    # Get the corresponding channel ids
    channels_ids = session.query(models.Channel.id) \
        .filter(models.Channel.name.in_(channels)) \
        .all()

    # Search the sessions
    query = session.query(models.ShowSession) \
        .filter(models.ShowSession.channel_id.in_(channels_ids)) \
        .filter(models.ShowSession.date_time >= start_datetime) \
        .filter(models.ShowSession.date_time <= end_datetime) \
        .filter(models.ShowSession.update_timestamp < now)

    return query.all()


def search_show_data_by_original_title(session: sqlalchemy.orm.Session, original_title: str, is_movie: bool,
                                       directors: List[str] = None, year: int = None, genre: str = None,
                                       creators: List[str] = None) -> Optional[models.ShowData]:
    """
    Search for the show data with the same original title and other parameters.

    :param session: the db session.
    :param original_title: the original title of the show.
    :param is_movie: whether or not it is a movie.
    :param directors: the directors of the show.
    :param year: the year of the show.
    :param genre: the genre of the show.
    :param creators: the creators of the show.
    :return: the show data with that data.
    """

    query = session.query(models.ShowData) \
        .filter(models.ShowData.is_movie == is_movie) \
        .filter(sqlalchemy.func.lower(models.ShowData.original_title) == original_title.lower())

    if is_movie:
        if directors is not None:
            query = query.filter(sqlalchemy.or_(models.ShowData.director.contains(d) for d in directors))

        if year is not None:
            query = query.filter(models.ShowData.year == year)

    if creators is not None:
        query = query.filter(sqlalchemy.or_(models.ShowData.creators.contains(c) for c in creators))

    if genre is not None:
        query = query.filter(models.ShowData.genre == genre)

    # Checking if there's more than one match
    results = query.all()

    if len(results) > 0:
        if len(results) > 1:
            print('Warning: There were multiple matches for search_show_data_by_original_title: ' + repr(results[0]))

        return results[0]

    else:
        return None


def search_show_data_by_search_title_and_everything_else_empty(session: sqlalchemy.orm.Session, portuguese_title: str) \
        -> Optional[models.ShowData]:
    """
    Search for the show data with the same search title and every other field empty.

    :param session: the db session.
    :param portuguese_title: the portuguese title.
    :return: the show data with that data.
    """

    search_title = auxiliary.make_searchable_title(portuguese_title.strip())

    # Can't use 'is' inside the filters, it needs to be '==' or 'is_'
    return session.query(models.ShowData) \
        .filter(models.ShowData.search_title == search_title) \
        .filter(models.ShowData.original_title.is_(None)) \
        .filter(models.ShowData.year.is_(None)) \
        .filter(models.ShowData.tmdb_id.is_(None)) \
        .first()


def search_show_sessions_data(session: sqlalchemy.orm.Session, search_pattern: str, is_movie: Optional[bool],
                              season: Optional[int], episode: Optional[int], search_adult: bool, complete_title: bool,
                              below_datetime: Optional[datetime.datetime] = None, ignore_with_tmdb_id: bool = False) \
        -> List[Tuple[models.ShowSession, models.Channel, models.ShowData]]:
    """
    Get the show sessions, and all associated data, that match a given search pattern and criteria.

    :param session: the db session.
    :param search_pattern: the search pattern.
    :param is_movie: True if the search is only for movies.
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param complete_title: whether it is a complete title or not.
    :param below_datetime: a datetime below to limit the search.
    :param ignore_with_tmdb_id: True if we want to ignore results that have a tmdb id.
    :return: the streaming service show with a given id.
    """

    if complete_title:
        query = session.query(models.ShowSession, models.Channel, models.ShowData) \
            .filter(models.ShowData.search_title == search_pattern)
    else:
        regex_operation = get_regex_operation_dbms()

        query = session.query(models.ShowSession, models.Channel, models.ShowData) \
            .filter(models.ShowData.search_title.op(regex_operation)(search_pattern))

    if is_movie:
        query = query.filter(sqlalchemy.or_(models.ShowData.is_movie.is_(None), models.ShowData.is_movie.is_(True)))
    else:
        if is_movie is not None:
            query = query.filter(
                sqlalchemy.or_(models.ShowData.is_movie.is_(None), models.ShowData.is_movie.is_(False)))

        if season is not None:
            query = query.filter(models.ShowSession.season == season)

        if episode is not None:
            query = query.filter(models.ShowSession.episode == episode)

    if not search_adult:
        query = query.filter(models.Channel.adult.is_(False))

    if below_datetime is not None:
        query = query.filter(models.ShowSession.update_timestamp > below_datetime)
        query = query.filter(models.ShowSession.date_time > datetime.datetime.utcnow())

    # Ignore shows that have a TMDB match
    if ignore_with_tmdb_id:
        query = query.filter(models.ShowData.tmdb_id.is_(None))

    # Join channels
    query = query.join(models.Channel)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def search_show_sessions_data_with_tmdb_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool,
                                           season: Optional[int], episode: Optional[int],
                                           below_datetime: Optional[datetime.datetime] = None) \
        -> List[Tuple[models.ShowSession, models.Channel, models.ShowData]]:
    """
    Search the show sessions, and all associated data, that match a tmdb_id.

    :param session: the db session.
    :param tmdb_id: the TMDB id.
    :param is_movie: whether it is a movie.
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param below_datetime: a datetime below to limit the search.
    :return: the show sessions associated with a given TMDB id.
    """

    query = session.query(models.ShowSession, models.Channel, models.ShowData) \
        .filter(models.ShowData.tmdb_id == tmdb_id) \
        .filter(models.ShowData.is_movie == is_movie)

    if season is not None:
        query = query.filter(models.ShowSession.season == season)

    if episode is not None:
        query = query.filter(models.ShowSession.episode == episode)

    if below_datetime is not None:
        query = query.filter(models.ShowSession.update_timestamp > below_datetime)
        query = query.filter(models.ShowSession.date_time > datetime.datetime.utcnow())

    # Join channels
    query = query.join(models.Channel)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def search_streaming_service_shows_data(session: sqlalchemy.orm.Session, search_pattern: str, is_movie: Optional[bool],
                                        season: Optional[int], episode: Optional[int], search_adult: bool,
                                        complete_title: bool, below_datetime: Optional[datetime.datetime] = None,
                                        ignore_with_tmdb_id: bool = False) \
        -> List[Tuple[models.ShowSession, models.StreamingService, models.ShowData]]:
    """
    Get the streaming services' shows, and all associated data, that match a given search pattern and criteria.

    :param session: the db session.
    :param search_pattern: the search pattern.
    :param is_movie: True if the search is only for movies.
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param complete_title: whether it is a complete title or not.
    :param below_datetime: a datetime below to limit the search.
    :param ignore_with_tmdb_id: True if we want to ignore results that have a tmdb id.
    :return: the streaming service show with a given id.
    """

    if complete_title:
        query = session.query(models.StreamingServiceShow, models.StreamingService, models.ShowData) \
            .filter(models.ShowData.search_title == search_pattern)
    else:
        regex_operation = get_regex_operation_dbms()

        query = session.query(models.StreamingServiceShow, models.StreamingService, models.ShowData) \
            .filter(models.ShowData.search_title.op(regex_operation)(search_pattern))

    if is_movie:
        query = query.filter(sqlalchemy.or_(models.ShowData.is_movie.is_(None), models.ShowData.is_movie.is_(True)))
    else:
        if is_movie is not None:
            query = query.filter(sqlalchemy.or_(models.ShowData.is_movie.is_(None),
                                                models.ShowData.is_movie.is_(False)))

        if season is not None:
            query = query.filter(models.StreamingServiceShow.first_season_available <= season)
            query = query.filter(models.StreamingServiceShow.last_season_available >= season)

            query = query.filter(sqlalchemy.or_(models.StreamingServiceShow.prev_first_season_available.is_(None),
                                                models.StreamingServiceShow.prev_first_season_available > season,
                                                models.StreamingServiceShow.prev_last_season_available < season))

        # TODO: FILTER THE EPISODE WHEN WE'RE SETTING THE NUMBER OF EPISODES OF THE LAST SEASON

    # TODO: SEARCH ADULT IF NEEDED

    if below_datetime is not None:
        query = query.filter(models.StreamingServiceShow.update_timestamp > below_datetime)

    # Ignore shows that have a TMDB match
    if ignore_with_tmdb_id:
        query = query.filter(models.ShowData.tmdb_id.is_(None))

    # Join channels
    query = query.join(models.StreamingService)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def search_streaming_service_shows_data_with_tmdb_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie:bool,
                                                     season: Optional[int], episode: Optional[int],
                                                     below_datetime: Optional[datetime.datetime] = None) \
        -> List[Tuple[models.ShowSession, models.StreamingService, models.ShowData]]:
    """
    Search the streaming services' shows, and all associated data, that match a given TMDB id.

    :param session: the db session.
    :param tmdb_id: the TMDB id.
    :param is_movie: whether it is a movie
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param below_datetime: a datetime below to limit the search.
    :return: the show sessions associated with a given TMDB id.
    """

    query = session.query(models.StreamingServiceShow, models.StreamingService, models.ShowData) \
        .filter(models.ShowData.tmdb_id == tmdb_id) \
        .filter(models.ShowData.is_movie == is_movie) \

    if season is not None:
        query = query.filter(models.StreamingServiceShow.first_season_available <= season)
        query = query.filter(models.StreamingServiceShow.last_season_available >= season)

        query = query.filter(sqlalchemy.or_(models.StreamingServiceShow.prev_first_season_available.is_(None),
                                            models.StreamingServiceShow.prev_first_season_available > season,
                                            models.StreamingServiceShow.prev_last_season_available < season))

    # TODO: FILTER THE EPISODE WHEN WE'RE SETTING THE NUMBER OF EPISODES OF THE LAST SEASON

    if below_datetime is not None:
        query = query.filter(models.StreamingServiceShow.update_timestamp > below_datetime)

    # Join channels
    query = query.join(models.StreamingService)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def update_reminder(session: sqlalchemy.orm.Session, reminder: models.Reminder, anticipation_minutes: int) \
        -> bool:
    """
    Update a reminder.

    :param session: the db session.
    :param reminder: the reminder.
    :param anticipation_minutes: the minutes before the show's session for the reminder.
    :return: True if the update was a success.
    """

    # Check if the reminder exists
    if reminder is None:
        return False

    # Check if there is a need for the update
    if anticipation_minutes == reminder.anticipation_minutes:
        return False

    reminder.anticipation_minutes = anticipation_minutes
    session.commit()

    return True


def update_show_sessions(session: sqlalchemy.orm.Session, current_show_id: int, new_show_id: int) \
        -> List[models.ShowSession]:
    """
    Change the show id of the sessions with a given show id.

    :param session: the db session.
    :param current_show_id: the current show id.
    :param new_show_id: the new show id.
    :return: the list of show sessions.
    """

    show_sessions = get_show_sessions_show_id(session, current_show_id)

    for ss in show_sessions:
        ss.show_id = new_show_id

    return show_sessions


def update_streaming_service_show(session: sqlalchemy.orm.Session, ss_show_id: int,
                                  first_season_available: Optional[int], last_season_available: Optional[int],
                                  should_commit: bool = True) -> bool:
    """
    Update a streaming service show.

    :param session: the db session.
    :param ss_show_id: the id of the streaming service show to be updated.
    :param first_season_available: the first season available in the streaming service.
    :param last_season_available: the last season available in the streaming service.
    :param should_commit: True it the data should be committed right away.
    :return: True if the operation was a success.
    """

    ss_show = get_streaming_service_show(session, ss_show_id)

    if ss_show is None:
        return False

    # Update the previous values with the current ones
    ss_show.prev_first_season_available = ss_show.first_season_available
    ss_show.prev_last_season_available = ss_show.last_season_available

    # Set the new values
    ss_show.first_season_available = first_season_available
    ss_show.last_season_available = last_season_available

    if should_commit:
        try:
            session.commit()
            return True
        except (IntegrityError, InvalidRequestError):
            session.rollback()
            return False
    else:
        return True
