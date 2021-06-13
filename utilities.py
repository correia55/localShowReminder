from typing import List

import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data
import models
import process_emails
import tmdb_calls
from file_parsers.cinemundo import Cinemundo
from file_parsers.fox import Fox
from file_parsers.fox_movies import FoxMovies
from file_parsers.generic_xlsx import GenericXlsx
from file_parsers.odisseia import Odisseia
from file_parsers.tvcine import TVCine

channel_insertion_list = [Cinemundo, Odisseia, TVCine, Fox, FoxMovies, GenericXlsx]


def insert_file_data(db_session: sqlalchemy.orm.Session, channel_set: int, filename: str, channel_name: str) -> ():
    """
    Select the function according to the channel set.

    :param db_session: the DB session.
    :param channel_set: the set of channels of the file.
    :param filename: the name of the file.
    :param filename: the name of the channel.
    """

    print('Processing file...')

    result = channel_insertion_list[channel_set].add_file_data(db_session, filename, channel_name)

    if result is not None:
        print('complete!\n')
        print('The file contained %d show sessions!' % result.total_nb_sessions_in_file)
        print('Shows\' interval from %s to %s.\n' % (str(result.start_datetime), str(result.end_datetime)))

        print('%4d show sessions updated!' % result.nb_updated_sessions)
        print('%4d show sessions added!' % result.nb_added_sessions)
        print('%4d show sessions deleted!' % result.nb_deleted_sessions)
        print('%4d new shows!' % result.nb_new_shows)


def insert_file_data_submenu(db_session: sqlalchemy.orm.Session):
    """
    Execute a data insertion.

    :param db_session: the DB session.
    """

    question = 'Choose one channel set for the data being inserted:\n'

    for i in range(len(channel_insertion_list)):
        question += '%d - %s\n' % (i, channel_insertion_list[i].channels)

    input_channel_set = int(input(question))

    if len(channel_insertion_list[input_channel_set].channels) > 1 \
            and channel_insertion_list[input_channel_set] != TVCine:
        question = 'Choose one channel for the data being inserted:\n'

        for i in range(len(channel_insertion_list[input_channel_set].channels)):
            question += '%d - %s\n' % (i, channel_insertion_list[input_channel_set].channels[i])

        channel_name = channel_insertion_list[input_channel_set].channels[int(input(question))]
    else:
        channel_name = channel_insertion_list[input_channel_set].channels[0]

    input_filename = input('What is the path to the file?\n')

    insert_file_data(db_session, input_channel_set, input_filename, channel_name)


def update_searchable_titles_db(db_session: sqlalchemy.orm.Session):
    """
    Update the searchable titles in the DB.

    :param db_session: the DB session.
    """

    shows = db_session.query(models.ShowData).all()

    for show in shows:
        show.search_title = auxiliary.make_searchable_title(show.portuguese_title)


def set_tmdb_match(db_session: sqlalchemy.orm.Session, show_id: int, tmdb_id: int, is_movie: bool):
    """
    Set a TMDB id as the match for a show.

    :param db_session: the DB session.
    :param show_id: the id of the show being processed.
    :param tmdb_id: the TMDB id.
    :param is_movie: is the show a movie or not.
    """

    # Get the show
    show = db_calls.get_show_data_id(db_session, show_id)

    if show is None:
        print('Show with id %d not found!' % show_id)
        return

    # Save the original information for the creation of the corrections
    original_title = show.original_title
    year = show.year

    if show.director is not None:
        directors = show.director.split(',')
    else:
        directors = None

    # Check if the tmdb_id is not already present in another entry
    original_show = db_calls.get_show_data_by_tmdb_id(db_session, tmdb_id)

    # If it is:
    if original_show is not None:
        final_show = original_show

        # - change all sessions to the previous show_id
        show_sessions = db_calls.update_show_sessions(db_session, show_id, original_show.id)

        # - delete show
        db_session.delete(show)
    else:
        final_show = show

        # Get show sessions
        show_sessions = db_calls.get_show_sessions_show_id(db_session, show_id)

        # Get the data from TMDB
        tmdb_show = tmdb_calls.get_show_using_id(db_session, tmdb_id, is_movie)

        # - update the show data with the correct data
        get_file_data.update_show_data_with_tmdb(show, tmdb_show)

    # If there are sessions
    if len(show_sessions) > 0:
        # Check if the correction is needed
        show_data = db_calls.search_show_data_by_original_title(db_session, original_title, show.is_movie,
                                                                directors=directors, year=year, genre=show.genre)

        # If it is: add it
        if show_data is None or show_data.id != final_show.id:
            db_calls.register_channel_show_data_correction(db_session, show_sessions[0].channel_id, final_show.id,
                                                           show.is_movie, original_title, show.portuguese_title,
                                                           directors=directors, year=year, subgenre=show.subgenre)


