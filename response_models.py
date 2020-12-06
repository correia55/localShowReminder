import datetime
from enum import Enum
from typing import List

import sqlalchemy.orm

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
