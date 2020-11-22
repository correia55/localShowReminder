import datetime
from enum import Enum

import sqlalchemy
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Date, DateTime
from sqlalchemy.ext.declarative import declarative_base

# Base class for DB Classes
Base = declarative_base()


class AvailableLanguage(Enum):
    PT = 'pt'
    EN = 'en'


AVAILABLE_LANGUAGES = [item.value for item in AvailableLanguage]


class LastUpdate(Base):
    """Used to know the last date of the data collected."""

    __tablename__ = 'LastUpdate'

    id = Column(Integer, primary_key=True)
    date = Column(Date)

    def __init__(self, date):
        self.date = date


class Channel(Base):
    __tablename__ = 'Channel'

    id = Column(Integer, primary_key=True)
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
        return 'id: %d; acronym: %s; name: %s; adult: %r; search_epg: %r' % (self.id, self.acronym, self.name,
                                                                      self.adult, self.search_epg)


class Show(Base):
    __tablename__ = 'Show'

    # Technical
    id = Column(Integer, primary_key=True)
    search_title = Column(String(255))

    # Foreign key
    channel_id = Column(Integer, ForeignKey('Channel.id'))

    # Identifies to this show session
    title = Column(String(255))
    season = Column(Integer)
    episode = Column(Integer)
    date_time = Column(DateTime)

    # Common to the show
    original_title = Column(String(255))
    duration = Column(Integer)
    synopsis = Column(String(500))
    year = Column(String(255))
    show_type = Column(String(255))  # Comedy, thriller, ...
    director = Column(String(255))
    cast = Column(String(255))
    languages = Column(String(255))
    countries = Column(String(255))
    age_classification = Column(String(255))
    episode_title = Column(String(255))

    def __init__(self, title, season, episode, synopsis, date_time, duration, channel_id, search_title,
                 original_title=None, year=None, show_type=None, director=None, cast=None, languages=None,
                 countries=None, age_classification=None, episode_title=None):
        self.search_title = search_title
        self.channel_id = channel_id

        self.title = title
        self.season = season
        self.episode = episode
        self.date_time = date_time

        self.synopsis = synopsis
        self.duration = duration

        # Optional fields
        self.original_title = original_title
        self.year = year
        self.show_type = show_type
        self.director = director
        self.cast = cast
        self.languages = languages
        self.countries = countries
        self.age_classification = age_classification
        self.episode_title = episode_title

    def __str__(self):
        return 'id: %d; title: %s; season: %s; episode: %s; synopsis: %s; ' \
               'date_time: %s; duration: %d; channel_id: %d; search_title: %s' % \
               (self.id, self.title, str(self.season), str(self.episode),
                self.synopsis, str(self.date_time), self.duration, self.channel_id, self.search_title)

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'title': self.title, 'season': self.season, 'episode': self.episode,
                'synopsis': self.synopsis, 'date_time': self.date_time}


class ShowMatch(Base):
    __tablename__ = 'ShowMatch'

    id = Column(Integer, primary_key=True)
    imdb_id = Column(String(255))
    show_id = Column(String(255))  # Corresponds to the show's series_id or pid, if the series_id is null
    verified = Column(Boolean)

    def __init__(self, imdb_id, show_id, verified=False):
        self.imdb_id = imdb_id
        self.show_id = show_id
        self.verified = verified


class DBReminder(Base):
    __tablename__ = 'DBReminder'

    id = Column(Integer, primary_key=True)

    show_name = Column(String(255), nullable=False)
    show_slug = Column(String(255), nullable=True)

    is_movie = Column(Boolean, nullable=False)
    reminder_type = Column(Integer, nullable=False)

    show_season = Column(Integer)
    show_episode = Column(Integer)

    user_id = Column(Integer, ForeignKey('User.id'))

    def __init__(self, show_name: str, is_movie: bool, reminder_type: int, show_season: int, show_episode: int,
                 user_id: int, show_slug: str):
        self.show_name = show_name
        self.is_movie = is_movie
        self.reminder_type = reminder_type
        self.show_season = show_season
        self.show_episode = show_episode
        self.user_id = user_id
        self.show_slug = show_slug


class Alarm(Base):
    __tablename__ = 'Alarm'
    __table_args__ = (
        sqlalchemy.UniqueConstraint("show_id", "user_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    anticipation_minutes = Column(Integer, nullable=False)

    show_id = Column(Integer, ForeignKey('Show.id'))
    user_id = Column(Integer, ForeignKey('User.id'))

    def __init__(self, anticipation_minutes: int, show_id: int, user_id: int):
        self.anticipation_minutes = anticipation_minutes
        self.show_id = show_id
        self.user_id = user_id

    def __eq__(self, o: object) -> bool:
        return self.anticipation_minutes == o.anticipation_minutes \
               and self.show_id == o.show_id \
               and self.user_id == o.user_id


class TraktTitle(Base):
    __tablename__ = 'TraktTitle'

    id = Column(Integer, primary_key=True, autoincrement=True)
    trakt_id = Column(String(255), nullable=False)
    is_movie = Column(Boolean, nullable=False)
    trakt_title = Column(String(255), nullable=False)

    def __init__(self, trakt_id, is_movie, trakt_title):
        self.trakt_id = trakt_id
        self.is_movie = is_movie
        self.trakt_title = trakt_title


class User(Base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)
    show_adult = Column(Boolean)
    verified = Column(Boolean)
    language = Column(String(5))

    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.show_adult = False
        self.verified = False
        self.language = AvailableLanguage.PT.value


class Token(Base):
    __tablename__ = 'Token'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(400), unique=True, nullable=False)

    def __init__(self, token):
        self.token = token
