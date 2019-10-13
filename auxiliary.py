import re
import unicodedata


def strip_accents(text):
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
