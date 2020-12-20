import datetime
import sys
import unittest.mock

import sqlalchemy.orm

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

# Configure a mock for the process_emails file
process_emails_mock = unittest.mock.MagicMock()
sys.modules['process_emails'] = process_emails_mock

import reminders
import models
import response_models


class TestReminders(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()

    def test_get_reminders_error_01(self) -> None:
        """ Test the function that obtains the list of reminders of a user, without a user. """

        # The expected result
        expected_result = []

        # Call the function
        actual_result = reminders.get_reminders(self.session, None)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_reminders_error_02(self) -> None:
        """ Test the function that obtains the list of reminders of a user, without reminders. """

        # The expected result
        expected_result = []

        # Prepare the mocks
        db_calls_mock.get_reminders_user.return_value = []

        # Call the function
        actual_result = reminders.get_reminders(self.session, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_reminders_user.assert_called_with(self.session, 1)

    def test_get_reminders_ok(self) -> None:
        """ Test the function that obtains the list of reminders of a user, with success. """

        # Prepare the mocks
        reminder_1 = models.Reminder(10, 1, 1)
        reminder_1.id = 1

        reminder_2 = models.Reminder(50, 2, 1)
        reminder_2.id = 2

        db_calls_mock.get_reminders_user.return_value = [reminder_1, reminder_2]

        response_reminder: response_models.Reminder = unittest.mock.MagicMock()
        response_reminder.anticipation_minutes = 10

        show_session = models.ShowSession(None, None, datetime.datetime(2020, 1, 1), 5, 10)
        complete_session = (show_session, 'Channel Name', 'Show Name', True)

        show_session_2 = models.ShowSession(None, None, datetime.datetime(2020, 2, 2), 15, 20)
        complete_session_2 = (show_session_2, 'Channel Name 2', 'Show Name 2', False)

        db_calls_mock.get_show_session_complete.side_effect = [complete_session, complete_session_2]

        # Call the function
        actual_result = reminders.get_reminders(self.session, 1)

        # Verify the result
        self.assertEqual(2, len(actual_result))

        self.assertEqual(1, actual_result[0].id)
        self.assertEqual('Show Name', actual_result[0].title)
        self.assertEqual(datetime.datetime(2020, 1, 1), actual_result[0].date_time)
        self.assertEqual(10, actual_result[0].anticipation_minutes)

        self.assertEqual(2, actual_result[1].id)
        self.assertEqual('Show Name 2', actual_result[1].title)
        self.assertEqual(datetime.datetime(2020, 2, 2), actual_result[1].date_time)
        self.assertEqual(50, actual_result[1].anticipation_minutes)

        # Verify the calls to the mocks
        db_calls_mock.get_reminders_user.assert_called_with(self.session, 1)
        db_calls_mock.get_show_session_complete.assert_has_calls(
            [unittest.mock.call(self.session, 1), unittest.mock.call(self.session, 2)])

    def test_register_reminder_error_01(self) -> None:
        """ Test the function that register a reminder, with an invalid session id. """

        # The expected result
        expected_result = None

        # Prepare the mocks
        db_calls_mock.get_show_session.return_value = None

        # Call the function
        actual_result = reminders.register_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_show_session.assert_called_with(self.session, 1)

    def test_register_reminder_error_02(self) -> None:
        """ Test the function that register a reminder, with a session that is airing in less than two hours. """

        # The expected result
        expected_result = None

        # Prepare the mocks
        show_session = models.ShowSession(None, None, datetime.datetime.now() + datetime.timedelta(hours=1), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        # Call the function
        actual_result = reminders.register_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_show_session.assert_called_with(self.session, 1)

    def test_register_reminder_error_03(self) -> None:
        """ Test the function that register a reminder, with the registration failing. """

        # The expected result
        expected_result = None

        # Prepare the mocks
        show_session = models.ShowSession(None, None, datetime.datetime.now() + datetime.timedelta(hours=4), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        db_calls_mock.register_reminder.return_value = None

        # Call the function
        actual_result = reminders.register_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_show_session.assert_called_with(self.session, 1)
        db_calls_mock.register_reminder.assert_called_with(self.session, 1, 60, 1)

    def test_register_reminder_ok(self) -> None:
        """ Test the function that register a reminder, with success. """

        # Prepare the mocks
        show_session = models.ShowSession(None, None, datetime.datetime.now() + datetime.timedelta(hours=4), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        reminder = models.Reminder(60, 1, 1)
        reminder.id = 123

        db_calls_mock.register_reminder.return_value = reminder

        # Call the function
        actual_result = reminders.register_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(123, actual_result.id)
        self.assertEqual(60, actual_result.anticipation_minutes)
        self.assertEqual(1, actual_result.session_id)
        self.assertEqual(1, actual_result.user_id)

        # Verify the calls to the mocks
        db_calls_mock.get_show_session.assert_called_with(self.session, 1)
        db_calls_mock.register_reminder.assert_called_with(self.session, 1, 60, 1)

    def test_process_reminders_ok_01(self) -> None:
        """ Test the function that processes reminders, with an empty list. """

        # Prepare the mocks
        db_calls_mock.get_sessions_reminders.return_value = []

        # Call the function
        reminders.process_reminders(self.session)

        # Verify the calls to the mocks
        db_calls_mock.get_sessions_reminders.assert_called_with(self.session)

    def test_process_reminders_ok_02(self) -> None:
        """ Test the function that processes reminders, with success. """

        # Prepare the mocks
        now = datetime.datetime.now()

        show_session_1 = models.ShowSession(None, None, now + datetime.timedelta(minutes=30), 5, 10)
        show_session_1.id = 1

        show_session_2 = models.ShowSession(2, 10, now + datetime.timedelta(minutes=100), 10, 15)
        show_session_2.id = 2

        show_session_3 = models.ShowSession(None, None, now + datetime.timedelta(days=15), 10, 10)
        show_session_3.id = 3

        reminder_1 = models.Reminder(60, 1, 1)
        reminder_session_1 = (reminder_1, show_session_1)

        reminder_2 = models.Reminder(120, 2, 2)
        reminder_session_2 = (reminder_2, show_session_2)

        reminder_3 = models.Reminder(60, 1, 2)
        reminder_session_3 = (reminder_3, show_session_1)

        # This session is still too far
        reminder_4 = models.Reminder(60, 3, 3)
        reminder_session_4 = (reminder_4, show_session_3)

        db_calls_mock.get_sessions_reminders.return_value = [reminder_session_1, reminder_session_2, reminder_session_3,
                                                             reminder_session_4]

        show_session_tuple_1 = (show_session_1, 'Channel 5', 'Show 10', True)
        show_session_tuple_2 = (show_session_2, 'Channel 10', 'Show 15', False)
        show_session_tuple_3 = (show_session_1, 'Channel 5', 'Show 10', True)

        db_calls_mock.get_show_session_complete.side_effect = [show_session_tuple_1, show_session_tuple_2,
                                                               show_session_tuple_3]

        db_calls_mock.get_user_id.side_effect = [models.User('email1@something.com', 'password', 'pt'),
                                                 models.User('email2@something.com', 'password', 'en'),
                                                 models.User('email2@something.com', 'password', 'en')]

        process_emails_mock.send_alarms_email.side_effect = [True, True, True]

        # Call the function
        reminders.process_reminders(self.session)

        # Verify the calls to the mocks
        db_calls_mock.get_sessions_reminders.assert_has_calls(self.session)

        db_calls_mock.get_show_session_complete.assert_has_calls([unittest.mock.call(self.session, 1),
                                                                  unittest.mock.call(self.session, 2),
                                                                  unittest.mock.call(self.session, 1)])

        db_calls_mock.get_user_id.assert_has_calls([unittest.mock.call(self.session, 1),
                                                    unittest.mock.call(self.session, 2),
                                                    unittest.mock.call(self.session, 2)])

        process_emails_mock.set_language.assert_has_calls([unittest.mock.call('pt'), unittest.mock.call('en'),
                                                           unittest.mock.call('en')])

        # Given that it can't compare the object sent in the email
        self.assertEqual(3, process_emails_mock.send_reminders_email.call_count)


if __name__ == '__main__':
    unittest.main()
