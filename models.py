import datetime
from enum import Enum
from typing import Optional

import sqlalchemy
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base

# Base class for DB Classes
Base = declarative_base()


class AccountType(Enum):
    EMAIL = 0
    GOOGLE = 1


class ShowData(Base):
    """Used to store all the data associated with a show."""

    __tablename__ = 'ShowData'
    __table_args__ = (
        sqlalchemy.UniqueConstraint("search_title", "tmdb_id"),
    )

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id = Column(String(255), unique=True)
    search_title = Column(String(255))

    # Identifies to this show session
    is_movie = Column(Boolean)
    original_title = Column(String(255))
    portuguese_title = Column(String(255))
    number_seasons = Column(Integer)
    duration = Column(Integer)
    synopsis = Column(String(2000))
    year = Column(Integer)
    genre = Column(String(255))  # Movie, Series, Documentary, News, ...
    subgenre = Column(String(255))   # Comedy, Thriller, ...
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
    update_timestamp = Column(DateTime, default=datetime.datetime.now())

    # Foreign key
    show_id = Column(Integer, ForeignKey('ShowData.id'))
    channel_id = Column(Integer, ForeignKey('Channel.id'))

    # Specific this show session
    season = Column(Integer)
    episode = Column(Integer)
    date_time = Column(DateTime)
    audio_language = Column(String(255))
    extended_cut = Column(Boolean)

    def __init__(self, season: Optional[int], episode: Optional[int], date_time: datetime.datetime, channel_id: int,
                 show_id: int, audio_language: str = None, extended_cut: bool = False):
        self.channel_id = channel_id
        self.show_id = show_id

        self.season = season
        self.episode = episode
        self.date_time = date_time
        self.original_audio = audio_language
        self.extended_cut = extended_cut


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
    __table_args__ = (
        sqlalchemy.UniqueConstraint("show_data_id", "streaming_service_id"),
    )

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    update_timestamp = Column(DateTime, default=datetime.datetime.now())
    prev_first_season_available = Column(Integer)  # Used to store the previous first season, needed for the alarms
    prev_last_season_available = Column(Integer)  # Used to store the previous last season, needed for the alarms

    # Most important data
    first_season_available = Column(Integer)
    last_season_available = Column(Integer)
    last_season_number_episodes = Column(Integer)
    original = Column(Boolean)

    # Foreign keys
    show_data_id = Column(Integer, ForeignKey('ShowData.id'))
    streaming_service_id = Column(Integer, ForeignKey('StreamingService.id'))

    def __init__(self, first_season_available: int, last_season_available: int, original: bool, show_data_id: int,
                 streaming_service_id: int, last_season_number_episodes: int = None):
        self.first_season_available = first_season_available
        self.last_season_available = last_season_available
        self.original = original

        self.last_season_number_episodes = last_season_number_episodes

        self.show_data_id = show_data_id
        self.streaming_service_id = streaming_service_id


class User(Base):
    """Used to store the user's information."""

    __tablename__ = 'User'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    verified = Column(Boolean)
    account_type = Column(String(20))

    # Necessary
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=True)

    # Preferences
    show_adult = Column(Boolean)
    language = Column(String(5))

    def __init__(self, email: str, password: str, language: str, account_type: AccountType = AccountType.EMAIL,
                 verified: bool = False):
        self.verified = verified
        self.account_type = account_type.name

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
    """Used to store the data from the last update."""

    __tablename__ = 'LastUpdate'

    id = Column(Integer, primary_key=True, autoincrement=True)
    epg_date = Column(Date)
    alarms_datetime = Column(DateTime)

    def __init__(self, epg_date: datetime.date, reminders_datetime: datetime.datetime):
        self.epg_date = epg_date
        self.alarms_datetime = reminders_datetime


class Cache(Base):
    """Used as cache to all outside requests."""

    __tablename__ = 'Cache'

    key = Column(String(100), primary_key=True)
    result = Column(String(100000))
    date_time = Column(DateTime, default=datetime.datetime.now())

    def __init__(self, key: str, result: str):
        self.key = key
        self.result = result
