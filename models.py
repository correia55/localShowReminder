import datetime
from enum import Enum
from typing import Optional

import sqlalchemy
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, DateTime, Date
from sqlalchemy.ext.declarative import declarative_base

import auxiliary

# Base class for DB Classes
Base = declarative_base()


class AccountType(Enum):
    EMAIL = 0
    GOOGLE = 1


@auxiliary.auto_repr
class ShowData(Base):
    """Used to store all the data associated with a show."""

    __tablename__ = 'ShowData'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    search_title = Column(String(255))
    tmdb_id = Column(Integer, unique=True)

    # Present in all shows
    is_movie = Column(Boolean)
    original_title = Column(String(255))
    portuguese_title = Column(String(255))
    synopsis = Column(String(2000))
    year = Column(Integer)
    genre = Column(String(255))  # Movie, Series, Documentary, News, ...
    subgenre = Column(String(255))  # Comedy, Thriller, ...
    audio_languages = Column(String(255))  # Original
    countries = Column(String(255))
    age_classification = Column(String(255))

    # Only movies
    duration = Column(Integer)
    cast = Column(String(255))
    director = Column(String(255))

    # Only tv shows
    number_seasons = Column(Integer)
    creators = Column(String(255))

    # Highlights
    tmdb_vote_average = Column(Integer)
    tmdb_popularity = Column(Integer)
    premiere_date = Column(Date)
    season_premiere = Column(Integer)

    def __init__(self, search_title: str, portuguese_title: str):
        self.search_title = search_title
        self.portuguese_title = portuguese_title


class ShowTitles(Base):
    """Used to store all of the titles associated with a tmdb id, for caching purposes."""

    __tablename__ = 'ShowTitles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tmdb_id = Column(Integer, unique=True)
    titles = Column(String(1000), nullable=False)  # Titles separated by a vertical var (|)
    # TODO: DATE SHOULD BE ENOUGH
    insertion_datetime = Column(DateTime, default=datetime.datetime.utcnow())

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

    def to_dict(self) -> dict:
        """
        Create a dictionary from the current object.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'name': self.name, 'adult': self.adult}


@auxiliary.auto_repr
class ShowSession(Base):
    __tablename__ = 'ShowSession'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)
    update_timestamp = Column(DateTime, default=datetime.datetime.utcnow())

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


@auxiliary.auto_repr
class ChannelShowData(Base):
    """Used to store corrections on names of the shows for a given channel."""

    __tablename__ = 'ChannelShowData'

    # Technical
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Foreign key
    show_id = Column(Integer, ForeignKey('ShowData.id'))
    channel_id = Column(Integer, ForeignKey('Channel.id'))

    # Mandatory
    is_movie = Column(Boolean)
    original_title = Column(String(255))
    localized_title = Column(String(255))

    # Optional
    year = Column(Integer)
    directors = Column(String(255))
    creators = Column(String(255))
    subgenre = Column(String(255))

    def __init__(self, channel_id: int, show_id: int, is_movie: bool, original_title: str, localized_title: str):
        self.channel_id = channel_id
        self.show_id = show_id

        self.is_movie = is_movie
        self.original_title = original_title
        self.localized_title = localized_title


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
    update_timestamp = Column(DateTime, default=datetime.datetime.utcnow())
    prev_first_season_available = Column(Integer)  # Used to store the previous first season, needed for the alarms
    prev_last_season_available = Column(Integer)  # Used to store the previous last season, needed for the alarms

    # Most important data
    first_season_available = Column(Integer)
    last_season_available = Column(Integer)
    last_season_number_episodes = Column(Integer)
    original = Column(Boolean)  # Originally created by this Streaming Service
    audio_languages = Column(String(255))
    subtitle_languages = Column(String(255))

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


class UserExcludedChannel(Base):
    """Used to store the channels whose content the user does not care."""

    __tablename__ = 'UserExcludedChannel'

    user_id = Column(Integer, ForeignKey('User.id'), primary_key=True)
    channel_id = Column(Integer, ForeignKey('Channel.id'), primary_key=True)

    def __init__(self, user_id: int, channel_id: int):
        self.user_id = user_id
        self.channel_id = channel_id


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

    def __init__(self, epg_date: datetime.date, alarms_datetime: datetime.datetime):
        self.epg_date = epg_date
        self.alarms_datetime = alarms_datetime


class Cache(Base):
    """Used as cache to all outside requests."""

    __tablename__ = 'Cache'

    key = Column(String(200), primary_key=True)
    result = Column(String(100000))
    date_time = Column(DateTime, default=datetime.datetime.utcnow())

    def __init__(self, key: str, result: str):
        self.key = key
        self.result = result


class HighlightsType(Enum):
    SCORE = 0
    NEW = 1


class Highlights(Base):
    """Used to store the highlights of each week."""

    __tablename__ = 'Highlights'

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(50))  # Either Score or New
    year = Column(Integer)
    week = Column(Integer)  # The number of the week
    result_list_json = Column(String(50000))  # The list of pairs (id/season) in json

    def __init__(self, key: HighlightsType, year: int, week: int, id_list: [int], season_list: [int]):
        self.key = key.name
        self.year = year
        self.week = week

        # Combine the lists of ids and seasons and convert it to json
        self.result_list_json = '['

        for i in range(len(id_list)):
            show_id = id_list[i]

            if self.result_list_json != '[':
                self.result_list_json += ','

            self.result_list_json += '{"id":' + str(show_id)

            # Combine the list of seasons - only for NEW highlights
            if season_list is not None and season_list[i] is not None:
                self.result_list_json += ',"season":' + str(season_list[i])

            self.result_list_json += '}'

        self.result_list_json += ']'
