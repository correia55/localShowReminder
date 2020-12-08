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
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', None, None, None, False, None)

        # Verify the result
        self.assertEqual(4, len(actual_result))

        self.assertEqual(1, actual_result[0][0].season)
        self.assertEqual(1, actual_result[0][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[0][1])
        self.assertEqual('other fake', actual_result[0][2])
        self.assertEqual(None, actual_result[0][3])

        self.assertEqual(2, actual_result[1][0].season)
        self.assertEqual(1, actual_result[1][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[1][1])
        self.assertEqual('other fakes', actual_result[1][2])
        self.assertEqual(False, actual_result[1][3])

        self.assertEqual(None, actual_result[2][0].season)
        self.assertEqual(None, actual_result[2][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[2][1])
        self.assertEqual('some other fakes', actual_result[2][2])
        self.assertEqual(True, actual_result[2][3])

        self.assertEqual(None, actual_result[3][0].season)
        self.assertEqual(None, actual_result[3][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[3][1])
        self.assertEqual('fakes', actual_result[3][2])
        self.assertEqual(True, actual_result[3][3])

        # Clean up the DB
        self.session.delete(show_session)
        self.session.delete(show_session_2)
        self.session.delete(show_session_3)
        self.session.delete(show_session_4)
        self.session.delete(show_session_5)
        self.session.delete(show_session_6)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(channel)
        self.session.delete(channel_2)

        self.session.commit()

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
        show_session_5 = db_calls.register_show_session(self.session, None, None, now, channel.id, show_data_5.id)
        self.assertIsNotNone(show_session_5)

        # This session is not a match because of the date
        show_session_6 = db_calls.register_show_session(self.session, None, None, now - datetime.timedelta(days=50),
                                                        channel.id, show_data_6.id)
        self.assertIsNotNone(show_session_6)

        # Call the function
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', True, None, None, True,
                                                           now - datetime.timedelta(days=2))

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(None, actual_result[0][0].season)
        self.assertEqual(None, actual_result[0][0].episode)
        self.assertEqual('TEST_CHANNEL', actual_result[0][1])
        self.assertEqual('some other fakes', actual_result[0][2])
        self.assertEqual(True, actual_result[0][3])

        # Clean up the DB
        self.session.delete(show_session)
        self.session.delete(show_session_2)
        self.session.delete(show_session_3)
        self.session.delete(show_session_4)
        self.session.delete(show_session_5)
        self.session.delete(show_session_6)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(channel)
        self.session.delete(channel_2)

        self.session.commit()

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
        actual_result = db_calls.search_show_sessions_data(self.session, '_fakes?_$', False, 4, 4, True, None)

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(4, actual_result[0][0].season)
        self.assertEqual(4, actual_result[0][0].episode)
        self.assertEqual('TEST_CHANNEL_2', actual_result[0][1])
        self.assertEqual('other fake', actual_result[0][2])
        self.assertEqual(None, actual_result[0][3])

        # Clean up the DB
        self.session.delete(show_session)
        self.session.delete(show_session_2)
        self.session.delete(show_session_3)
        self.session.delete(show_session_4)
        self.session.delete(show_session_5)
        self.session.delete(show_session_6)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(channel)
        self.session.delete(channel_2)

        self.session.commit()

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
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, streaming_service.id, show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is a match
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, streaming_service.id, show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is a match
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, streaming_service.id, show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is a match
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is a match
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', None, None, None, False,
                                                                     None)

        # Verify the result
        self.assertEqual(4, len(actual_result))

        found = 0

        # Can't ensure order
        for r in actual_result:
            if r[2] == 'other fake':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(1, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1])
                self.assertEqual(None, r[3])

                found += 1

            elif r[2] == 'other fakes':
                self.assertEqual(1, r[0].first_season_available)
                self.assertEqual(2, r[0].last_season_available)
                self.assertEqual('streaming_service', r[1])
                self.assertEqual(False, r[3])

                found += 1

            elif r[2] == 'some other fakes':
                self.assertEqual(None, r[0].first_season_available)
                self.assertEqual(None, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1])
                self.assertEqual(True, r[3])

                found += 1

            elif r[2] == 'fakes':
                self.assertEqual(None, r[0].first_season_available)
                self.assertEqual(None, r[0].last_season_available)
                self.assertEqual('streaming_service_2', r[1])
                self.assertEqual(True, r[3])

                found += 1

        self.assertEqual(4, found)

        # Clean up the DB
        self.session.delete(ss_show)
        self.session.delete(ss_show_2)
        self.session.delete(ss_show_3)
        self.session.delete(ss_show_4)
        self.session.delete(ss_show_5)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(streaming_service)
        self.session.delete(streaming_service_2)

        self.session.commit()

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
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, streaming_service.id, show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is not a match because it is not a movie
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, streaming_service.id, show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is not a match because it is not a movie
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, streaming_service.id, show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is a match
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is not a match because of the date
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', True, None, None, True,
                                                                     now - datetime.timedelta(days=2))

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(None, actual_result[0][0].first_season_available)
        self.assertEqual(None, actual_result[0][0].last_season_available)
        self.assertEqual('streaming_service_2', actual_result[0][1])
        self.assertEqual('some other fakes', actual_result[0][2])
        self.assertEqual(True, actual_result[0][3])

        # Clean up the DB
        self.session.delete(ss_show)
        self.session.delete(ss_show_2)
        self.session.delete(ss_show_3)
        self.session.delete(ss_show_4)
        self.session.delete(ss_show_5)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(streaming_service)
        self.session.delete(streaming_service_2)

        self.session.commit()

    def test_search_streaming_service_shows_data_03(self) -> None:
        """ Test the function search_streaming_service_shows_data: only one matches everything. """

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
        ss_show = db_calls.register_streaming_service_show(self.session, 5, 5, streaming_service.id, show_data.id)
        self.assertIsNotNone(ss_show)

        # This session is not a match because it has the wrong episode
        ss_show_2 = db_calls.register_streaming_service_show(self.session, 1, 1, streaming_service.id, show_data_3.id)
        self.assertIsNotNone(ss_show_2)

        # This session is a match
        ss_show_3 = db_calls.register_streaming_service_show(self.session, 1, 2, streaming_service.id, show_data_4.id)
        self.assertIsNotNone(ss_show_3)

        # This session is not a match because it has the wrong episode
        ss_show_4 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_5.id)
        self.assertIsNotNone(ss_show_4)

        # This session is not a match because it has the wrong episode
        ss_show_5 = db_calls.register_streaming_service_show(self.session, None, None, streaming_service_2.id,
                                                             show_data_6.id)
        self.assertIsNotNone(ss_show_5)
        ss_show_5.update_timestamp = now - datetime.timedelta(days=50)

        # Call the function
        actual_result = db_calls.search_streaming_service_shows_data(self.session, '_fakes?_$', False, 2, 4, True, None)

        # Verify the result
        self.assertEqual(1, len(actual_result))

        self.assertEqual(1, actual_result[0][0].first_season_available)
        self.assertEqual(2, actual_result[0][0].last_season_available)
        self.assertEqual('streaming_service', actual_result[0][1])
        self.assertEqual('other fakes', actual_result[0][2])
        self.assertEqual(False, actual_result[0][3])

        # Clean up the DB
        self.session.delete(ss_show)
        self.session.delete(ss_show_2)
        self.session.delete(ss_show_3)
        self.session.delete(ss_show_4)
        self.session.delete(ss_show_5)

        self.session.commit()

        self.session.delete(show_data)
        self.session.delete(show_data_2)
        self.session.delete(show_data_3)
        self.session.delete(show_data_4)
        self.session.delete(show_data_5)
        self.session.delete(show_data_6)

        self.session.commit()

        self.session.delete(streaming_service)
        self.session.delete(streaming_service_2)

        self.session.commit()
