import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
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


def set_tmdb_match(db_session: sqlalchemy.orm.Session, show: models.ShowData, tmdb_id: int, is_movie: bool):
    """
    Set a TMDB id as the match for a show.

    :param db_session: the DB session.
    :param show: the show being processed.
    :param tmdb_id: the TMDB id.
    :param is_movie: is the show a movie or not.
    """

    # Check if the tmdb_id is not already present in another entry
    original_show = db_calls.get_show_data_by_tmdb_id(db_session, tmdb_id)

    # If it is:
    if original_show is not None:
        # - change all sessions to the previous show_id
        show_sessions = db_calls.update_show_sessions(db_session, show.id, original_show.id)
        final_show = original_show
    else:
        show_sessions = db_calls.get_show_sessions_show_id(db_session, show.id)
        final_show = show

    show_correction = None

    # Create a correction either way
    if len(show_sessions) > 0:
        # But only if the info is different
        if show.original_title.casefold() != final_show.original_title.casefold() \
                or (show.year is not None and show.year != final_show.year):
            show_correction = db_calls.register_channel_show_data(db_session, show_sessions[0].channel_id,
                                                                  final_show.id, show.is_movie, show.original_title,
                                                                  show.portuguese_title, directors=show.director,
                                                                  year=show.year, subgenre=show.subgenre)

    # If it is:
    if original_show is not None:
        # - delete show
        db_session.delete(show)

    # If it isn't:
    else:
        # Get the data from TMDB
        tmdb_show = tmdb_calls.get_show_using_id(db_session, tmdb_id, is_movie)

        # - update the show data with the correct data
        update_show_data_with_tmdb(show, tmdb_show)

    if show_correction is not None:
        # Check if the correction is needed
        show_data = db_calls.search_show_data_by_original_title(db_session, show.original_title, show.is_movie,
                                                                directors=show.directors, year=show.year,
                                                                genre=show.genre)

        # If it isn't: delete it
        if show_data is not None and show_data.id == final_show.id:
            db_session.delete(show_correction)


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
        shows = db_calls.get_unmatched_show_data(db_session, 1)

        if len(shows) == 0:
            print('No more shows without a match!')
            return

        print('%s\n' % shows[0])

        question = 'What is the id of show?\n'
        tmdb_id = int(input(question))

        question = 'Is it a \'movie\' or a \'tv show\'?\n'
        is_movie = input(question) == 'movie'

        set_tmdb_match(db_session, shows[0], tmdb_id, is_movie)

    if option != 1:
        try:
            db_session.commit()
        except:
            db_session.rollback()
            raise

        set_tmdb_match_menu(db_session, call_count + 1)


def menu():
    """ Menu for choosing the utility function being run. """

    question = 'Choose one utility function:\n'
    question += '0 - Update search title\n'
    question += '1 - Set tmdb match\n'

    option = int(input(question))

    session = configuration.Session()

    try:
        if option == 0:
            update_searchable_titles_db(session)
        else:
            set_tmdb_match_menu(session, 0)

        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    menu()
