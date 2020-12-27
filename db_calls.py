import datetime
from typing import Optional, List, Tuple

import sqlalchemy.orm
from sqlalchemy.exc import IntegrityError, InvalidRequestError

import auxiliary
import configuration
import models
import response_models


def get_regex_operation_dbms() -> str:
    """
    Get the name of the operation that compares with regex, based on the current DBMS.

    :return: the name of the operation
    """

    if 'mysql' in configuration.database_url:
        return 'REGEXP'
    else:
        return '~*'


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


def register_user(session, email: str, password_hash: str, language: str = None) -> Optional[models.User]:
    """
    Register a user.

    :param session: the db session.
    :param email: the email of the user.
    :param password_hash: the password's hash.
    :param language: the language of the user.
    :return: the created user.
    """

    # Set the language for the user
    if language is None or language not in configuration.AVAILABLE_LANGUAGES:
        language = configuration.AvailableLanguage.PT.value

    user = models.User(email, password_hash, language)
    session.add(user)

    try:
        session.commit()
        return user
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


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

    alarm = session.query(models.Alarm) \
        .filter(models.Alarm.user_id == user_id) \
        .filter(models.Alarm.is_movie == is_movie) \
        .filter(models.Alarm.show_name == show_name).first()

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


def get_alarms(session: sqlalchemy.orm.Session) -> List[models.Alarm]:
    """
    Get all alarms.

    :param session: the db session.
    :return: all alarms.
    """

    return session.query(models.Alarm) \
        .all()


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


def get_reminders(session: sqlalchemy.orm.Session) -> List[models.Reminder]:
    """
    Get all reminders.

    :param session: the db session.
    :return: all reminders.
    """

    return session.query(models.Reminder) \
        .all()


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
def get_sessions_reminders(session: sqlalchemy.orm.Session) -> List[Tuple[models.Reminder, models.ShowSession]]:
    """
    Get all reminders and the corresponding sessions.

    :param session: the db session.
    :return: all reminders and the corresponding sessions.
    """

    return session.query(models.Reminder, models.ShowSession) \
        .filter(models.Reminder.session_id == models.ShowSession.id) \
        .all()


def update_reminder(session: sqlalchemy.orm.Session, reminder_id: int, anticipation_minutes: int,
                    user_id: int) -> bool:
    """
    Update a reminder.

    :param session: the db session.
    :param reminder_id: the id of the reminder.
    :param anticipation_minutes: the minutes before the show's session for the reminder.
    :param user_id: the id of the user.
    :return: True if the operation was a success.
    """

    # Get the reminder
    reminder = session.query(models.Reminder) \
        .filter(models.Reminder.id == reminder_id) \
        .filter(models.Reminder.user_id == user_id) \
        .first()

    # Check if the reminder exists
    if reminder is None:
        return False

    reminder.anticipation_minutes = anticipation_minutes
    session.commit()

    return True


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


def register_show_titles(session: sqlalchemy.orm.Session, tmdb_id: int, titles_str: str) -> Optional[models.ShowTitles]:
    """
    Register an entry of ShowTitles.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param titles_str: the string with the list of titles for the show.
    :return: the created ShowTitles.
    """

    show_titles = models.ShowTitles(tmdb_id, titles_str)
    session.add(show_titles)

    try:
        session.commit()
        return show_titles
    except (IntegrityError, InvalidRequestError):
        session.rollback()
        return None


def get_show_titles(session: sqlalchemy.orm.Session, tmdb_id: int) -> Optional[models.ShowTitles]:
    """
    Get the various possible titles for the selected title, in both english and portuguese, using the DB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :return: the various possible titles.
    """

    return session.query(models.ShowTitles) \
        .filter(models.ShowTitles.tmdb_id == tmdb_id) \
        .first()


def register_show_session(session: sqlalchemy.orm.Session, season: Optional[int], episode: Optional[int],
                          date_time: datetime.datetime, channel_id: int, show_id: int, should_commit: bool = True) \
        -> Optional[models.ShowSession]:
    """
    Register a show session.

    :param session: the db session.
    :param season: the season of the show session.
    :param episode: the episode of the show session.
    :param date_time: the date and time of the show session.
    :param channel_id: the id of the channel where the show session will take place.
    :param show_id: the id of the corresponding show data (technical).
    :param should_commit: True it the data should be committed right away.
    :return: the created show session.
    """

    show_session = models.ShowSession(season, episode, date_time, channel_id, show_id)
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
def get_show_session_complete(session: sqlalchemy.orm.Session, show_id: int) \
        -> Optional[Tuple[models.ShowSession, str, str, bool]]:
    """
    Get the show session, and all associated data, with a given id.

    :param session: the db session.
    :param show_id: the id of the show session.
    :return: the show session, and all associated data, with a given id.
    """

    query = session.query(models.ShowSession, models.Channel.name, models.ShowData.portuguese_title,
                          models.ShowData.is_movie).filter(models.ShowSession.id == show_id)

    # Join channels
    query = query.join(models.Channel)

    # Join show data
    query = query.join(models.ShowData)

    return query.first()


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

    # Can't use 'is' inside the filters, it needs to be '==' or 'is_'
    return session.query(models.ShowData) \
        .filter(models.ShowData.search_title == search_title) \
        .filter(models.ShowData.original_title.is_(None)) \
        .filter(models.ShowData.year.is_(None)) \
        .filter(models.ShowData.tmdb_id.is_(None)) \
        .first()


