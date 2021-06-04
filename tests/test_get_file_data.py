import datetime
import os
import sys
import unittest.mock

import sqlalchemy.orm

import models

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

import tmdb_calls
import get_file_data

# To ensure the tests find the data folder no matter where it runs
if 'tests' in os.getcwd():
    base_path = ''
else:
    base_path = 'tests/'


class TestGetFileData(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()

    def test_delete_old_sessions(self) -> None:
        """ Test the function delete_old_sessions. """

        # The expected result
        expected_result = 2

        # Prepare the mocks
        # Prepare the call to search_old_sessions
        show_session_1 = models.ShowSession(None, None, datetime.datetime(2020, 1, 1), 5, 10)
        show_session_1.id = 1

        show_session_2 = models.ShowSession(1, 10, datetime.datetime(2020, 2, 2), 8, 25)
        show_session_2.id = 2

        db_calls_mock.search_old_sessions.return_value = [show_session_1, show_session_2]

        # Prepare the call to get_reminders_session for session 1 and session 2
        reminder_1 = models.Reminder(10, 1, 7)
        reminder_1.id = 1

        reminder_2 = models.Reminder(50, 1, 4)
        reminder_2.id = 2

        reminders_session_1 = [reminder_1, reminder_2]
        reminders_session_2 = []

        db_calls_mock.get_reminders_session.side_effect = [reminders_session_1, reminders_session_2]

        # Prepare the call to get_show_session_complete for session 1
        channel = models.Channel(None, 'Channel Name')

        show_data = models.ShowData('_Show_Name_', 'Show Name')
        show_data.is_movie = True

        complete_session = (show_session_1, channel, show_data)

        db_calls_mock.get_show_session_complete.return_value = complete_session

        # Prepare the call to get_user_id for reminder 1 and reminder 2
        user_7 = models.User('user7@email.com', 'password', 'pt')
        user_7.id = 7

        user_4 = models.User('user4@email.com', 'password', 'pt')
        user_4.id = 4

        db_calls_mock.get_user_id.side_effect = [user_7, user_4]

        # Prepare the call to send_deleted_sessions_email for user 7 and user 4
        process_emails_mock.send_deleted_sessions_email.return_value = True

        # Call the function
        start_datetime = datetime.datetime.utcnow() - datetime.timedelta(days=2)
        end_datetime = datetime.datetime.utcnow()
        channels = ['Odisseia']

        actual_result = get_file_data.delete_old_sessions(self.session, start_datetime, end_datetime, channels)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.search_old_sessions.assert_called_with(self.session, start_datetime, end_datetime, channels)
        db_calls_mock.get_reminders_session.assert_has_calls(
            [unittest.mock.call(self.session, 1), unittest.mock.call(self.session, 2)])
        db_calls_mock.get_show_session_complete.assert_called_with(self.session, 1)
        db_calls_mock.get_user_id.assert_has_calls(
            [unittest.mock.call(self.session, 7), unittest.mock.call(self.session, 4)])
        process_emails_mock.send_deleted_sessions_email.assert_has_calls(
            [unittest.mock.call('user7@email.com', unittest.mock.ANY),
             unittest.mock.call('user4@email.com', unittest.mock.ANY)])
        self.session.delete.assert_has_calls(
            [unittest.mock.call(reminder_1), unittest.mock.call(reminder_2), unittest.mock.call(show_session_1),
             unittest.mock.call(show_session_2)])

    @unittest.mock.patch('get_file_data.tmdb_calls')
    def test_search_tmdb_match_01(self, tmdb_calls_mock) -> None:
        """ Test the function search_tmdb_match with a match on a query with year. """

        # The expected result
        expected_result = tmdb_calls.TmdbShow()
        expected_result.year = 2020
        expected_result.is_movie = True
        expected_result.id = 2
        expected_result.original_title = 'Original Title'

        # Prepare the mocks
        # Prepare the call to search_shows_by_text
        tmdb_show_1 = tmdb_calls.TmdbShow()
        tmdb_show_1.year = 2020
        tmdb_show_1.is_movie = True
        tmdb_show_1.id = 1
        tmdb_show_1.original_title = 'Similar Title'

        tmdb_calls_mock.search_shows_by_text.return_value = (1, [tmdb_show_1, expected_result])

        # Prepare the call to get_show_crew_members for the show 1
        tmdb_calls_mock.get_show_crew_members.return_value = []

        # Call the function
        show_data = models.ShowData('_search_title', 'Localized Title')
        show_data.director = 'Director 1,Director 2'
        show_data.year = 2020
        show_data.genre = 'Documentary'
        show_data.original_title = 'Original Title'
        show_data.is_movie = True

        actual_result = get_file_data.search_tmdb_match(self.session, show_data, use_year=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        tmdb_calls_mock.search_shows_by_text.assert_called_with(self.session, 'Original Title', is_movie=True,
                                                                year=2020)

        tmdb_calls_mock.get_show_crew_members.assert_called_with(1, True)
