import datetime

import sqlalchemy
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

# Base class for DB Classes
import auxiliary

Base = declarative_base()


class ShowData(Base):
    """Used to store all the date associated with a show."""

    __tablename__ = 'ShowData'
    __table_args__ = (
        sqlalchemy.UniqueConstraint("search_title", "tmdb_id"),
    )

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id = Column(String(255), unique=True)
    search_title = Column(String(255))

    # Identifies to this show session
    original_title = Column(String(255))
    portuguese_title = Column(String(255))
    number_seasons = Column(Integer)
    duration = Column(Integer)
    synopsis = Column(String(500))
    year = Column(Integer)
    category = Column(String(255))  # Movie, series, documentary, news, ...
    show_type = Column(String(255))  # Comedy, thriller, ...
    director = Column(String(255))
    cast = Column(String(255))
    audio_languages = Column(String(255))
    subtitle_languages = Column(String(255))
    countries = Column(String(255))
    age_classification = Column(String(255))

    def __init__(self, search_title: str, portuguese_title: str):
        self.search_title = search_title
        self.portuguese_title = portuguese_title


class ShowTitles(Base):
    """Used to store all of the titles associated with a tmdb id, for caching purposes."""

    __tablename__ = 'ShowTitles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True)
    titles = Column(String(1000), nullable=False)  # Titles separated by a vertical var (|)
    insertion_datetime = Column(DateTime, default=datetime.datetime.now())

    def __init__(self, trakt_id: int, titles: str):
        self.tmdb_id = trakt_id
        self.titles = titles


class Channel(Base):
    """Used to store all of the information associated with a TV channel."""

    __tablename__ = 'Channel'

    id = Column(Integer, primary_key=True, autoincrement=True)
    acronym = Column(String(255), unique=True)
    name = Column(String(255), unique=True)
    adult = Column(Boolean)
    search_epg = Column(Boolean)

    def __init__(self, acronym, name):
        self.acronym = acronym
        self.name = name
        self.adult = False
        self.search_epg = True

    def __str__(self):
        return 'id: %d; acronym: %s; name: %s; adult: %r; search_epg: %r' \
               % (self.id, self.acronym, self.name, self.adult, self.search_epg)


class ShowSession(Base):
    __tablename__ = 'ShowSession'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    show_id = Column(Integer, ForeignKey('ShowData.id'))
    channel_id = Column(Integer, ForeignKey('Channel.id'))

    # Identifies to this show session
    season = Column(Integer)
    episode = Column(Integer)
    date_time = Column(DateTime)

    def __init__(self, season: int, episode: int, date_time: datetime.datetime, channel_id: int, show_id: int):
        self.channel_id = channel_id
        self.show_id = show_id

        self.season = season
        self.episode = episode
        self.date_time = date_time

    def __str__(self):
        return 'id: %d; show_id: %d; season: %s; episode: %s; date_time: %s; channel_id: %d' % \
               (self.id, self.show_id, str(self.season), str(self.episode), str(self.date_time), self.channel_id)

    def to_dict(self, date_with_t_format=True) -> dict:
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        session_dict = {'id': self.id, 'season': self.season, 'episode': self.episode}

        if date_with_t_format:
            # Converts the date_time to UTC and formats it
            session_dict['date_time'] = auxiliary.convert_datetime_to_utc(
                auxiliary.get_datetime_with_tz_offset(self.date_time)).strftime("%Y-%m-%dT%H:%M:%S")
        else:
            session_dict['date_time'] = auxiliary.convert_datetime_to_utc(
                auxiliary.get_datetime_with_tz_offset(self.date_time))

        return session_dict


class StreamingService(Base):
    __tablename__ = 'StreamingService'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True)

    def __init__(self, name: str):
        self.name = name

    def __str__(self):
        return 'id: %d; name: %s;' % (self.id, self.name)


class StreamingServiceShow(Base):
    __tablename__ = 'StreamingServiceShow'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    update_timestamp = Column(DateTime, default=datetime.datetime.now())
    search_title = Column(String(255))

    # Most important data
    title = Column(String(255))
    seasons_available = Column(String(255))
    synopsis = Column(String(500))

    # Foreign keys
    show_data_id = Column(Integer, ForeignKey('ShowData.id'))
    streaming_service_id = Column(Integer, ForeignKey('StreamingService.id'))

    def __init__(self, search_title: str, title: str, seasons_available: str, synopsis: str, show_data_id: int,
                 streaming_service_id: int):
        self.search_title = search_title
        self.title = title
        self.seasons_available = seasons_available
        self.synopsis = synopsis
        self.show_data_id = show_data_id
        self.streaming_service_id = streaming_service_id


class User(Base):
    """Used to store the user's information."""

    __tablename__ = 'User'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    verified = Column(Boolean)

    # Necessary
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    # Preferences
    show_adult = Column(Boolean)
    language = Column(String(5))

    def __init__(self, email: str, password: str, language: str):
        self.verified = False

        self.email = email
        self.password = password

        self.show_adult = False
        self.language = language


class Alarm(Base):
    __tablename__ = 'Alarm'

    id = Column(Integer, primary_key=True, autoincrement=True)

    show_name = Column(String(255), nullable=False)
    trakt_id = Column(Integer)

    is_movie = Column(Boolean)
    alarm_type = Column(Integer, nullable=False)

    show_season = Column(Integer)
    show_episode = Column(Integer)

    user_id = Column(Integer, ForeignKey('User.id'))

    def __init__(self, show_name: str, trakt_id: int, is_movie: bool, alarm_type: int, show_season: int,
                 show_episode: int, user_id: int):
        self.show_name = show_name
        self.trakt_id = trakt_id

        self.is_movie = is_movie
        self.alarm_type = alarm_type

        self.show_season = show_season
        self.show_episode = show_episode

        self.user_id = user_id


class Reminder(Base):
    __tablename__ = 'Reminder'
    __table_args__ = (
        sqlalchemy.UniqueConstraint("session_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    anticipation_minutes = Column(Integer, nullable=False)

    session_id = Column(Integer, ForeignKey('ShowSession.id'))
    user_id = Column(Integer, ForeignKey('User.id'))

    def __init__(self, anticipation_minutes: int, session_id: int, user_id: int):
        self.anticipation_minutes = anticipation_minutes
        self.session_id = session_id
        self.user_id = user_id


class Token(Base):
    """Used to store user's valid refresh tokens."""

    __tablename__ = 'Token'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(400), unique=True, nullable=False)

    def __init__(self, token: str):
        self.token = token


class LastUpdate(Base):
    """Used to know the last date of the data collected."""

    __tablename__ = 'LastUpdate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(Date)

    def __init__(self, date: datetime.date):
        self.date = date


class Cache(Base):
    """Used as cache to all outside requests."""

    __tablename__ = 'Cache'

    key = Column(String(100), primary_key=True)
    result = Column(String(100000))
    date = Column(Date)

    def __init__(self, key: str, result: str):
        self.key = key
        self.result = result
        self.date = datetime.datetime.today()

    def __repr__(self):
        return 'key: %s; date: %s' % (self.key, str(self.date))
