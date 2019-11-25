import json

from models import ReminderType


class ShowReminder:
    def __init__(self, id, show_id, is_show, reminder_type: ReminderType, show_season, show_episode, titles):
        self.id = id
        self.show_id = show_id
        self.is_show = is_show
        self.reminder_type = reminder_type
        self.show_season = show_season
        self.show_episode = show_episode
        self.show_titles = titles

    def to_dict(self):
        """
        Create a dictionary with all the information being sent in the responses to the API.

        :return: the corresponding dictionary.
        """

        return {'id': self.id, 'show_id': self.show_id, 'is_show': self.is_show, 'reminder_type': self.reminder_type.name,
                'show_season': self.show_season, 'show_episode': self.show_episode,
                'show_titles': json.dumps(self.show_titles, ensure_ascii=False)}
