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
import models


# TODO: UPDATE TESTS WITH THE NEW SHOW_DATA SHOW_SESSION ORGANIZATION


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

    def test_get_reminders_01(self) -> None:
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

    def test_get_reminders_02(self) -> None:
        """ Test the function get_reminders with results. """

        # Prepare the DB by creating a new user
        user = db_calls.register_user(self.session, 'test_email', 'test_password')
        self.assertIsNotNone(user)

        channel = db_calls.register_channel(self.session, 'TC', 'TEST_CHANNEL')
        self.assertIsNotNone(channel)

        show_session = db_calls.register_show_session(self.session, 'test_title', 1, 1, 'synopsis',
                                                      datetime.datetime.utcnow())
        self.assertIsNotNone(show_session)

        reminder = db_calls.register_reminder(self.session, show_session.id, 10, user.id)
        self.assertIsNotNone(reminder)

        # The expected result
        expected_result = [models.Reminder(10, show_session.id, user.id)]

        # Call the function
        actual_result = db_calls.get_reminders_user(self.session, user.id)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Clean up the DB
        self.session.delete(reminder)
        self.session.commit()

        self.session.delete(show_session)
        self.session.commit()

        self.session.delete(channel)
        self.session.commit()

        self.session.delete(user)
        self.session.commit()


if __name__ == '__main__':
    unittest.main()
