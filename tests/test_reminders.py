import datetime
import unittest.mock

import globalsub
import sqlalchemy.orm

import db_calls
import models
import process_emails
import reminders
import response_models

# Prepare the mock variables for the modules
db_calls_mock = unittest.mock.MagicMock()
process_emails_mock = unittest.mock.MagicMock()


class TestReminders(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = unittest.mock.MagicMock()

    @classmethod
    def setUpClass(cls) -> None:
        global db_calls_mock, process_emails_mock

        # Replace all references to the modules with mocks
        globalsub.subs(db_calls, db_calls_mock)
        globalsub.subs(process_emails, process_emails_mock)

    @classmethod
    def tearDownClass(cls) -> None:
        # Replace back all references to the mocked modules
        globalsub.restore(db_calls)
        globalsub.restore(process_emails)

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
        channel = models.Channel(None, 'Channel Name')

        show_data = models.ShowData('_Show_Name_', 'Show Name')
        show_data.is_movie = True

        complete_session = (show_session, channel, show_data)

        show_session_2 = models.ShowSession(None, None, datetime.datetime(2020, 2, 2), 15, 20)
        channel_2 = models.Channel(None, 'Channel Name 2')

        show_data_2 = models.ShowData('_Show_Name_2_', 'Show Name 2')
        show_data_2.is_movie = False

        complete_session_2 = (show_session_2, channel_2, show_data_2)

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
        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=1), 1, 1)
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
        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=4), 1, 1)
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
        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=4), 1, 1)
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

    def test_update_reminder_error_01(self) -> None:
        """ Test the function update_reminder with an reminder id or user id. """

        # The expected result
        expected_result = False, 'Not found'

        # Prepare the mocks
        db_calls_mock.get_reminder_id_user.return_value = None

        # Call the function
        actual_result = reminders.update_reminder(self.session, -1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_reminder_id_user.assert_called_with(self.session, -1, 1)

    def test_update_reminder_error_02(self) -> None:
        """ Test the function update_reminder with anticipation in less than two hours from airing. """

        # The expected result
        expected_result = False, 'Invalid anticipation time'

        # Prepare the mocks
        reminder = models.Reminder(60, 15, 1)
        reminder.id = 123

        db_calls_mock.get_reminder_id_user.return_value = reminder

        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=1), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        # Call the function
        actual_result = reminders.update_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_reminder_id_user.assert_called_with(self.session, 1, 1)
        db_calls_mock.get_show_session.assert_called_with(self.session, 15)

    def test_update_reminder_error_03(self) -> None:
        """ Test the function update_reminder with the same anticipation time. """

        # The expected result
        expected_result = False, 'Same anticipation time'

        # Prepare the mocks
        reminder = models.Reminder(60, 15, 1)
        reminder.id = 123

        db_calls_mock.get_reminder_id_user.return_value = reminder

        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=4), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        db_calls_mock.update_reminder.return_value = False

        # Call the function
        actual_result = reminders.update_reminder(self.session, 1, 60, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_reminder_id_user.assert_called_with(self.session, 1, 1)
        db_calls_mock.get_show_session.assert_called_with(self.session, 15)
        db_calls_mock.update_reminder.assert_called()

    def test_update_reminder_ok(self) -> None:
        """ Test the function update_reminder with success. """

        # The expected result
        expected_result = True, None

        # Prepare the mocks
        reminder = models.Reminder(60, 15, 1)
        reminder.id = 123

        db_calls_mock.get_reminder_id_user.return_value = reminder

        show_session = models.ShowSession(None, None, datetime.datetime.utcnow() + datetime.timedelta(hours=5), 1, 1)
        db_calls_mock.get_show_session.return_value = show_session

        db_calls_mock.update_reminder.return_value = True

        # Call the function
        actual_result = reminders.update_reminder(self.session, 1, 120, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        db_calls_mock.get_reminder_id_user.assert_called_with(self.session, 1, 1)
        db_calls_mock.get_show_session.assert_called_with(self.session, 15)
        db_calls_mock.update_reminder.assert_called()

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
        now = datetime.datetime.utcnow()

        show_session_1 = models.ShowSession(None, None, now + datetime.timedelta(minutes=30), 5, 10)
        show_session_1.id = 1

        show_session_2 = models.ShowSession(2, 10, now + datetime.timedelta(minutes=100), 10, 15)
        show_session_2.id = 2

        show_session_3 = models.ShowSession(None, None, now + datetime.timedelta(days=15), 10, 10)
        show_session_3.id = 3

        channel_5 = models.Channel(None, 'Channel 5')
        channel_10 = models.Channel(None, 'Channel 10')

        show_data_10 = models.ShowData('Show 10', 'Show 10')
        show_data_10.is_movie = True

        show_data_15 = models.ShowData('Show 15', 'Show 15')
        show_data_15.is_movie = False

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

        show_session_tuple_1 = (show_session_1, channel_5, show_data_10)
        show_session_tuple_2 = (show_session_2, channel_10, show_data_15)
        show_session_tuple_3 = (show_session_1, channel_5, show_data_10)

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
