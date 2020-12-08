import datetime
from enum import Enum
from typing import List, Optional

import sqlalchemy.orm

import auxiliary
import db_calls
import models


class AlarmType(Enum):
    LISTINGS = 0
    DB = 1


class Alarm:
    id: int
    show_name: str
    is_movie: bool
    alarm_type: AlarmType
    show_season: int
    show_episode: int
    show_titles: [str]

    def __init__(self, alarm: models.Alarm, titles: List[str]):
        """
        Create an instance using a DB alarm and a list of titles.

        :param alarm: the DB alarm.
        :param titles: the list of titles.
        """

        self.id = alarm.id
        self.show_name = alarm.show_name
        self.is_movie = alarm.is_movie
        self.alarm_type = AlarmType(alarm.alarm_type)
        self.show_season = alarm.show_season
        self.show_episode = alarm.show_episode
        self.show_titles = titles

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'show_name': self.show_name, 'is_movie': self.is_movie,
                'alarm_type': self.alarm_type.name,
                'show_season': self.show_season, 'show_episode': self.show_episode,
                'show_titles': self.show_titles}


class Reminder:
    id: int
    title: str
    date_time: datetime.datetime
    anticipation_minutes: int

    def __init__(self, session: sqlalchemy.orm.Session, reminder: models.Reminder):
        """
        Create an instance using a DB reminder.

        :param reminder: the DB reminder.
        """

        reminder_session = db_calls.get_show_session(session, reminder.show_id)

        self.id = reminder.id
        self.title = reminder_session.title
        self.date_time = reminder_session.date_time
        self.anticipation_minutes = reminder.anticipation_minutes

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'title': self.title, 'date_time': self.date_time,
                'anticipation_minutes': self.anticipation_minutes}


class LocalShowResultType(Enum):
    TV = 'TV'
    Streaming = 'Streaming'


class LocalShowResult:
    # Technical
    id: int
    type: LocalShowResultType  # TV or Streaming

    # Common to both types
    show_name: str
    service_name: str  # Channel name or Streaming Service name
    is_movie: Optional[bool]

    # TV
    season: Optional[int]
    episode: Optional[int]
    date_time: Optional[datetime.datetime]

    # Streaming
    first_season_available: Optional[int]
    last_season_available: Optional[int]

    @staticmethod
    def create_from_show_session(show_session: models.ShowSession, show_name: str, is_movie: Optional[bool],
                                 channel_name: str):
        """
        Create local show result from the a show session, the name of the show, whether it is a movie or not and the
        name of the channel.

        :param show_session: the corresponding session.
        :param show_name: the name of the show.
        :param is_movie: whether it is a movie or not.
        :param channel_name: the name of the channel.
        :return: the local show result.
        """

        local_show_result = LocalShowResult()
        local_show_result.id = show_session.id
        local_show_result.type = LocalShowResultType.TV

        local_show_result.show_name = show_name
        local_show_result.service_name = channel_name
        local_show_result.is_movie = is_movie

        local_show_result.season = show_session.season
        local_show_result.episode = show_session.episode
        local_show_result.date_time = show_session.date_time

        return local_show_result

    @staticmethod
    def create_from_streaming_service_show(ss_show: models.StreamingServiceShow, show_name: str,
                                           is_movie: Optional[bool],
                                           channel_name: str):
        """
        Create local show result from the a show session, the name of the show, whether it is a movie or not and the
        name of the channel.

        :param ss_show: the corresponding streaming service show.
        :param show_name: the name of the show.
        :param is_movie: whether it is a movie or not.
        :param channel_name: the name of the channel.
        :return: the local show result.
        """

        local_show_result = LocalShowResult()
        local_show_result.id = ss_show.id
        local_show_result.type = LocalShowResultType.Streaming

        local_show_result.show_name = show_name
        local_show_result.service_name = channel_name
        local_show_result.is_movie = is_movie

        local_show_result.first_season_available = ss_show.first_season_available
        local_show_result.last_season_available = ss_show.last_season_available

        return local_show_result

    def to_dict(self) -> dict:
        """
        Create a dictionary from the current object.

        :return: the corresponding dictionary.
        """

        local_show_dict = {'id': self.id, 'type': self.type.value, 'title': self.show_name,
                           'service': self.service_name}

        if self.is_movie:
            local_show_dict['is_movie'] = self.is_movie

        # TV
        if self.season:
            local_show_dict['season'] = self.season

        if self.season:
            local_show_dict['episode'] = self.episode

        if self.date_time:
            # Converts the date_time to UTC and formats it
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(self.date_time))
            local_show_dict['date_time'] = date_time.strftime("%Y-%m-%dT%H:%M:%S")

        # Streaming
        if self.first_season_available:
            local_show_dict['first_season_available'] = self.first_season_available

        if self.last_season_available:
            local_show_dict['last_season_available'] = self.last_season_available

        return local_show_dict
