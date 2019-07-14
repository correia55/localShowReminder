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
                self.show_details, str(self.date_time), self.duration, self.channel_id)

    # def to_dict(self):
    #     return {'id': self.id, 'pid': self.pid, 'series_id': self.series_id, 'show_title': self.show_title,
    #             'show_season': self.show_season, 'show_episode': self.show_episode, 'show_details': self.show_details,
    #             'date_time': self.date_time, 'duration': self.duration, 'channel_id': self.channel_id}

    def to_dict(self):
        return {'id': self.id, 'show_title': self.show_title,
                'show_season': self.show_season, 'show_episode': self.show_episode, 'show_details': self.show_details,
                'date_time': self.date_time}


class ShowMatch(base):
    __tablename__ = 'ShowMatch'

    id = Column(Integer, primary_key=True)
    imdb_id = Column(String)
    show_id = Column(String)  # Corresponds to the show's series_id or pid, if the series_id is null
    verified = Column(Boolean)

    def __init__(self, imdb_id, show_id, verified=False):
        self.imdb_id = imdb_id
        self.show_id = show_id
        self.verified = verified


class ShowReminder(base):
    __tablename__ = 'ShowReminder'

    id = Column(Integer, primary_key=True)

    # Corresponds to the show's series_id or pid, if the series_id is null
    show_id = Column(String, nullable=False)

    is_show = Column(Boolean, nullable=False)
    reminder_type = Column(Integer, nullable=False)

    show_season = Column(Integer)
    show_episode = Column(Integer)
    comparison_type = Column(Integer)

    def __init__(self, show_id, is_show, reminder_type, show_season, show_episode, comparison_type):
        self.show_id = show_id
        self.is_show = is_show
        self.reminder_type = reminder_type
        self.show_season = show_season
        self.show_episode = show_episode
        self.comparison_type = comparison_type

    def __str__(self):
        if self.show_season is None:
            show_season = -1
        else:
            show_season = self.show_season

        if self.show_episode is None:
            show_episode = -1
        else:
            show_episode = self.show_season

        if self.comparison_type is None:
            comparison_type = -1
        else:
            comparison_type = self.comparison_type

        return 'id: %d; show_id: %s; is_show: %r; reminder_type: %d; show_season: %d; show_episode: %d; ' \
               'comparison_type: %d' % \
               (self.id, self.show_id, self.is_show, self.reminder_type, show_season, show_episode, comparison_type)


class User(base):
    __tablename__ = 'User'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=False)
    password = Column(String(255), nullable=False)

    def __init__(self, email, password):
        self.email = email
        self.password = password


class Token(base):
    __tablename__ = 'Token'

    id = Column(Integer, primary_key=True, autoincrement=True)
    token = Column(String(400), unique=True, nullable=False)

    def __init__(self, token):
        self.token = token
