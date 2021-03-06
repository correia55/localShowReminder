import datetime
from enum import Enum
from typing import List, Optional, Tuple

import auxiliary
import models


class AlarmType(Enum):
    LISTINGS = 0
    DB = 1


class Alarm:
    id: int
    show_name: str
    show_id: str
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
        self.show_id = alarm.trakt_id
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
                'alarm_type': self.alarm_type.name, 'show_season': self.show_season, 'show_episode': self.show_episode,
                'show_titles': self.show_titles, 'show_id': self.show_id}


class Reminder:
    id: int
    anticipation_minutes: int
    session_id: int

    title: str
    season: int
    episode: int
    date_time: datetime.datetime

    channel_name: str

    def __init__(self, reminder: models.Reminder,
                 reminder_session_tuple: Tuple[models.ShowSession, models.Channel, models.ShowData]):
        """
        Create an instance using a reminder.

        :param reminder: the DB reminder.
        :param reminder_session_tuple: the tuple with all information on a reminder.
        """

        self.id = reminder.id
        self.anticipation_minutes = reminder.anticipation_minutes
        self.session_id = reminder.session_id

        self.title = reminder_session_tuple[2].portuguese_title
        self.season = reminder_session_tuple[0].season
        self.episode = reminder_session_tuple[0].episode
        self.date_time = reminder_session_tuple[0].date_time

        self.channel_name = reminder_session_tuple[1].name

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'anticipation_minutes': self.anticipation_minutes, 'session_id': self.session_id,
                'title': self.title, 'season': self.season, 'episode': self.episode, 'date_time': self.date_time,
                'channel_name': self.channel_name}


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
    year: Optional[int]
    extended_cut: Optional[bool]

    # TV
    season: Optional[int]
    episode: Optional[int]
    date_time: Optional[datetime.datetime]
    audio_language: Optional[str]

    # Streaming
    first_season_available: Optional[int]
    last_season_available: Optional[int]
    original: bool

    @staticmethod
    def create_from_show_session(show_session: models.ShowSession, channel: models.Channel, show_data: models.ShowData):
        """
        Create local show result from the a show session, the name of the show, whether it is a movie or not and the
        name of the channel.

        :param show_session: the corresponding session.
        :param channel: the corresponding channel.
        :param show_data: the corresponding show data.
        :return: the local show result.
        """

        local_show_result = LocalShowResult()
        local_show_result.id = show_session.id
        local_show_result.type = LocalShowResultType.TV

        local_show_result.show_name = show_data.portuguese_title
        local_show_result.service_name = channel.name
        local_show_result.is_movie = show_data.is_movie
        local_show_result.year = show_data.year

        local_show_result.season = show_session.season
        local_show_result.episode = show_session.episode
        local_show_result.date_time = show_session.date_time
        local_show_result.extended_cut = show_session.extended_cut
        local_show_result.audio_language = show_session.audio_language

        return local_show_result

    @staticmethod
    def create_from_streaming_service_show(ss_show: models.StreamingServiceShow,
                                           streaming_service: models.StreamingService, show_data: models.ShowData):
        """
        Create local show result from the a show session, the name of the show, whether it is a movie or not and the
        name of the channel.

        :param ss_show: the corresponding streaming service show.
        :param streaming_service: the corresponding stream service.
        :param show_data: the corresponding show data.
        :return: the local show result.
        """

        local_show_result = LocalShowResult()
        local_show_result.id = ss_show.id
        local_show_result.type = LocalShowResultType.Streaming

        local_show_result.show_name = show_data.portuguese_title
        local_show_result.service_name = streaming_service.name
        local_show_result.is_movie = show_data.is_movie
        local_show_result.year = show_data.year

        local_show_result.first_season_available = ss_show.first_season_available
        local_show_result.last_season_available = ss_show.last_season_available
        local_show_result.original = ss_show.original

        return local_show_result

    def to_dict(self) -> dict:
        """
        Create a dictionary from the current object.

        :return: the corresponding dictionary.
        """

        local_show_dict = {'id': self.id, 'type': self.type.value, 'title': self.show_name,
                           'service': self.service_name}

        if self.is_movie is not None:
            local_show_dict['is_movie'] = self.is_movie

        if self.year is not None:
            local_show_dict['year'] = self.year

        if self.extended_cut is not None:
            local_show_dict['extended_cut'] = self.extended_cut

        # TV
        if self.type == LocalShowResultType.TV:
            if self.season:
                local_show_dict['season'] = self.season

            if self.season:
                local_show_dict['episode'] = self.episode

            if self.date_time:
                # Converts the date_time to UTC and formats it
                date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(self.date_time))
                local_show_dict['date_time'] = date_time.strftime("%Y-%m-%dT%H:%M:%S")

            if self.audio_language:
                local_show_dict['audio_language'] = self.audio_language
        # Streaming
        else:
            if self.first_season_available:
                local_show_dict['first_season_available'] = self.first_season_available

            if self.last_season_available:
                local_show_dict['last_season_available'] = self.last_season_available

            local_show_dict['original'] = self.original

        return local_show_dict
