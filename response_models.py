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
    match_reason: str  # Either id or name

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
        Create local show result from a show session, the name of the show, whether it is a movie or not and the
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

        if self.match_reason is not None:
            local_show_dict['match_reason'] = self.match_reason

        # TV
        if self.type == LocalShowResultType.TV:
            if self.season:
                local_show_dict['season'] = self.season

            if self.season:
                local_show_dict['episode'] = self.episode

            if self.date_time:
                local_show_dict['date_time'] = self.date_time.strftime("%Y-%m-%dT%H:%M:%S")

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


@auxiliary.auto_repr
class HighlightResponse:
    key = str  # Either SCORE or NEW
    year = int
    week = int  # The number of the week
    show_list: [dict]

    @staticmethod
    def create_from_highlight(db_highlight: models.Highlights):
        """
        Create a highlight from an entry in the Highlight table of the DB.

        :param db_highlight: the highlight entry from the DB.
        :return: the Highlight Response.
        """

        highlight_response = HighlightResponse()
        highlight_response.key = db_highlight.key
        highlight_response.year = db_highlight.year
        highlight_response.week = db_highlight.week
        highlight_response.show_list = []

        return highlight_response

    def to_dict(self) -> dict:
        """
        Create a dictionary from the current object.

        :return: the corresponding dictionary.
        """

        # Remark: the show_list already comes as a dict
        highlight_dict = {'key': self.key, 'year': self.year, 'week': self.week, 'show_list': self.show_list}

        return highlight_dict


@auxiliary.auto_repr
class TmdbShow(object):
    """The class that will represent the data in the response from a search to tmdb."""

    id: int
    original_title: str
    original_language: str
    popularity: float
    overview: str
    title: str
    vote_average: float
    vote_count: int
    is_movie: bool
    adult: bool
    genres: List[str]
    match_reason: str  # The matching reason, whether it is direct search, acting, directing...

    poster_path: Optional[str]
    origin_country: Optional[str]
    year: Optional[int]
    creators: List[str]

    def __init__(self):
        self.poster_path = None
        self.year = None
        self.origin_country = None
        self.adult = False
        self.genres = []
        self.creators = []
        self.popularity = None

    def fill_from_dict(self, show_dict: dict, is_movie: bool = None, match_reason: str = 'Name'):
        if is_movie is not None:
            self.is_movie = is_movie
        else:
            self.is_movie = show_dict['media_type'] == 'movie'

        if self.is_movie:
            self.original_title = show_dict['original_title']
            self.title = show_dict['title']

            if 'release_date' in show_dict and show_dict['release_date'] != '':
                self.year = int(show_dict['release_date'][0:4])
        else:
            self.original_title = show_dict['original_name']
            self.title = show_dict['name']

            if 'first_air_date' in show_dict and show_dict['first_air_date'] != '' \
                    and show_dict['first_air_date'] is not None:
                self.year = int(show_dict['first_air_date'][0:4])

            self.origin_country = show_dict['origin_country']

        self.id = int(show_dict['id'])
        self.vote_average = show_dict['vote_average']
        self.vote_count = show_dict['vote_count']
        self.original_language = show_dict['original_language']
        self.overview = show_dict['overview']
        self.match_reason = match_reason

        if 'popularity' in show_dict:
            self.popularity = show_dict['popularity']

        if 'genres' in show_dict:
            for g in show_dict['genres']:
                self.genres.append(g['name'])

        if 'adult' in show_dict:
            self.adult = show_dict['adult']

        if 'poster_path' in show_dict and show_dict['poster_path']:
            self.poster_path = 'https://image.tmdb.org/t/p/w220_and_h330_face' + show_dict['poster_path']

        if 'created_by' in show_dict:
            for c in show_dict['created_by']:
                self.creators.append(c['name'])

    def to_dict(self) -> dict:
        """
        Create a dictionary from the current object.

        :return: the corresponding dictionary.
        """

        show_dict = {'is_movie': self.is_movie, 'show_title': self.title, 'show_year': self.year, 'trakt_id': self.id,
                     'show_overview': self.overview, 'language': self.original_language,
                     'vote_average': self.vote_average, 'vote_count': self.vote_count,
                     'match_reason': self.match_reason}

        if self.popularity:
            show_dict['popularity'] = self.popularity

        if self.poster_path:
            show_dict['show_image'] = self.poster_path
        else:
            show_dict['show_image'] = 'N/A'

        return show_dict


class TmdbTranslation(object):
    """The class that will represent a tmdb translation."""

    tmdb_id: int
    title: str
    overview: str
    language_country: str

    def __init__(self):
        return

    def fill_from_dict(self, tmdb_id: int, translation_dict: dict, is_movie: bool = None):
        self.tmdb_id = tmdb_id

        self.language_country = '%s-%s' % (
            translation_dict['iso_639_1'], translation_dict['iso_3166_1'])  # pt-PT, en-US...

        data: dict = translation_dict['data']

        self.overview = data['overview']

        if is_movie:
            self.title = data['title']
        else:
            self.title = data['name']


class TmdbAlias(object):
    """The class that will represent a tmdb translation."""

    tmdb_id: int
    title: str
    country: str

    def __init__(self):
        return

    def fill_from_dict(self, tmdb_id: int, alias_dict: dict):
        self.tmdb_id = tmdb_id

        self.country = alias_dict['iso_3166_1']
        self.title = alias_dict['title']


class TmdbCrewMember(object):
    """The class that will represent a tmdb crew member."""

    name: str
    jobs: List[str]

    def __init__(self):
        return

    def fill_from_dict(self, crew_member_dict: dict, is_movie: bool):
        self.name = crew_member_dict['name']

        if is_movie:
            self.jobs = [crew_member_dict['job']]
        else:
            self.jobs = []

            for job in crew_member_dict['jobs']:
                self.jobs.append(job['job'])