def register_show_data(session: sqlalchemy.orm.Session, portuguese_title: str, original_title: str = None,
                       duration: int = None, synopsis: str = None, year: int = None, show_type: str = None,
                       director: str = None, cast: str = None, audio_languages: str = None, countries: str = None,
                       age_classification: str = None, category: Optional[str] = None, is_movie: Optional[bool] = None) \
        -> Optional[models.ShowData]:
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
    :param category: the category of the show (movie, series, documentary, ...).
    :param is_movie: True if it is a movie, False if it is TV.
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

    if category is not None:
        show_data.category = category

    if is_movie is not None:
        show_data.is_movie = is_movie

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
                                countries: str = None, age_classification: str = None, category: Optional[str] = None,
                                is_movie: Optional[bool] = None) \
        -> Optional[models.ShowData]:
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
    :param category: the category of the show (movie, series, documentary, ...).
    :param is_movie: True if it is a movie, False if it is TV.
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
                              cast, audio_languages, countries, age_classification, is_movie)


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

    current_date = datetime.datetime.now()

    # Check if the entry is still valid
    if current_date > cache_entry.date_time + datetime.timedelta(days=configuration.cache_validity_days):
        session.delete(cache_entry)
        session.commit()

        return None

    return cache_entry


def clear_cache(session: sqlalchemy.orm.Session) -> None:
    """Delete invalid cache entries."""

    today = datetime.datetime.now().date()

    session.query(models.Cache).filter(models.Cache.date_time < today -
                                       datetime.timedelta(days=configuration.cache_validity_days)).delete()
    session.commit()


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


def get_token(session: sqlalchemy.orm.Session, token: bytes) -> Optional[models.Token]:
    """
    Get a token.

    :param session: the db session.
    :param token: the token.
    :return: the corresponding token in the DB.
    """

    return session.query(models.Token).filter(models.Token.token == token.decode()).first()


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


def search_show_sessions_data(session: sqlalchemy.orm.Session, search_pattern: str, is_movie: Optional[bool],
                              season: Optional[int], episode: Optional[int], search_adult: bool,
                              below_datetime: Optional[datetime.datetime] = None):
    """
    Get the show sessions, and all associated data, that match a given search pattern and criteria.

    :param session: the db session.
    :param search_pattern: the search pattern.
    :param is_movie: True if the search is only for movies.
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param below_datetime: a datetime below to limit the search.
    :return: the streaming service show with a given id.
    """

    regex_operation = get_regex_operation_dbms()

    query = session.query(models.ShowSession, models.Channel.name, models.ShowData.portuguese_title,
                          models.ShowData.is_movie) \
        .filter(models.ShowData.search_title.op(regex_operation)(search_pattern))

    if is_movie:
        query = query.filter(models.ShowData.is_movie.is_(True))
    else:
        if season is not None:
            query = query.filter(models.ShowSession.season == season)

        if episode is not None:
            query = query.filter(models.ShowSession.episode == episode)

    if not search_adult:
        query = query.filter(models.Channel.adult.is_(False))

    if below_datetime is not None:
        query = query.filter(models.ShowSession.update_timestamp > below_datetime)
        query = query.filter(models.ShowSession.date_time > datetime.datetime.now())

    # Join channels
    query = query.join(models.Channel)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def search_streaming_service_shows_data(session: sqlalchemy.orm.Session, search_pattern: str, is_movie: Optional[bool],
                                        season: Optional[int], episode: Optional[int], search_adult: bool,
                                        below_datetime: Optional[datetime.datetime] = None):
    """
    Get the streaming services' shows, and all associated data, that match a given search pattern and criteria.

    :param session: the db session.
    :param search_pattern: the search pattern.
    :param is_movie: True if the search is only for movies.
    :param season: to specify a season.
    :param episode: to specify an episode.
    :param search_adult: if it should also search in adult channels.
    :param below_datetime: a datetime below to limit the search.
    :return: the streaming service show with a given id.
    """

    regex_operation = get_regex_operation_dbms()

    query = session.query(models.StreamingServiceShow, models.StreamingService.name, models.ShowData.portuguese_title,
                          models.ShowData.is_movie) \
        .filter(models.ShowData.search_title.op(regex_operation)(search_pattern))

    if is_movie:
        query = query.filter(models.ShowData.is_movie.is_(True))
    else:
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

    # Join channels
    query = query.join(models.StreamingService)

    # Join show data
    query = query.join(models.ShowData)

    return query.all()


def get_last_update(session: sqlalchemy.orm.Session) -> Optional[models.LastUpdate]:
    """
    Get the last update.

    :param session: the db session.
    :return: the LastUpdate.
    """

    return session.query(models.LastUpdate) \
        .first()


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
