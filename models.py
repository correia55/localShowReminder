from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Date, DateTime

# Base class for DB Classes
base = declarative_base()


class LastUpdate(base):
    """Used to know the last date of the data collected."""

    __tablename__ = 'LastUpdate'

    id = Column(Integer, primary_key=True)
    date = Column(Date)

    def __init__(self, date):
        self.date = date


class Channel(base):
    __tablename__ = 'Channel'

    id = Column(Integer, primary_key=True)
    pid = Column(Integer, unique=True)
    name = Column(String, unique=True)

    def __init__(self, pid, name):
        self.pid = pid
        self.name = name


class Show(base):
    __tablename__ = 'Show'

    id = Column(Integer, primary_key=True)
    pid = Column(Integer)
    series_id = Column(String)
    show_title = Column(String)
    show_season = Column(Integer)
    show_episode = Column(Integer)
    show_details = Column(String)
    date_time = Column(DateTime)
    duration = Column(Integer)

    channel_id = Column(Integer, ForeignKey('Channel.id'))

    def __init__(self, pid, series_id, show_title, show_season, show_episode, show_details, date_time, duration,
                 channel_id):
        self.pid = pid
        self.series_id = series_id
        self.show_title = show_title
        self.show_season = show_season
        self.show_episode = show_episode
        self.show_details = show_details
        self.date_time = date_time
        self.duration = duration
        self.channel_id = channel_id

    def __str__(self):
        return 'id: %d; pid: %d; series_id: %s; show_title: %s; show_season: %d; show_episode: %d; show_details: %s; ' \
               'date_time: %s; duration: %d; channel_id: %d' % \
               (self.id, self.pid, self.series_id, self.show_title, self.show_season, self.show_episode,
                self.show_details,str(self.date_time), self.duration, self.channel_id)


class ShowMatch(base):
    __tablename__ = 'ShowMatch'

    id = Column(Integer, primary_key=True)
    imdb_id = Column(Integer, unique=True)
    show_id = Column(Integer, unique=True)  # Corresponds to the show's series_id or pid, if the series_id is null
    verified = Column(Boolean)

    def __init__(self, imdb_id, show_id, verified=False):
        self.imdb_id = imdb_id
        self.show_id = show_id
        self.verified = verified
