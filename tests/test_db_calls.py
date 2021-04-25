import datetime
import os
import unittest

import sqlalchemy.orm

# To prevent the error from the import of configuration
import models

if os.environ.get('DATABASE_URL', None) is None or 'Test' not in os.environ.get('DATABASE_URL', None):
    import pytest

    pytest.skip("Skipping DB tests", allow_module_level=True)

import configuration
import db_calls


class TestDBCalls(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = configuration.Session()

    def tearDown(self) -> None:
        self.session.query(models.Reminder).delete()
        self.session.query(models.ShowSession).delete()
        self.session.query(models.StreamingServiceShow).delete()
        self.session.query(models.ShowData).delete()
        self.session.query(models.Channel).delete()
        self.session.query(models.StreamingService).delete()
        self.session.query(models.Alarm).delete()
        self.session.query(models.User).delete()
        self.session.query(models.Token).delete()
        self.session.query(models.Cache).delete()
        self.session.query(models.LastUpdate).delete()
        self.session.query(models.ShowTitles).delete()

        self.session.commit()

        self.session.close()

    def test_get_user_id_error(self) -> None:
        """ Test the function get_user_id without user. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_user_id(self.session, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_user_id_ok(self) -> None:
        """ Test the function get_user_id with a user. """

        # Prepare the DB by creating a new user
        expected_result = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(expected_result)

        # Call the function
        actual_result = db_calls.get_user_id(self.session, expected_result.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_user_email_error(self) -> None:
        """ Test the function get_user_email without user. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_user_email(self.session, 'invalid_email')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_user_email_ok(self) -> None:
        """ Test the function get_user_email with a user. """

        # Prepare the DB by creating a new user
        expected_result = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(expected_result)

        # Call the function
        actual_result = db_calls.get_user_email(self.session, expected_result.email)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_user_error(self) -> None:
        """ Test the function register_user with error due to same email already registered. """

        # The expected result
        expected_result = None

        # Prepare the DB by creating a new user
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        # Call the function
        actual_result = db_calls.register_user(self.session, 'test_email', 'test_password')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_user_ok_01(self) -> None:
        """ Test the function register_user with success, but without language. """

        # Call the function
        actual_result = db_calls.register_user(self.session, 'test_email', 'test_password')

        # Verify the result
        self.assertEqual('test_email', actual_result.email)
        self.assertEqual('test_password', actual_result.password)
        self.assertEqual('pt', actual_result.language)
        self.assertEqual(False, actual_result.show_adult)
        self.assertEqual(False, actual_result.verified)
        self.assertEqual('EMAIL', actual_result.account_type)

    def test_register_user_ok_02(self) -> None:
        """ Test the function register_user with success, with language and account type. """

        # Call the function
        actual_result = db_calls.register_user(self.session, 'test_email', 'test_password', language='en',
                                               account_type=models.AccountType.GOOGLE)

        # Verify the result
        self.assertEqual('test_email', actual_result.email)
        self.assertEqual('test_password', actual_result.password)
        self.assertEqual('en', actual_result.language)
        self.assertEqual(False, actual_result.show_adult)
        self.assertEqual(False, actual_result.verified)
        self.assertEqual('GOOGLE', actual_result.account_type)

    def test_get_show_session_complete_error(self) -> None:
        """ Test the function get all of the information associated with a show session without results. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_show_session_complete(self.session, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_show_session_complete_ok(self) -> None:
        """ Test the function get all of the information associated with a show session with results. """

        # Prepare the DB
        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        # Call the function
        actual_result = db_calls.get_show_session_complete(self.session, show_session.id)

        # Verify the result
        self.assertEqual(show_session, actual_result[0])
        self.assertEqual(channel, actual_result[1])
        self.assertEqual(show_data, actual_result[2])

    def test_get_reminders_error(self) -> None:
        """ Test the function get_reminders without results. """

        # The expected result
        expected_result = []

        # Prepare the DB by creating a new user
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        # Call the function
        actual_result = db_calls.get_reminders_user(self.session, user.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_reminders_ok(self) -> None:
        """ Test the function get_reminders with results. """

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.get_reminders_user(self.session, user.id)

        # Verify the result
        self.assertEqual(1, len(actual_result))
        self.assertEqual(10, actual_result[0].anticipation_minutes)
        self.assertEqual(show_session.id, actual_result[0].session_id)
        self.assertEqual(user.id, actual_result[0].user_id)

    def test_get_reminders_session_error(self) -> None:
        """ Test the function get reminders associated with a session without results. """

        # The expected result
        expected_result = []

        # Call the function
        actual_result = db_calls.get_reminders_session(self.session, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_reminders_session_ok(self) -> None:
        """ Test the function get reminders associated with a session with results. """

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.get_reminders_session(self.session, show_session.id)

        # Verify the result
        self.assertEqual(1, len(actual_result))
        self.assertEqual(10, actual_result[0].anticipation_minutes)
        self.assertEqual(show_session.id, actual_result[0].session_id)
        self.assertEqual(user.id, actual_result[0].user_id)

    def test_get_reminder_id_user_error_01(self) -> None:
        """ Test the function get_reminder_id_user with an invalid reminder id. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_reminder_id_user(self.session, -1, 1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_reminder_id_user_error_02(self) -> None:
        """ Test the function get_reminder_id_user with the incorrect user id. """

        # The expected result
        expected_result = None

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.get_reminder_id_user(self.session, reminder.id, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_reminder_id_user_ok(self) -> None:
        """ Test the function get_reminder_id_user with success. """

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.get_reminder_id_user(self.session, reminder.id, reminder.user_id)

        # Verify the result
        self.assertIsNotNone(actual_result)

    def test_update_reminder_error_01(self) -> None:
        """ Test the function update_reminder with an invalid reminder. """

        # The expected result
        expected_result = False

        # Call the function
        actual_result = db_calls.update_reminder(self.session, None, 10)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_update_reminder_error_02(self) -> None:
        """ Test the function update_reminder with the same anticipation minutes. """

        # The expected result
        expected_result = False

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.update_reminder(self.session, reminder, 10)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_update_reminder_ok(self) -> None:
        """ Test the function update_reminder with success. """

        # Prepare the DB
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 1, 1, datetime.datetime.utcnow(), channel.id,
                                                      show_data.id, should_commit=True)
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # Call the function
        actual_result = db_calls.update_reminder(self.session, reminder, 20)

        # Verify the result
        self.assertEqual(20, reminder.anticipation_minutes)
        self.assertTrue(actual_result)

    def test_register_streaming_service_error(self) -> None:
        """ Test the function register_streaming_service with error due to same name already registered. """

        # The expected result
        expected_result = None

        # Prepare the DB by creating a new streaming service
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        # Call the function
        actual_result = db_calls.register_streaming_service(self.session, 'streaming_service')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_streaming_service_ok(self) -> None:
        """ Test the function register_streaming_service with success. """

        # Call the function
        actual_result = db_calls.register_streaming_service(self.session, 'streaming_service')

        # Verify the result
        self.assertEqual('streaming_service', actual_result.name)

    def test_get_streaming_service_id_error(self) -> None:
        """ Test the function get_streaming_service_id without streaming service. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_streaming_service_id(self.session, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_streaming_service_id_ok(self) -> None:
        """ Test the function get_streaming_service_id with a streaming service. """

        # Prepare the DB by creating a new streaming service
        expected_result = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(expected_result)

        # Call the function
        actual_result = db_calls.get_streaming_service_id(self.session, expected_result.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_streaming_service_show_error_01(self) -> None:
        """ Test the function register_streaming_service_show with error due to same show id and ss id already
        registered. """

        # The expected result
        expected_result = None

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        streaming_service_show = db_calls.register_streaming_service_show(self.session, None, None, False,
                                                                          streaming_service.id, show_data.id,
                                                                          should_commit=True)
        self.assertIsNotNone(streaming_service_show)

        # Call the function
        actual_result = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_streaming_service_show_error_02(self) -> None:
        """ Test the function register_streaming_service_show with error due to last season being inferior to first. """

        # The expected result
        expected_result = None

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        # Call the function
        actual_result = db_calls.register_streaming_service_show(self.session, 5, 1, False, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_register_streaming_service_show_ok(self) -> None:
        """ Test the function register_streaming_service_show with success. """

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        # Call the function
        actual_result = db_calls.register_streaming_service_show(self.session, 1, 5, False, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(1, actual_result.first_season_available)
        self.assertEqual(5, actual_result.last_season_available)
        self.assertEqual(show_data.id, actual_result.show_data_id)
        self.assertEqual(streaming_service.id, actual_result.streaming_service_id)

    def test_get_streaming_service_show_error(self) -> None:
        """ Test the function get_streaming_service_show without streaming service show. """

        # The expected result
        expected_result = None

        # Call the function
        actual_result = db_calls.get_streaming_service_show(self.session, -1)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_streaming_service_show_ok(self) -> None:
        """ Test the function get_streaming_service_show with a streaming service show. """

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        expected_result = db_calls.register_streaming_service_show(self.session, None, None, False,
                                                                   streaming_service.id,
                                                                   show_data.id, should_commit=True)
        self.assertIsNotNone(expected_result)

        # Call the function
        actual_result = db_calls.get_streaming_service_show(self.session, expected_result.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_regex_operation_01(self) -> None:
        """ Test the function get_regex_operation with a Mysql DB. """

        # The expected result
        expected_result = 'REGEXP'

        # Change the value of the DB url
        original_db_url = configuration.database_url
        configuration.database_url = 'mysql:///something'

        # Call the function
        actual_result = db_calls.get_regex_operation_dbms()

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Change the value of the DB url back to the original value
        configuration.database_url = original_db_url

    def test_get_regex_operation_02(self) -> None:
        """ Test the function get_regex_operation with a non Mysql DB. """

        # The expected result
        expected_result = '~*'

        # Change the value of the DB url
        original_db_url = configuration.database_url
        configuration.database_url = 'postgres:///something'

        # Call the function
        actual_result = db_calls.get_regex_operation_dbms()

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Change the value of the DB url back to the original value
        configuration.database_url = original_db_url

    def test_search_show_sessions_data_01(self) -> None:
        """
        Test the function search_show_sessions_data:
        - show that does not match the pattern;
        - show that does not match because the channel is adult;
        - show that does not match because it has no session;
        - show that matches and is movie;
        - show that matches and is series with season 1 and episode 1;
        - show that matches and is series with season 2 and episode 1;
        - show that matches and has old date.
        """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        # Non adult channel
        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        # Adult channel
        channel_2 = db_calls.register_channel(self.session, 'TC2', 'TEST_CHANNEL_2')
        self.assertIsNotNone(channel_2)
        channel_2.adult = True

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        # This session is not a match because the title is not a match
        show_session = db_calls.register_show_session(self.session, 5, 5, now, channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # This session is not a match because it is associated with an adult channel
        show_session_2 = db_calls.register_show_session(self.session, 4, 4, now, channel_2.id, show_data_3.id)
        self.assertIsNotNone(show_session_2)

        # This session is a match
        show_session_3 = db_calls.register_show_session(self.session, 1, 1, now, channel.id, show_data_3.id)
        self.assertIsNotNone(show_session_3)

        # This session is a match
        show_session_4 = db_calls.register_show_session(self.session, 2, 1, now, channel.id, show_data_4.id)
        self.assertIsNotNone(show_session_4)

        # This session is a match
        show_session_5 = db_calls.register_show_session(self.session, None, None, now, channel.id, show_data_5.id)
        self.assertIsNotNone(show_session_5)

        # This session is a match
        show_session_6 = db_calls.register_show_session(self.session, None, None, now - datetime.timedelta(days=50),
                                                        channel.id, show_data_6.id)
        self.assertIsNotNone(show_session_6)

        # Call the function
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', None, None, None, False, False)

        # Verify the result
        self.assertEqual(4, len(actual_result))

        found = [False] * 4

        # Can't ensure order
        for r in actual_result:
            if r[2].portuguese_title == 'other fake':
                self.assertEqual(1, r[0].season)
                self.assertEqual(1, r[0].episode)
                self.assertEqual('TEST_CHANNEL', r[1].name)
                self.assertEqual(None, r[2].is_movie)

                found[0] = True

            if r[2].portuguese_title == 'other fakes':
                self.assertEqual(2, r[0].season)
                self.assertEqual(1, r[0].episode)
                self.assertEqual('TEST_CHANNEL', r[1].name)
                self.assertEqual(False, r[2].is_movie)

                found[1] = True

            if r[2].portuguese_title == 'some other fakes':
                self.assertEqual(None, r[0].season)
                self.assertEqual(None, r[0].episode)
                self.assertEqual('TEST_CHANNEL', r[1].name)
                self.assertEqual(True, r[2].is_movie)

                found[2] = True

            if r[2].portuguese_title == 'fakes':
                self.assertEqual(None, r[0].season)
                self.assertEqual(None, r[0].episode)
                self.assertEqual('TEST_CHANNEL', r[1].name)
                self.assertEqual(True, r[2].is_movie)

                found[3] = True

        for f in found:
            self.assertTrue(f)

    def test_search_show_sessions_data_02(self) -> None:
        """
        Test the function search_show_sessions_data:
        only two match the movie and pattern criteria, but only one has a valid date.
        """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        # Non adult channel
        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        # Adult channel
        channel_2 = db_calls.register_channel(self.session, 'TC2', 'TEST_CHANNEL_2')
        self.assertIsNotNone(channel_2)
        channel_2.adult = True

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        # This session is not a match because the title is not a match
        show_session = db_calls.register_show_session(self.session, 5, 5, now, channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # This session is not a match because it is not a movie
        show_session_2 = db_calls.register_show_session(self.session, 4, 4, now, channel_2.id, show_data_3.id)
        self.assertIsNotNone(show_session_2)

        # This session is not a match because it is not a movie
        show_session_3 = db_calls.register_show_session(self.session, 1, 1, now, channel.id, show_data_3.id)
        self.assertIsNotNone(show_session_3)

        # This session is not a match because it is not a movie
        show_session_4 = db_calls.register_show_session(self.session, 2, 1, now, channel.id, show_data_4.id)
        self.assertIsNotNone(show_session_4)

        # This session is a match
        show_session_5 = db_calls.register_show_session(self.session, None, None, now + datetime.timedelta(days=1),
                                                        channel.id, show_data_5.id)
        self.assertIsNotNone(show_session_5)

        # This session is not a match because of the date
        show_session_6 = db_calls.register_show_session(self.session, None, None, now - datetime.timedelta(days=50),
                                                        channel.id, show_data_6.id)
        self.assertIsNotNone(show_session_6)

        # Call the function
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', True, None, None, True, False,
                                                           below_datetime=now - datetime.timedelta(days=2))

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(None, actual_result[0][0].season)
        self.assertEqual(None, actual_result[0][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[0][1].name)
        self.assertEqual('some other fakes', actual_result[0][2].portuguese_title)
        self.assertEqual(True, actual_result[0][2].is_movie)

    def test_search_show_sessions_data_03(self) -> None:
        """Test the function search_show_sessions_data: only one matches everything and it is from an adult channel."""

        # Prepare the DB
        now = datetime.datetime.utcnow()

        # Non adult channel
        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        # Adult channel
        channel_2 = db_calls.register_channel(self.session, 'TC2', 'TEST_CHANNEL_2')
        self.assertIsNotNone(channel_2)
        channel_2.adult = True

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        # This session is not a match because the title is not a match
        show_session = db_calls.register_show_session(self.session, 5, 5, now, channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # This session is a match
        show_session_2 = db_calls.register_show_session(self.session, 4, 4, now, channel_2.id, show_data_3.id)
        self.assertIsNotNone(show_session_2)

        # This session is not a match because it has the wrong episode
        show_session_3 = db_calls.register_show_session(self.session, 1, 1, now, channel.id, show_data_3.id)
        self.assertIsNotNone(show_session_3)

        # This session is not a match because it has the wrong episode
        show_session_4 = db_calls.register_show_session(self.session, 2, 1, now, channel.id, show_data_4.id)
        self.assertIsNotNone(show_session_4)

        # This session is not a match because it has the wrong episode
        show_session_5 = db_calls.register_show_session(self.session, None, None, now, channel.id, show_data_5.id)
        self.assertIsNotNone(show_session_5)

        # This session is not a match because it has the wrong episode
        show_session_6 = db_calls.register_show_session(self.session, None, None, now - datetime.timedelta(days=50),
                                                        channel.id, show_data_6.id)
        self.assertIsNotNone(show_session_6)

        # Call the function
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', False, 4, 4, True, False)

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(4, actual_result[0][0].season)
        self.assertEqual(4, actual_result[0][0].episode)
        self.assertEqual('TEST_CHANNEL_2', actual_result[0][1].name)
        self.assertEqual('other fake', actual_result[0][2].portuguese_title)
        self.assertEqual(None, actual_result[0][2].is_movie)

    def test_search_streaming_service_shows_data_01(self) -> None:
        """
        Test the function search_streaming_service_shows_data:
        - show that does not match the pattern;
        - show that does not match because it has no session;
        - show that matches and is movie;
        - show that matches and is series with only the season 1 available;
        - show that matches and is series with the 2 first seasons available;
        - show that matches and has old date.
        """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        streaming_service_2 = db_calls.register_streaming_service(self.session, 'streaming_service_2')
        self.assertIsNotNone(streaming_service_2)

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        # This session is not a match because the title is not a match
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, False, streaming_service.id,
                                                           show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is a match
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, False, streaming_service.id,
                                                             show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is a match
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service.id,
                                                             show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is a match
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is a match
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', None, None, None, False,
                                                                     False)

        # Verify the result
        self.assertEqual(4, len(actual_result))

        found = [False] * 4

        # Can't ensure order
        for r in actual_result:
            if r[2].portuguese_title == 'other fake':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(1, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1].name)
                self.assertEqual(None, r[2].is_movie)

                found[0] = True

            elif r[2].portuguese_title == 'other fakes':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(2, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1].name)
                self.assertEqual(False, r[2].is_movie)

                found[1] = True

            elif r[2].portuguese_title == 'some other fakes':
                self.assertEqual(None, r[0].first_season_available)
                self.assertEqual(None, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1].name)
                self.assertEqual(True, r[2].is_movie)

                found[2] = True

            elif r[2].portuguese_title == 'fakes':
                self.assertEqual(None, r[0].first_season_available)
                self.assertEqual(None, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1].name)
                self.assertEqual(True, r[2].is_movie)

                found[3] = True

        for f in found:
            self.assertTrue(f)

    def test_search_streaming_service_shows_data_02(self) -> None:
        """
        Test the function search_streaming_service_shows_data:
        only two match the movie and pattern criteria, but only one has a valid date.
        """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        streaming_service_2 = db_calls.register_streaming_service(self.session, 'streaming_service_2')
        self.assertIsNotNone(streaming_service_2)

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        # This session is not a match because the title is not a match
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, False, streaming_service.id,
                                                           show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is a match because is_movie is None
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, False, streaming_service.id,
                                                             show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is not a match because it is not a movie
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service.id,
                                                             show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is a match
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is not a match because of the date
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', True, None, None, True,
                                                                     False,
                                                                     below_datetime=now - datetime.timedelta(days=2))

        # Verify the result
        self.assertEqual(2, len(actual_result))

        found = [False] * 2

        # Can't ensure order
        for r in actual_result:
            if r[2].portuguese_title == 'some other fakes':
                self.assertEqual(None, r[0].first_season_available)
                self.assertEqual(None, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1].name)
                self.assertEqual(True, r[2].is_movie)

                found[0] = True

            elif r[2].portuguese_title == 'other fake':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(1, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1].name)
                self.assertEqual(None, r[2].is_movie)

                found[1] = True

        for f in found:
            self.assertTrue(f)

    def test_search_streaming_service_shows_data_03(self) -> None:
        """ Test the function search_streaming_service_shows_data: only two match everything. """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        streaming_service_2 = db_calls.register_streaming_service(self.session, 'streaming_service_2')
        self.assertIsNotNone(streaming_service_2)

        show_data = db_calls.register_show_data(self.session, 'fake show')
        self.assertIsNotNone(show_data)

        # This show is not a match because it has no session associated with it
        show_data_2 = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data_2)

        show_data_3 = db_calls.register_show_data(self.session, 'other fake')
        self.assertIsNotNone(show_data_3)

        show_data_4 = db_calls.register_show_data(self.session, 'other fakes')
        self.assertIsNotNone(show_data_4)
        show_data_4.is_movie = False

        show_data_5 = db_calls.register_show_data(self.session, 'some other fakes')
        self.assertIsNotNone(show_data_5)
        show_data_5.is_movie = True

        show_data_6 = db_calls.register_show_data(self.session, 'fakes')
        self.assertIsNotNone(show_data_6)
        show_data_6.is_movie = True

        show_data_7 = db_calls.register_show_data(self.session, 'yet another fakes')
        self.assertIsNotNone(show_data_7)
        show_data_7.is_movie = False

        # This session is not a match because the title is not a match
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, False, streaming_service.id,
                                                           show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is not a match because it has the wrong episode
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, False, streaming_service.id,
                                                             show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is a match
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service.id,
                                                             show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is not a match because it has the wrong episode
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is not a match because it has the wrong episode
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # This session is a match
        ss_show_6 = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service_2.id,
                                                             show_data_3.id)
        self.assertIsNotNone(ss_show_6)
        ss_show_6.prev_first_season_available = 1
        ss_show_6.prev_last_season_available = 1

        # This session is not a match because the previous update already was a match
        ss_show_7 = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service.id,
                                                             show_data_7.id)
        self.assertIsNotNone(ss_show_7)
        ss_show_7.prev_first_season_available = 1
        ss_show_7.prev_last_season_available = 2

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', False, 2, 4, True,
                                                                     False)

        # Verify the result
        self.assertEqual(2, len(actual_result))

        found = [False] * 2

        # Can't ensure order
        for r in actual_result:
            if r[2].portuguese_title == 'other fakes':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(2, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1].name)
                self.assertEqual(False, r[2].is_movie)

                found[0] = True
            elif r[2].portuguese_title == 'other fake':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(2, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1].name)
                self.assertEqual(None, r[2].is_movie)

                found[1] = True

        for f in found:
            self.assertTrue(f)

    def test_update_streaming_service_show_error(self):
        """ Test the update of a streaming service show with an nonexistent id. """

        # The expected result
        expected_result = False

        # Call the function
        actual_result = db_calls.update_streaming_service_show(self.session, -1, None, None, True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_update_streaming_service_show_ok_01(self):
        """ Test the update of a streaming service show with a movie. """

        # The expected result
        expected_result = True

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data)
        show_data.is_movie = False

        ss_show = db_calls.register_streaming_service_show(self.session, None, None, False, streaming_service.id,
                                                           show_data.id)
        self.assertIsNotNone(ss_show)

        # Call the function
        actual_result = db_calls.update_streaming_service_show(self.session, ss_show.id, None, None, True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        self.assertEqual(None, ss_show.prev_first_season_available)
        self.assertEqual(None, ss_show.prev_last_season_available)

    def test_update_streaming_service_show_ok_02(self):
        """ Test the update of a streaming service show with a tv show. """

        # The expected result
        expected_result = True

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'fake')
        self.assertIsNotNone(show_data)
        show_data.is_movie = True

        ss_show = db_calls.register_streaming_service_show(self.session, 1, 2, False, streaming_service.id,
                                                           show_data.id)
        self.assertIsNotNone(ss_show)

        # Call the function
        actual_result = db_calls.update_streaming_service_show(self.session, ss_show.id, 3, 4, True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        self.assertEqual(1, ss_show.prev_first_season_available)
        self.assertEqual(2, ss_show.prev_last_season_available)

    def test_search_old_sessions_ok_01(self) -> None:
        """ Test the function search_old_sessions with only new sessions. """

        # The expected result
        expected_result = []

        # Prepare the DB
        now = datetime.datetime.utcnow()

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'show name')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 5, 5, now, channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # Call the function
        today_at_start = now.replace(hour=0, minute=0, second=0)
        today_at_end = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0) \
                       - datetime.timedelta(seconds=1)

        actual_result = db_calls.search_old_sessions(self.session, today_at_start, today_at_end, ['TEST_CHANNEL'])

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_search_old_sessions_ok_02(self) -> None:
        """ Test the function search_old_sessions with old sessions. """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'show name')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 5, 5, now, channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # Change the update timestamp to an old datetime
        show_session.update_timestamp = now - datetime.timedelta(hours=24)
        self.session.commit()

        # Call the function
        today_at_start = now.replace(hour=0, minute=0, second=0)
        today_at_end = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0) \
                       - datetime.timedelta(seconds=1)

        actual_result = db_calls.search_old_sessions(self.session, today_at_start, today_at_end, ['TEST_CHANNEL'])

        # Verify the result
        self.assertEqual(1, len(actual_result))
        self.assertEqual(5, actual_result[0].season)
        self.assertEqual(5, actual_result[0].episode)
        self.assertEqual(channel.id, actual_result[0].channel_id)
        self.assertEqual(show_data.id, actual_result[0].show_id)

    def test_search_existing_session_ok_01(self) -> None:
        """ Test the function search_existing_session without an existing session. """

        # The expected result
        expected_result = None

        # Prepare the DB
        now = datetime.datetime.utcnow()

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'show name')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 5, 5, now - datetime.timedelta(hours=5), channel.id,
                                                      show_data.id)
        self.assertIsNotNone(show_session)

        # Call the function
        actual_result = db_calls.search_existing_session(self.session, 5, 5, now, channel.id, show_data.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_search_existing_session_ok_02(self) -> None:
        """ Test the function search_existing_session with an existing session. """

        # Prepare the DB
        now = datetime.datetime.utcnow()

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_data = db_calls.register_show_data(self.session, 'show name')
        self.assertIsNotNone(show_data)

        show_session = db_calls.register_show_session(self.session, 5, 5, now - datetime.timedelta(minutes=30),
                                                      channel.id, show_data.id)
        self.assertIsNotNone(show_session)

        # Call the function
        actual_result = db_calls.search_existing_session(self.session, 5, 5, now, channel.id, show_data.id)

        # Verify the result
        self.assertIsNotNone(actual_result)


class TestUserExcludedChannel(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = configuration.Session()

    def tearDown(self) -> None:
        self.session.query(models.UserExcludedChannel).delete()
        self.session.query(models.Channel).delete()
        self.session.query(models.User).delete()

        self.session.commit()

        self.session.close()

    def test_get_user_excluded_channels_error(self) -> None:
        """ Test the function get_user_excluded_channels without any entries. """

        # The expected result
        expected_result = []

        # Prepare the DB
        user = db_calls.register_user(self.session, 'email', 'password')
        self.assertIsNotNone(user)

        # Call the function
        actual_result = db_calls.get_user_excluded_channels(self.session, user.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_user_excluded_channels_ok(self) -> None:
        """ Test the function get_user_excluded_channels with entries. """

        # Prepare the DB
        user = db_calls.register_user(self.session, 'email', 'password')
        self.assertIsNotNone(user)

        channel_1 = db_calls.register_channel(self.session, 'CH', 'Channel')
        self.assertIsNotNone(channel_1)

        channel_3 = db_calls.register_channel(self.session, 'CH3', 'Channel 3')
        self.assertIsNotNone(channel_3)

        user_excluded_channel_1 = models.UserExcludedChannel(user.id, channel_1.id)
        self.session.add(user_excluded_channel_1)

        user_excluded_channel_3 = models.UserExcludedChannel(user.id, channel_3.id)
        self.session.add(user_excluded_channel_3)

        user_2 = db_calls.register_user(self.session, 'email 2', 'password2')
        self.assertIsNotNone(user_2)

        channel_2 = db_calls.register_channel(self.session, 'CH2', 'Channel 2')
        self.assertIsNotNone(channel_2)

        user_excluded_channel_2 = models.UserExcludedChannel(user_2.id, channel_2.id)
        self.session.add(user_excluded_channel_2)

        self.session.commit()

        # Call the function
        actual_result = db_calls.get_user_excluded_channels(self.session, user.id)

        # Verify the result
        self.assertEqual(2, len(actual_result))

        self.assertEqual(user.id, actual_result[0].user_id)
        self.assertEqual(channel_1.id, actual_result[0].channel_id)

        self.assertEqual(user.id, actual_result[1].user_id)
        self.assertEqual(channel_3.id, actual_result[1].channel_id)
