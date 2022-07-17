import csv
import datetime
import os
from typing import Optional, Dict

import sqlalchemy.orm

import configuration


class GenericField:
    field_name: str
    field_format: str

    def __init__(self, field_name: str, field_format: str):
        self.field_name = field_name
        self.field_format = field_format


class InsertionResult:
    """To store the results of an insertion from a file."""

    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    total_nb_sessions_in_file: int
    nb_updated_sessions: int
    nb_added_sessions: int
    nb_deleted_sessions: int
    nb_new_shows: int

    def __init__(self):
        self.total_nb_sessions_in_file = 0
        self.nb_updated_sessions = 0
        self.nb_added_sessions = 0
        self.nb_deleted_sessions = 0
        self.nb_new_shows = 0


class AbstractChannelFileParser:
    channels: str

    @staticmethod
    def process_configuration(file_name: str) -> (Dict[str, GenericField], Dict[str, GenericField]):
        """
        Process the configurations file.

        :param file_name: the path to the file.
        :return: a tuple with a dictionary with the fields of interest and a dictionary with the configuration fields.
        """

        fields = dict()
        config = dict()

        with open(os.path.join(configuration.base_dir, 'file_parsers/channel_config', file_name)) as csvfile:
            content = csv.reader(csvfile, delimiter=';')

            # Skip the headers
            next(content, None)

            for row in content:

                if row[0].startswith('_'):
                    config[row[0]] = GenericField(row[1], row[2])
                else:
                    fields[row[1].lower()] = GenericField(row[0], row[2])

        return fields, config

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel.
        :return: the InsertionResult.
        """

        pass
