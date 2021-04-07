from typing import List

import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data
import models
import tmdb_calls


def update_searchable_titles_db(db_session: sqlalchemy.orm.Session):
    """
    Update the searchable titles in the DB.

    :param db_session: the DB session.
    """

    shows = db_session.query(models.ShowData).all()

    for show in shows:
        show.search_title = auxiliary.make_searchable_title(show.portuguese_title)


def update_show_data_with_tmdb(show_data: models.ShowData, tmdb_show: tmdb_calls.TmdbShow):
    """
    Update a show data with the data from TMDB.

    :param show_data: the show data in the DB.
    :param tmdb_show: the corresponding TMDB show.
    """

    show_data.tmdb_id = tmdb_show.id
    show_data.year = tmdb_show.year
    show_data.original_title = tmdb_show.original_title

    # Delete information that is no longer useful
    if not show_data.is_movie:
        show_data.director = None
        show_data.cast = None


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

    # Save the original information for the creation of the corrections
    original_title = show.original_title
    year = show.year
    directors = show.director

    if show is None:
        print('Show with id %d not found!' % show_id)
        return

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
        update_show_data_with_tmdb(show, tmdb_show)

    # If there are sessions
    if len(show_sessions) > 0:
        # Check if the correction is needed
        show_data = db_calls.search_show_data_by_original_title(db_session, original_title, show.is_movie,
                                                                directors=directors, year=year, genre=show.genre)

        # If it isn't: delete it
        if show_data is None or show_data.id != final_show.id:
            db_calls.register_channel_show_data_correction(db_session, show_sessions[0].channel_id, final_show.id,
                                                           show.is_movie, original_title, show.portuguese_title,
                                                           directors=directors, year=year, subgenre=show.subgenre)


def set_tmdb_match_menu(db_session: sqlalchemy.orm.Session, call_count: int):
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
        shows = db_calls.get_unmatched_show_data(db_session, 10)

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

        set_tmdb_match_menu(db_session, call_count + 1)


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
    question += '0 - Update search title\n'
    question += '1 - Set tmdb match\n'
    question += '2 - Search tmdb match (for verification)\n'
    question += '3 - Search DB match (for verification)\n'

    option = int(input(question))

    session = configuration.Session()

    try:
        if option == 0:
            update_searchable_titles_db(session)
        elif option == 1:
            set_tmdb_match_menu(session, 0)
        elif option == 2:
            search_tmdb_match(session)
        elif option == 3:
            search_db_match(session)

        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    menu()
