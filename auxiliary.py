import re
import unicodedata


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


def make_searchable_title(title):
    """
    Remove accents from the title and join words with _ (underscore).

    :param title: the original title.
    :return: the resulting title.
    """

    return '_' + '_'.join(get_words(title)) + '_'
