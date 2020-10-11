from enum import Enum

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

    id = Column(Integer, primary_key=True)
    pid = Column(Integer)
    series_id = Column(String(255))
    show_title = Column(String(255))
    show_season = Column(Integer)
    show_episode = Column(Integer)
    show_details = Column(String(255))
    date_time = Column(DateTime)
    duration = Column(Integer)
    search_title = Column(String(255))

    channel_id = Column(Integer, ForeignKey('Channel.id'))

    def __init__(self, pid, series_id, show_title, show_season, show_episode, show_details, date_time, duration,
                 channel_id, search_title):
        self.pid = pid
        self.series_id = series_id
        self.show_title = show_title
        self.show_season = show_season
        self.show_episode = show_episode
        self.show_details = show_details
        self.date_time = date_time
        self.duration = duration
        self.channel_id = channel_id
        self.search_title = search_title

    def __str__(self):
        return 'id: %d; pid: %d; series_id: %s; show_title: %s; show_season: %d; show_episode: %d; show_details: %s; ' \
               'date_time: %s; duration: %d; channel_id: %d; search_title: %s' % \
               (self.id, self.pid, self.series_id, self.show_title, self.show_season, self.show_episode,
                self.show_details, str(self.date_time), self.duration, self.channel_id, self.search_title)

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'pid': self.pid, 'series_id': self.series_id, 'show_title': self.show_title,
                'show_season': self.show_season, 'show_episode': self.show_episode, 'show_details': self.show_details,
                'date_time': self.date_time}


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
