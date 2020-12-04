import json
import urllib.error
import urllib.parse
import urllib.request
from typing import List, Optional, Tuple

import sqlalchemy.orm

import auxiliary
import configuration
import db_calls


@auxiliary.auto_repr
class TmdbShow(object):
    """The class that will represent the data in the response from a search to tmdb."""

    id: int
    original_title: str
    origin_country: str
    original_language: str
    popularity: float
    overview: str
    title: str
    vote_average: float
    is_movie: bool
    adult: bool

    poster_path: Optional[str]
    origin_country: Optional[str]
    year: Optional[int]

    def __init__(self, show_dict: dict, is_movie: bool = None):
        if is_movie is not None:
            self.is_movie = is_movie
        else:
            self.is_movie = show_dict['media_type'] == 'movie'

        self.year = None

        if self.is_movie:
            self.original_title = show_dict['original_title']
            self.title = show_dict['title']

            if 'release_date' in show_dict and show_dict['release_date'] != '':
                self.year = int(show_dict['release_date'][0:4])
        else:
            self.original_title = show_dict['original_name']
            self.title = show_dict['name']

            if 'first_air_date' in show_dict and show_dict['first_air_date'] != '':
                self.year = int(show_dict['first_air_date'][0:4])

            self.origin_country = show_dict['origin_country']

        self.id = int(show_dict['id'])
        self.popularity = show_dict['popularity']
        self.vote_average = show_dict['vote_average']
        self.original_language = show_dict['original_language']
        self.overview = show_dict['overview']

        if 'adult' in show_dict:
            self.adult = show_dict['adult']

        if 'poster_path' in show_dict and show_dict['poster_path']:
            self.poster_path = 'https://image.tmdb.org/t/p/w220_and_h330_face' + show_dict['poster_path']
        else:
            self.poster_path = None


class TmdbTranslation(object):
    """The class that will represent a tmdb translation."""

    tmdb_id: int
    title: str
    overview: str
    language_country: str

    def __init__(self, tmdb_id: int, translation_dict: dict, is_movie: bool = None):
        self.tmdb_id = tmdb_id

        self.language_country = '%s-%s' % (
            translation_dict['iso_639_1'], translation_dict['iso_3166_1'])  # pt-PT, en-US...

        data: dict = translation_dict['data']

        self.overview = data['overview']

        if is_movie:
            self.title = data['title']
        else:
            self.title = data['name']


class TmdbAlias(object):
    """The class that will represent a tmdb translation."""

    tmdb_id: int
    title: str
    country: str

    def __init__(self, tmdb_id: int, alias_dict: dict):
        self.tmdb_id = tmdb_id

        self.country = alias_dict['iso_3166_1']
        self.title = alias_dict['title']


