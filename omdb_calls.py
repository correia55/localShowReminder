import json
import urllib.error
import urllib.request
from typing import Optional

import configuration


class OmdbShow(object):
    """The class that will represent the data in the response from a search to Omdb."""

    poster: str

    def __init__(self, show_json_object):
        self.poster = show_json_object['Poster']


def search_show_by_imdb_id(imdb_id: str) -> Optional[OmdbShow]:
    """
    Get a show's information, from Omdb.

    :param imdb_id: the imdb id of the show.
    :return: the OmdbShow.
    """

    if configuration.omdb_key is None or imdb_id is None:
        return None

    search_show_request = urllib.request.Request('http://www.omdbapi.com/?apikey=%s&i=%s'
                                                 % (configuration.omdb_key, imdb_id))

    try:
        search_json = urllib.request.urlopen(search_show_request).read()
    except urllib.error.HTTPError:
        return None

    # Parse the show from the request
    show_json_object = json.loads(search_json)

    # When the Omdb can't find the information
    if show_json_object['Response'] == 'False':
        return None

    return OmdbShow(show_json_object)
