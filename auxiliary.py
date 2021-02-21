import datetime
import re
import unicodedata
from typing import List

import pytz


def strip_accents(text: str):
    """
    Source: https://stackoverflow.com/questions/517923/what-is-the-best-way-to-remove-accents-in-a-python-unicode-string

    Strip accents from input String.

    :param text: The input string.
    :returns: The processed String.
    """

    text = unicodedata.normalize('NFD', text)
    text = text.encode('ascii', 'ignore')
    text = text.decode("utf-8")

    return str(text)


def remove_quote(text: str):
    """
    Remove quote, grave and acute accents from text.

    :param text: The input string.
    :returns: The processed String.
    """

    return re.sub('[\'´`]', '', text)


def get_words(text: str):
    """
    Get the words in a text.

    :param text: the text.
    :return: a list of the words in the text.
    """

    processed_title = remove_quote(strip_accents(text))

    return re.compile('[^0-9A-Za-z]+').split(processed_title)


def make_searchable_title(title: str):
    """
    Remove accents from the title and join words with _ (underscore).

    :param title: the original title.
    :return: the resulting title.
    """

    return '_' + '_'.join(get_words(title)) + '_'


def get_datetime_with_tz_offset(date_time: datetime.datetime) -> datetime.datetime:
    """
    Get the datetime with the timezone offset.

    :param date_time: the datetime.
    :return: the datetime with the timezone offset.
    """

    return pytz.timezone('Europe/Lisbon').localize(date_time)


def convert_datetime_to_utc(date_time: datetime.datetime) -> datetime.datetime:
    """
    Convert a datetime to utc.

    :param date_time: the datetime.
    :return: the datetime in utc.
    """

    return date_time.astimezone(datetime.timezone.utc)


def auto_repr(cls):
    """
    Automatically generate the method __repr__ for a class.
    Source: https://stackoverflow.com/questions/32910096/is-there-a-way-to-auto-generate-a-str-implementation-in-python#33800620
    """

    def __repr__(self):
        return '%s(%s)' % (
            type(self).__name__,
            ', '.join('%s=%s' % item for item in vars(self).items())
        )

    cls.__repr__ = __repr__
    return cls


def list_to_json(list_of_objects):
    """Create a list with the result of to_dict for each element."""

    result = []

    for o in list_of_objects:
        result.append(o.to_dict())

    return result


def search_chars(text: str, chars: List[str]) -> List[List[int]]:
    """
    Get all indexes of a list of chars in a string.

    :param text: the text.
    :param chars: the list of chars of interest.
    :return: the list with the lists of indexes for each of the chars in the string.
    """

    search_result = [[] for _ in range(len(chars))]

    for i in range(len(text)):
        for j in range(len(chars)):
            if text[i] == chars[j]:
                search_result[j].append(i)
                break

    return search_result
