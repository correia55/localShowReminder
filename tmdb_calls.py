import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List

import configuration


class TmdbShow(object):
    """The class that will represent the data in the response from a search to tmdb."""

    id: int
    poster_path: str
    original_title: str
    origin_country: str
    original_language: str
    popularity: float
    overview: str
    title: str
    vote_average: float
    is_movie: bool

    def __init__(self, show_json_object, is_movie: bool = None):
        if is_movie is not None:
            self.is_movie = is_movie
        else:
            self.is_movie = show_json_object['media_type'] == 'movie'

        self.id = int(show_json_object['id'])
        self.poster_path = show_json_object['poster_path']

        if self.is_movie:
            self.original_title = show_json_object['original_title']
            self.title = show_json_object['title']
        else:
            self.original_title = show_json_object['original_name']
            self.title = show_json_object['name']

            self.origin_country = show_json_object['origin_country']

        self.popularity = show_json_object['popularity']
        self.vote_average = show_json_object['vote_average']

        # TODO: THE OVERVIEW CAN BE EMPTY FOR THE GIVEN LANGUAGE - NEED TO CHECK IT AND THEN ASK FOR THE ORIGINAL OVERVIEW
        self.overview = show_json_object['overview']


def search_shows_by_text(search_text: str, language: str, is_movie: bool = None) -> List[TmdbShow]:
    """
    Search shows by text, using TMDB.

    :param search_text: the search text.
    :param is_movie: if the show is a movie.
    :param language: the language in which we want the response (pt-PT, en-US...).
    :return: the list of TmdbShow.
    """

    if is_movie is None:
        show_type = 'multi'
    else:
        if is_movie:
            show_type = 'movie'
        else:
            show_type = 'tv'

    search_request = urllib.request.Request('https://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s'
                                            % (show_type, configuration.tmdb_key, language,
                                               urllib.parse.quote(search_text)))

    try:
        search_json = urllib.request.urlopen(search_request).read()
    except urllib.error.HTTPError:
        return []

    # Parse the response
    search_json_object = json.loads(search_json)

    # Create a TmdbShow for each entry
    tmdb_shows = []

    for entry in search_json_object['results']:
        tmdb_shows.append(TmdbShow(entry, is_movie))

    return tmdb_shows
