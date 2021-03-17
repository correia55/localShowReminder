import datetime
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

import get_file_data


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
        start_datetime = datetime.datetime.now() - datetime.timedelta(days=2)
        end_datetime = datetime.datetime.now()
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

    def test_TVCine_process_title_01(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VO)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Angry Birds Movie 2, The (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_02(self) -> None:
        """ Test the function TvCine.process_title with a title with "(VP)". """

        # The expected result
        expected_result = ('The Angry Birds Movie 2', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Angry Birds Movie 2, The (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_03(self) -> None:
        """ Test the function TvCine.process_title with the year in the title. """

        # The expected result
        expected_result = ('Endings, Beginnings', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Endings, Beginnings (2019)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_04(self) -> None:
        """ Test the function TvCine.process_title with an inverted section at the end. """

        # The expected result
        expected_result = ('A Beautiful Day In The Neighborhood', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Beautiful Day In The Neighborhood, A')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_05(self) -> None:
        """ Test the function TvCine.process_title with year and "VO". """

        # The expected result
        expected_result = ('Abominable', False, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Abominable (2019) (VO)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_06(self) -> None:
        """ Test the function TvCine.process_title with year and "VP". """

        # The expected result
        expected_result = ('Abominable', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Abominable (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_07(self) -> None:
        """ Test the function TvCine.process_title with year, "VP" and an inverted section. """

        # The expected result
        expected_result = ('The Addams Family', True, False)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Addams Family, The (2019) (VP)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_TVCine_process_title_08(self) -> None:
        """ Test the function TvCine.process_title with the extended cut. """

        # The expected result
        expected_result = ('Furious 7', False, True)

        # Call the function
        actual_result = get_file_data.TVCine.process_title('Furious 7 (extended cut)')

        # Verify the result
        self.assertEqual(expected_result, actual_result)


if __name__ == '__main__':
    unittest.main()