def search_show_by_id(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool, language: str = None) \
        -> Optional[TmdbShow]:
    """
    Get a show's information, from TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :param language: the language in which we want the response (pt-PT, en-US...).
    :return: the TmdbShow.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|id|%s-%s-%s' % (show_type, language, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        show_request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s?api_key=%s&language=%s'
                                              % (show_type, tmdb_id, configuration.tmdb_key, language))

        try:
            response = urllib.request.urlopen(show_request).read()
        except urllib.error.HTTPError:
            return None

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response to json
    response_dict = json.loads(response)

    return TmdbShow(response_dict, is_movie)


def search_shows_by_text(session: sqlalchemy.orm.Session, search_text: str, language: str = None, is_movie: bool = None,
                         page: int = 1) -> Tuple[int, List[TmdbShow]]:
    """
    Search shows by text, using TMDB.

    :param session: the db session.
    :param search_text: the search text.
    :param is_movie: if the show is a movie.
    :param language: the language in which we want the response (pt-PT, en-US...).
    :param page: the page to obtain.
    :return: a tuple with the total number of pages and the list of TmdbShow.
    """

    if is_movie is None:
        show_type = 'multi'
    else:
        if is_movie:
            show_type = 'movie'
        else:
            show_type = 'tv'

    cache_key = 'tmdb|text|%s-%s-%s-%s' % (show_type, language, search_text, page)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        search_request = urllib.request.Request('https://api.themoviedb.org/3/search/%s?api_key=%s&language=%s&query=%s'
                                                % (show_type, configuration.tmdb_key, language,
                                                   urllib.parse.quote(search_text)))

        # Add the page, when it exists
        if page:
            search_request.full_url = '%s&page=%d' % (search_request.full_url, page)

        try:
            response = urllib.request.urlopen(search_request).read()
        except urllib.error.HTTPError:
            return 0, []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbShow for each entry
    tmdb_shows = []

    for entry in response_dict['results']:
        # TODO: Need to change this, if I want to allow for searches to include people
        if show_type != 'multi' or entry['media_type'] == 'tv' or entry['media_type'] == 'movie':
            tmdb_shows.append(TmdbShow(entry, is_movie))

    return response_dict['total_pages'], tmdb_shows


def get_show_translations(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) \
        -> List[TmdbTranslation]:
    """
    Search for a show's translations, using TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :return: the list of TmdbTranslation.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|translations|%s-%s' % (show_type, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s/translations?api_key=%s'
                                         % (show_type, tmdb_id, configuration.tmdb_key))

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbTranslation for each entry
    tmdb_translations = []

    for entry in response_dict['translations']:
        tmdb_translations.append(TmdbTranslation(tmdb_id, entry, is_movie))

    return tmdb_translations


def get_show_aliases(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) \
        -> List[TmdbAlias]:
    """
    Search for a show's aliases, using TMDB.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: if the show is a movie.
    :return: the list of TmdbAlias.
    """

    if is_movie:
        show_type = 'movie'
    else:
        show_type = 'tv'

    cache_key = 'tmdb|aliases|%s-%s' % (show_type, tmdb_id)

    cache_entry = db_calls.get_cache(session, cache_key)

    # If there's a valid entry of cache for this request
    if cache_entry:
        response = cache_entry.result
    else:
        # Make the request
        request = urllib.request.Request('https://api.themoviedb.org/3/%s/%s/alternative_titles?api_key=%s'
                                         % (show_type, tmdb_id, configuration.tmdb_key))

        try:
            response = urllib.request.urlopen(request).read()
        except urllib.error.HTTPError:
            return []

        # Save the result in the cache
        db_calls.register_cache(session, cache_key, response.decode("utf-8"))

    # Parse the response
    response_dict = json.loads(response)

    # Create a TmdbTranslation for each entry
    tmdb_aliases = []

    if is_movie:
        for entry in response_dict['titles']:
            tmdb_aliases.append(TmdbAlias(tmdb_id, entry))
    else:
        for entry in response_dict['results']:
            tmdb_aliases.append(TmdbAlias(tmdb_id, entry))

    return tmdb_aliases


def collect_titles(session: sqlalchemy.orm.Session, tmdb_id: int, is_movie: bool) -> List[str]:
    """
    Get all tmdb titles for a tmdb id.

    :param session: the db session.
    :param tmdb_id: the tmdb id of the show.
    :param is_movie: true if it is a movie.
    :return a list with the titles from a show.
    """

    # Get the show's information from tmdb
    tmdb_show = search_show_by_id(session, tmdb_id, is_movie)

    # If no result is found
    if tmdb_show is None:
        return []

    titles = set()
    titles.add(tmdb_show.title)

    # Add the titles in the translations
    tmdb_translation_list = get_show_translations(session, tmdb_id, is_movie)

    for t in tmdb_translation_list:
        if (t.language_country.startswith('en') or t.language_country == 'pt-PT') \
                and t.title is not None and t.title != '':
            titles.add(t.title)

    # Add the titles in the aliases
    trak_alias_list = get_show_aliases(session, tmdb_id, is_movie)

    for a in trak_alias_list:
        if (a.country == 'US' or a.country == 'PT' or (not is_movie and a.country == tmdb_show.origin_country)) \
                and a.title is not None and a.title != '':
            titles.add(a.title)

    return list(titles)
