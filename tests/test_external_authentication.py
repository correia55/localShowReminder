import sys
import unittest.mock

# Configure a mock for the configuration file
configuration_mock = unittest.mock.MagicMock()
sys.modules['configuration'] = configuration_mock

# Configure a mock for the id_token file
id_token_mock = unittest.mock.MagicMock()
sys.modules['google.oauth2.id_token'] = id_token_mock

import external_authentication


def verify_oauth2_token_with_error(token, request, client_id):
    raise ValueError()


class TestExternalAuthentication(unittest.TestCase):
    def setUp(self) -> None:
        """ Prepare the mocks for each test. """

        configuration_mock.google_client_id = 'google client id'

    def tearDown(self) -> None:
        """ Reset the mocks after each test. """

        id_token_mock.verify_oauth2_token.reset_mock(return_value=True, side_effect=True)

    def test_external_authentication_ok(self) -> None:
        """ Test the function external_authentication, with a success case. """

        # The expected result
        expected_result = 'user_email@something.com'

        # Prepare the mocks
        id_token_mock.verify_oauth2_token.return_value = {'email': 'user_email@something.com'}

        # Call the function
        token = 'valid token'
        source = 'GOOGLE'

        actual_result = external_authentication.external_authentication(token, source)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        id_token_mock.verify_oauth2_token.assert_called_with('valid token', unittest.mock.ANY, 'google client id')

    def test_external_authentication_error_01(self) -> None:
        """ Test the function external_authentication, with an invalid source. """

        # The expected result
        expected_result = None

        # Call the function
        token = 'valid token'
        source = 'INVALID SOURCE'

        actual_result = external_authentication.external_authentication(token, source)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        id_token_mock.verify_oauth2_token.assert_not_called()

    def test_external_authentication_error_02(self) -> None:
        """ Test the function external_authentication, with the google authentication failing. """

        # The expected result
        expected_result = None

        # Prepare the mocks
        id_token_mock.verify_oauth2_token.side_effect = verify_oauth2_token_with_error

        # Call the function
        token = 'invalid token'
        source = 'GOOGLE'

        actual_result = external_authentication.external_authentication(token, source)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

        # Verify the calls to the mocks
        id_token_mock.verify_oauth2_token.assert_called_with('invalid token', unittest.mock.ANY, 'google client id')
