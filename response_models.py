from enum import Enum

from models import DBReminder


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

    def __init__(self, reminder: DBReminder, titles: [str]):
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
