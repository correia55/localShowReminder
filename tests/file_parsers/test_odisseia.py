import datetime
import os
import sys
import unittest.mock
from typing import Type

import sqlalchemy.orm

import models

configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

# Configure a mock for the configuration file
from file_parsers.odisseia import Odisseia

# To ensure the tests find the data folder no matter where it runs
if 'tests' in os.getcwd():
    base_path = '../'
else:
    base_path = 'tests/'


# This class allows us to set a fake datetime as the today date in datetime
# Remark: they need to be set and then reset
class NewDatetime(datetime.datetime):
    @classmethod
    def utcnow(cls):
        return datetime.datetime(2021, 3, 1, 15, 13, 34)


class TestOdisseia(unittest.TestCase):
    session: sqlalchemy.orm.Session
    datetime_backup: Type[datetime.datetime]

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()
        configuration_mock.show_sessions_validity_days = 7

        # Save the datetime.date
        self.datetime_backup = datetime.datetime

    def tearDown(self) -> None:
        # Reset the datetime class to work normally
        datetime.date = self.datetime_backup

    def test_Odisseia_process_title_01(self) -> None:
        """ Test the function Odisseia.process_title with nothing in particular. """

        # The expected result
        expected_result = 'Attack and Defend'

        # Call the function
        actual_result = Odisseia.process_title('Attack and Defend')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Odisseia_process_title_02(self) -> None:
        """ Test the function Odisseia.process_title with quotation marks. """

        # The expected result
        expected_result = 'History\'s Greatest Lies'

        # Call the function
        actual_result = Odisseia.process_title('History´s Greatest Lies')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_Odisseia_add_file_data(self) -> None:
        """
        Test the function Odisseia.add_file_data with a new session of a show with a matching channel correction.
        An old event was added to show that nothing changes and it is ignored.
        """

        # Prepare the mocks
        # Replace datetime class with a utility class with a fixed today datetime
        datetime.datetime = NewDatetime

        # Prepare the call to get_channel_name
        channel_data = models.Channel('Acronym', 'Channel Name')
        channel_data.id = 8373

        db_calls_mock.get_channel_name.return_value = channel_data

        # Prepare the call to search_channel_show_data
        channel_show_data = models.ChannelShowData(8373, 2, False, 'Attack and Defend', 'Ataque e Defesa')
        channel_show_data.show_id = 51474

        db_calls_mock.search_channel_show_data_correction.return_value = channel_show_data

        # Prepare the call to get_show_data_id
        show_data = models.ShowData('Search Title', 'Localized Title')
        show_data.id = 51474

        db_calls_mock.get_show_data_id.return_value = show_data

        # Prepare the call to search_existing_session
        db_calls_mock.search_existing_session.return_value = None

        # Prepare the call to register_show_session
        show_session = models.ShowSession(1, 5, datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474)

        db_calls_mock.register_show_session.return_value = show_session

        # Prepare the call to search_old_sessions
        db_calls_mock.search_old_sessions.return_value = []

        # Call the function
        actual_result = Odisseia.add_file_data(self.session, base_path + 'data/odisseia_example.xml')

        # Verify the result
        self.assertEqual(datetime.datetime(2021, 3, 19, 5, 10, 16), actual_result.start_datetime)
        self.assertEqual(datetime.datetime(2021, 3, 19, 5, 20, 16), actual_result.end_datetime)
        self.assertEqual(1, actual_result.total_nb_sessions_in_file)
        self.assertEqual(0, actual_result.nb_updated_sessions)
        self.assertEqual(1, actual_result.nb_added_sessions)
        self.assertEqual(0, actual_result.nb_deleted_sessions)

        # Verify the calls to the mocks
        db_calls_mock.get_channel_name.assert_called_with(self.session, 'Odisseia')

        db_calls_mock.search_channel_show_data_correction.assert_called_with(self.session, 8373, False,
                                                                             'Attack and Defend', 'Ataque e Defesa',
                                                                             directors=['Seaton McLean'],
                                                                             year=2015, subgenre='Natureza',
                                                                             creators=None)

        db_calls_mock.get_show_data_id.assert_called_with(self.session, 51474)

        db_calls_mock.search_existing_session.assert_called_with(self.session, 1, 5,
                                                                 datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474)

        db_calls_mock.register_show_session.assert_called_with(self.session, 1, 5,
                                                               datetime.datetime(2021, 3, 19, 5, 15, 16), 8373, 51474,
                                                               audio_language=None, extended_cut=False,
                                                               should_commit=False)

        db_calls_mock.search_old_sessions.assert_called_with(self.session, datetime.datetime(2021, 3, 19, 5, 10, 16),
                                                             datetime.datetime(2021, 3, 19, 5, 20, 16), ['Odisseia'])