def set_tmdb_match_submenu(db_session: sqlalchemy.orm.Session, call_count: int):
    """
    Print the menu for set_tmdb_match.

    :param db_session: the DB session.
    :param call_count: the call count for a function.
    """

    option = 0

    if call_count != 0:
        question = 'Choose one of the options:\n'
        question += '0 - Next\n'
        question += '1 - End\n'

        option = int(input(question))

    if option == 0:
        shows = db_calls.get_unmatched_show_data(db_session, 5)

        if len(shows) == 0:
            print('No more shows without a match!')

        for s in shows:
            print('%s\n' % s)

        question = 'What is the id of the show?\n'
        show_id = int(input(question))

        question = 'What is the matching TMBD id?\n'
        tmdb_id = int(input(question))

        question = 'Is it a \'movie\' or a \'tv show\'?\n'
        is_movie = input(question) == 'movie'

        set_tmdb_match(db_session, show_id, tmdb_id, is_movie)

    if option != 1:
        try:
            db_session.commit()
        except:
            db_session.rollback()
            raise

        set_tmdb_match_submenu(db_session, call_count + 1)


def search_tmdb_match(db_session: sqlalchemy.orm.Session):
    """
    Try to find a TMDB match for a given show.

    :param db_session: the DB session.
    """

    show_data = db_calls.get_show_data_id(db_session, int(input('Id of the show?')))

    if show_data is None:
        print('ShowData NOT found!')
        exit(0)

    tmdb_show = get_file_data.search_tmdb_match(db_session, show_data)

    if tmdb_show is None:
        print('TMDB Show NOT found!')
    else:
        print('TMDB Show found!')


def search_db_match(db_session: sqlalchemy.orm.Session):
    """
    Try to find a DB match for a given show.

    :param db_session: the DB session.
    """

    show_data = db_calls.get_show_data_id(db_session, int(input('Id of the show?')))

    if show_data is None:
        print('ShowData NOT found!')
        exit(0)

    query = db_session.query(models.ShowData) \
        .filter(models.ShowData.is_movie == show_data.is_movie) \
        .filter(sqlalchemy.func.lower(models.ShowData.original_title) == show_data.original_title.lower())

    if show_data.is_movie:
        if show_data.director is not None:
            directors = show_data.director.split(',')

            query = query.filter(sqlalchemy.or_(models.ShowData.director.contains(d) for d in directors))

        if show_data.year is not None:
            query = query.filter(models.ShowData.year == show_data.year)

    if show_data.genre is not None:
        query = query.filter(models.ShowData.genre == show_data.genre)

    # Checking if there's more than one match
    results: List[models.ShowData] = query.all()

    for r in results:
        if r.id != show_data.id:
            print('Found another match!')
            return

    print('Match NOT found!')


def menu():
    """ Menu for choosing the utility function being run. """

    question = 'Choose one utility function:\n'
    question += '0 - Get data from file\n\n'
    question += '1 - Update search title\n'
    question += '2 - Set tmdb match\n'
    question += '3 - Search tmdb match (for verification)\n'
    question += '4 - Search DB match (for verification)\n'

    option = int(input(question))

    session = configuration.Session()

    try:
        if option == 0:
            insert_file_data_submenu(session)
        elif option == 1:
            update_searchable_titles_db(session)
        elif option == 2:
            set_tmdb_match_submenu(session, 0)
        elif option == 3:
            search_tmdb_match(session)
        elif option == 4:
            search_db_match(session)

        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


def main():
    configuration.initialize()
    process_emails.initialize()

    menu()


if __name__ == '__main__':
    main()
