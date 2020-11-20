import datetime
import sqlalchemy.orm
from enum import Enum

import db_calls
import models


class ReminderType(Enum):
    LISTINGS = 0
    DB = 1


class ShowReminder:
    id: int
    show_name: str
    is_movie: bool
    reminder_type: ReminderType
    show_season: int
    show_episode: int
    show_titles: [str]

    def __init__(self, reminder: models.DBReminder, titles: [str]):
        """
        Create an instance using a DB reminder and a list of titles.

        :param reminder: the DB reminder.
        :param titles: the list of titles.
        """

        self.id = reminder.id
        self.show_name = reminder.show_name
        self.is_movie = reminder.is_movie
        self.reminder_type = ReminderType(reminder.reminder_type)
        self.show_season = reminder.show_season
        self.show_episode = reminder.show_episode
        self.show_titles = titles

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'show_name': self.show_name, 'is_movie': self.is_movie,
                'reminder_type': self.reminder_type.name,
                'show_season': self.show_season, 'show_episode': self.show_episode,
                'show_titles': self.show_titles}


class Alarm:
    id: int
    title: str
    date_time: datetime.datetime
    anticipation_minutes: int

    def __init__(self, session: sqlalchemy.orm.Session, alarm: models.Alarm):
        """
        Create an instance using a DB Alarm.

        :param alarm: the DB alarm.
        """

        alarm_session = db_calls.get_show_session(session, alarm.show_id)

        self.id = alarm.id
        self.title = alarm_session.title
        self.date_time = alarm_session.date_time
        self.anticipation_minutes = alarm.anticipation_minutes

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'title': self.title, 'date_time': self.date_time,
                'anticipation_minutes': self.anticipation_minutes}
