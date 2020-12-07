import datetime
import os
import unittest

import sqlalchemy.orm

# To prevent the error from the import of configuration
if os.environ.get('DATABASE_URL', None) is None:
    import pytest

    pytest.skip("Skipping DB tests", allow_module_level=True)

import configuration
import db_calls


class TestDBCalls(unittest.TestCase):
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.session = configuration.Session()

    def tearDown(self) -> None:
        # Delete test data
        user = db_calls.get_user_email(self.session, 'test_email')

        channel = db_calls.get_channel_name(self.session, 'TEST_CHANNEL')

        if channel is not None:
            sessions = db_calls.get_show_sessions_channel(self.session, channel.id)

            # Delete all sessions associated with the test channel
            for s in sessions:
                if user is not None:
                    # Delete all reminders associated with a session
                    reminders = db_calls.get_reminders_user(self.session, user.id)

                    for a in reminders:
                        self.session.delete(a)

                    self.session.commit()

                self.session.delete(s)

            self.session.delete(channel)
            self.session.commit()

        if user is not None:
            self.session.delete(user)

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

        # Clean up the DB
        self.session.delete(expected_result)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(expected_result)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(user)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(actual_result)
        self.session.commit()

    def test_register_user_ok_02(self) -> None:
        """ Test the function register_user with success, with language. """

        # Call the function
        actual_result = db_calls.register_user(self.session, 'test_email', 'test_password', 'en')

        # Verify the result
        self.assertEqual('test_email', actual_result.email)
        self.assertEqual('test_password', actual_result.password)
        self.assertEqual('en', actual_result.language)
        self.assertEqual(False, actual_result.show_adult)
        self.assertEqual(False, actual_result.verified)

        # Clean up the DB
        self.session.delete(actual_result)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(user)
        self.session.commit()

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
                                                      show_data.id, True)
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

        # Clean up the DB
        self.session.delete(reminder)
        self.session.commit()

        self.session.delete(show_session)
        self.session.commit()

        self.session.delete(show_data)
        self.session.commit()

        self.session.delete(channel)
        self.session.commit()

        self.session.delete(user)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(streaming_service)
        self.session.commit()

    def test_register_streaming_service_ok(self) -> None:
        """ Test the function register_streaming_service with success. """

        # Call the function
        actual_result = db_calls.register_streaming_service(self.session, 'streaming_service')

        # Verify the result
        self.assertEqual('streaming_service', actual_result.name)

        # Clean up the DB
        self.session.delete(actual_result)
        self.session.commit()

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

        # Clean up the DB
        self.session.delete(expected_result)
        self.session.commit()

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

        streaming_service_show = db_calls.register_streaming_service_show(self.session, None, None,
                                                                          streaming_service.id, show_data.id,
                                                                          should_commit=True)
        self.assertIsNotNone(streaming_service_show)

        # Call the function
        actual_result = db_calls.register_streaming_service_show(self.session, None, None, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Clean up the DB
        self.session.delete(streaming_service_show)
        self.session.commit()

        self.session.delete(show_data)
        self.session.commit()

        self.session.delete(streaming_service)
        self.session.commit()

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
        actual_result = db_calls.register_streaming_service_show(self.session, 5, 1, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Clean up the DB
        self.session.delete(show_data)
        self.session.commit()

        self.session.delete(streaming_service)
        self.session.commit()

    def test_register_streaming_service_show_ok(self) -> None:
        """ Test the function register_streaming_service_show with success. """

        # Prepare the DB
        streaming_service = db_calls.register_streaming_service(self.session, 'streaming_service')
        self.assertIsNotNone(streaming_service)

        show_data = db_calls.register_show_data(self.session, 'test_title')
        self.assertIsNotNone(show_data)

        # Call the function
        actual_result = db_calls.register_streaming_service_show(self.session, 1, 5, streaming_service.id,
                                                                 show_data.id, should_commit=True)

        # Verify the result
        self.assertEqual(1, actual_result.first_season_available)
        self.assertEqual(5, actual_result.last_season_available)
        self.assertEqual(show_data.id, actual_result.show_data_id)
        self.assertEqual(streaming_service.id, actual_result.streaming_service_id)

        # Clean up the DB
        self.session.delete(actual_result)
        self.session.commit()

        self.session.delete(show_data)
        self.session.commit()

        self.session.delete(streaming_service)
        self.session.commit()

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

        expected_result = db_calls.register_streaming_service_show(self.session, None, None, streaming_service.id,
                                                                   show_data.id, should_commit=True)
        self.assertIsNotNone(expected_result)

        # Call the function
        actual_result = db_calls.get_streaming_service_show(self.session, expected_result.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Clean up the DB
        self.session.delete(expected_result)
        self.session.commit()

        self.session.delete(show_data)
        self.session.commit()

        self.session.delete(streaming_service)
        self.session.commit()

    # TODO: ADD THE TESTS FOR THE SEARCHES


if __name__ == '__main__':
    unittest.main()
