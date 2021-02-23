import datetime
import unittest

import auxiliary


@auxiliary.auto_repr
class AutoReprTest:
    string: str
    number: int

    def __init__(self, string: str, number: int) -> None:
        self.string = string
        self.number = number

    def to_dict(self):
        return {'string': self.string, 'number': self.number}


class TestAuxiliary(unittest.TestCase):
    def test_strip_accents(self) -> None:
        """ Test the function strip_accents. """

        # The expected result
        expected_result = 'aaaaaAAAAAoooOOOeeeEEErt'

        # Call the function
        text = 'aàáãâAÁÀÃÂoóôOÓÔeéêEÉÊrt'
        actual_result = auxiliary.strip_accents(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_remove_quote(self) -> None:
        """ Test the function remove_quote. """

        # The expected result
        expected_result = 'schits, schits, schits'

        # Call the function
        text = 'schit\'s, schit`s, schit´s'
        actual_result = auxiliary.remove_quote(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_words(self) -> None:
        """ Test the function get_words. """

        # The expected result
        expected_result = ['schits', 'schits', 'schits', 'aaaaaAAAAAoooOOOeeeEEErt']

        # Call the function
        text = 'schit\'s schit`s schit´s aàáãâAÁÀÃÂoóôOÓÔeéêEÉÊrt'
        actual_result = auxiliary.get_words(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_make_searchable_title(self) -> None:
        """ Test the function make_searchable_title. """

        # The expected result
        expected_result = '_schits_schits_schits_aaaaaAAAAAoooOOOeeeEEErt_'

        # Call the function
        text = 'schit\'s schit`s schit´s aàáãâAÁÀÃÂoóôOÓÔeéêEÉÊrt'
        actual_result = auxiliary.make_searchable_title(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_get_datetime_with_tz_offset_01(self) -> None:
        """ Test the function get_datetime_with_tz_offset with a date where timezone matters. """

        # The expected result
        expected_result = '2020-08-01 09:00:00+01:00'

        # Call the function
        date_time = datetime.datetime(2020, 8, 1, 9)
        actual_result = auxiliary.get_datetime_with_tz_offset(date_time)

        # Verify the result
        self.assertEqual(expected_result, str(actual_result))

    def test_get_datetime_with_tz_offset_02(self) -> None:
        """ Test the function get_datetime_with_tz_offset with a date where timezone does not matter. """

        # The expected result
        expected_result = '2020-01-01 09:00:00+00:00'

        # Call the function
        date_time = datetime.datetime(2020, 1, 1, 9)
        actual_result = auxiliary.get_datetime_with_tz_offset(date_time)

        # Verify the result
        self.assertEqual(expected_result, str(actual_result))

    def test_convert_datetime_to_utc_01(self) -> None:
        """ Test the function convert_datetime_to_utc with a date where timezone matters. """

        # The expected result
        expected_result = datetime.datetime(2020, 8, 1, 8, tzinfo=datetime.timezone.utc)

        # Call the function
        date_time = auxiliary.get_datetime_with_tz_offset(datetime.datetime(2020, 8, 1, 9))
        actual_result = auxiliary.convert_datetime_to_utc(date_time)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_convert_datetime_to_utc_02(self) -> None:
        """ Test the function convert_datetime_to_utc with a date where timezone does not matter. """

        # The expected result
        expected_result = datetime.datetime(2020, 1, 1, 9, tzinfo=datetime.timezone.utc)

        # Call the function
        date_time = auxiliary.get_datetime_with_tz_offset(datetime.datetime(2020, 1, 1, 9))
        actual_result = auxiliary.convert_datetime_to_utc(date_time)

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_auto_repr(self) -> None:
        """ Test the annotation that automatically generates the function __repr__ for any class. """

        # The expected result
        expected_result = 'AutoReprTest(string=a string, number=353)'

        # Call the function
        auto_repr_test = AutoReprTest('a string', 353)

        actual_result = auto_repr_test.__repr__()

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_list_to_json(self) -> None:
        """ Test the function list_to_json. """

        # The expected result
        expected_result = [{'number': 353, 'string': 'a string'},
                           {'number': 123, 'string': 'other string'}]

        # Call the function
        auto_repr_test_1 = AutoReprTest('a string', 353)
        auto_repr_test_2 = AutoReprTest('other string', 123)

        actual_result = auxiliary.list_to_json([auto_repr_test_1, auto_repr_test_2])

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_search_chars(self) -> None:
        """ Test the function search_chars. """

        # The expected result
        expected_result = [[19, 50], [4, 10, 24, 37], [16, 20, 27]]

        # Call the function
        text = 'Text, with, commas (and), parenthesis, everywhere (!)'

        actual_result = auxiliary.search_chars(text, ['(', ',', 'a'])

        # Verify the result
        self.assertEqual(expected_result, actual_result)

    def test_make_search_pattern(self) -> None:
        """ Test the function make_search_pattern. """

        # The expected result
        expected_result = '_cancaos?_as?_procurars?_'

        # Call the function
        text = 'canção a procurar'

        actual_result = auxiliary.make_search_pattern(text)

        # Verify the result
        self.assertEqual(expected_result, actual_result)
