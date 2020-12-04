import datetime
import sys
import unittest.mock

import jwt

import models

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the db_calls file
db_calls_mock = unittest.mock.MagicMock()
sys.modules['db_calls'] = db_calls_mock

import authentication


class TestAuthentication(unittest.TestCase):
    def setUp(self) -> None:
        """ Prepare the mocks for each test. """

        configuration_mock.secret_key = 'random key'

    def tearDown(self) -> None:
        """ Reset the mocks after each test. """

        configuration_mock.reset_mock()
        db_calls_mock.reset_mock()

    def test_get_token_payload_ok(self) -> None:
        """ Test the function that returns the payload of a token, with a success case. """

        # The expected result
        expected_result = {'key': 'value'}

        # Call the function
        token = jwt.encode(expected_result, 'random key', algorithm='HS256')

        actual_result = authentication.get_token_payload(token)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_payload_error_01(self) -> None:
        """ Test the function that returns the payload of a token, with an error due to invalid secret key. """

        # The expected result
        expected_result = None

        # Call the function
        token_payload = {'key': 'value'}
        token = jwt.encode(token_payload, 'other key', algorithm='HS256')

        actual_result = authentication.get_token_payload(token)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_payload_error_02(self) -> None:
        """ Test the function that returns the payload of a token, with an error due to expiration of the token. """

        # The expected result
        expected_result = None

        # Call the function
        token_payload = {'key': 'value', 'exp': datetime.datetime.utcnow() - datetime.timedelta(days=5)}

        token = jwt.encode(token_payload, 'random key', algorithm='HS256')

        actual_result = authentication.get_token_payload(token)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_payload_error_03(self) -> None:
        """ Test the function that returns the payload of a token, with an error due to invalid token. """

        # The expected result
        expected_result = None

        # Call the function
        token = 'random string'.encode()
        actual_result = authentication.get_token_payload(token)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_field_ok(self) -> None:
        """ Test the function that returns a field in the payload of a token, with a success case. """

        # The expected result
        expected_result = 'value'

        # Call the function
        token_payload = {'key': 'value'}

        token = jwt.encode(token_payload, 'random key', algorithm='HS256')

        actual_result = authentication.get_token_field(token, 'key')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_field_error_01(self) -> None:
        """ Test the function that returns a field in the payload of a token, with an error due to invalid token. """

        # The expected result
        expected_result = None

        # Call the function
        token = 'random string'.encode()
        actual_result = authentication.get_token_field(token, 'key')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_token_field_error_02(self) -> None:
        """ Test the function that returns a field in the payload of a token, with an error due to invalid field. """

        # The expected result
        expected_result = None

        # Call the function
        token_payload = {'key': 'value'}

        token = jwt.encode(token_payload, 'random key', algorithm='HS256')

        actual_result = authentication.get_token_field(token, 'invalid key')

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_generate_token_ok_01(self) -> None:
        """ Test the function that generates a token, with a success case for REFRESH. """

        # The expected result
        expected_expiration_date = datetime.datetime.today().replace(microsecond=0) + datetime.timedelta(days=5)

        expected_type = 'REFRESH'

        # Prepare the mocks
        token_payload = {'key': 'value'}
        token = jwt.encode(token_payload, 'random key', algorithm='HS256')

        configuration_mock.REFRESH_TOKEN_VALIDITY_DAYS = 5
        db_calls_mock.register_token.return_value = models.Token(token)

        # Call the function
        actual_result = authentication.generate_token(1, authentication.TokenType.REFRESH, unittest.mock.MagicMock())

        # Verify the result
        self.assertIsNotNone(actual_result)
        db_calls_mock.register_token.assert_called()

        # Verify the date
        actual_expiration_date = datetime.datetime.fromtimestamp(authentication.get_token_field(actual_result, 'exp'))
        self.assertEqual(expected_expiration_date, actual_expiration_date)

        # Verify the other fields exist
        self.assertEqual(expected_type, authentication.get_token_field(actual_result, 'type'))
        self.assertEqual(1, authentication.get_token_field(actual_result, 'user'))

    def test_generate_token_ok_02(self) -> None:
        """ Test the function that generates a token, with a success case for VERIFICATION.
         And also include some extra fields in the payload."""

        # The expected result
        expected_expiration_date = datetime.datetime.today().replace(microsecond=0) + datetime.timedelta(days=5)

        expected_type = 'VERIFICATION'

        # Prepare the mocks
        configuration_mock.VERIFICATION_TOKEN_VALIDITY_DAYS = 5

        # Call the function
        actual_result = authentication.generate_token(1234, authentication.TokenType.VERIFICATION,
                                                      unittest.mock.MagicMock(), {'extra_key': 'extra_value'})

        # Verify the result
        self.assertIsNotNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

        # Verify the date
        actual_expiration_date = datetime.datetime.fromtimestamp(authentication.get_token_field(actual_result, 'exp'))
        self.assertEqual(expected_expiration_date, actual_expiration_date)

        # Verify the other fields exist
        self.assertEqual(expected_type, authentication.get_token_field(actual_result, 'type'))
        self.assertEqual(1234, authentication.get_token_field(actual_result, 'user'))
        self.assertEqual('extra_value', authentication.get_token_field(actual_result, 'extra_key'))

    def test_generate_token_error_01(self) -> None:
        """ Test the function that generates a token, with an error case for REFRESH due to session being None. """

        # Call the function
        actual_result = authentication.generate_token(1, authentication.TokenType.REFRESH, None)

        # Verify the result
        self.assertIsNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

    def test_generate_token_error_02(self) -> None:
        """ Test the function that generates a token, with an error case for REFRESH due to a fail in the insertion of
        the token in the DB. """

        # Prepare the mocks
        configuration_mock.REFRESH_TOKEN_VALIDITY_DAYS = 5
        db_calls_mock.register_token.return_value = None

        # Call the function
        actual_result = authentication.generate_token(1, authentication.TokenType.REFRESH, unittest.mock.MagicMock())

        # Verify the result
        self.assertIsNone(actual_result)
        db_calls_mock.register_token.assert_called()

    def test_generate_token_error_03(self) -> None:
        """ Test the function that generates a token, with an error due to invalid token type. """

        # Call the function
        actual_result = authentication.generate_token(1, unittest.mock.MagicMock(), unittest.mock.MagicMock())

        # Verify the result
        self.assertIsNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

    def test_generate_token_error_04(self) -> None:
        """ Test the function that generates a token, with an error due to invalid token type. """

        # Prepare the mocks
        configuration_mock.CHANGE_EMAIL_TOKEN_VALIDITY_DAYS = 5
        configuration_mock.secret_key = None

        # Call the function
        actual_result = authentication.generate_token(1, authentication.TokenType.CHANGE_EMAIL_NEW,
                                                      unittest.mock.MagicMock())

        # Verify the result
        self.assertIsNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

    def test_generate_change_token_ok(self) -> None:
        """ Test the function that generates a change token, with a success case for DELETION. """

        # The expected result
        expected_expiration_date = datetime.datetime.today().replace(microsecond=0) + datetime.timedelta(days=5)

        expected_type = 'DELETION'

        # Prepare the mocks
        configuration_mock.DELETION_TOKEN_VALIDITY_DAYS = 5

        # Call the function
        actual_result = authentication.generate_change_token(123, authentication.TokenType.DELETION,
                                                             {'extra_key': 'extra_value'})

        # Verify the result
        self.assertIsNotNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

        # Verify the date
        actual_expiration_date = datetime.datetime.fromtimestamp(authentication.get_token_field(actual_result, 'exp'))
        self.assertEqual(expected_expiration_date, actual_expiration_date)

        # Verify the other fields exist
        self.assertEqual(expected_type, authentication.get_token_field(actual_result, 'type'))
        self.assertEqual(123, authentication.get_token_field(actual_result, 'user'))
        self.assertEqual('extra_value', authentication.get_token_field(actual_result, 'extra_key'))

    def test_generate_change_token_error(self) -> None:
        """ Test the function that generates a change token, with an error case due to missing session. """

        # Call the function
        actual_result = authentication.generate_change_token(123, authentication.TokenType.REFRESH,
                                                             {'extra_key': 'extra_value'})

        # Verify the result
        self.assertIsNone(actual_result)
        db_calls_mock.register_token.assert_not_called()

    # TODO: ADD TESTS FOR THE REMAINING METHODS


if __name__ == '__main__':
    unittest.main()
