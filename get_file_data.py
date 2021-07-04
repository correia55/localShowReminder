import datetime
from typing import List, Optional

import sqlalchemy.orm

import db_calls
import models
import process_emails
import response_models
import tmdb_calls

unordered_words = ['the', 'a', 'an', 'i', 'un', 'le', 'la', 'les', 'um', 'o', 'el', 'as', 'os']


class InsertionResult:
    """To store the results of an insertion from a file."""

    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    total_nb_sessions_in_file: int
    nb_updated_sessions: int
    nb_added_sessions: int
    nb_deleted_sessions: int
    nb_new_shows: int

    def __init__(self):
        self.total_nb_sessions_in_file = 0
        self.nb_updated_sessions = 0
        self.nb_added_sessions = 0
        self.nb_deleted_sessions = 0
        self.nb_new_shows = 0


class ChannelInsertion:
    channels: str


def process_file_entry(db_session: sqlalchemy.orm.Session, insertion_result: InsertionResult, original_title: str,
                       localized_title: str, is_movie: bool, genre: str, date_time: datetime.datetime, channel_id: int,
                       year: Optional[int], directors: Optional[List[str]], subgenre: Optional[str],
                       synopsis: Optional[str], season: Optional[int], episode: Optional[int],
                       cast: Optional[str] = None, duration: Optional[int] = None, audio_languages: str = None,
                       countries: str = None, age_classification: Optional[str] = None,
                       session_audio_language: Optional[str] = None, extended_cut: bool = False,
                       creators: List[str] = None) -> Optional[InsertionResult]:
    """
    Process an entry in the file, inserting all of the needed data.

    :param db_session: the db session.
    :param insertion_result: the insertion result.
    :param original_title: the original title.
    :param localized_title: the localized title.
    :param is_movie: whether or not it is a movie.
    :param genre: the type of show (movie, series, documentary, ...).
    :param date_time: the datetime.
    :param channel_id: the id of the channel.
    :param year: the year of the show.
    :param directors: the directors of the show.
    :param subgenre: the subgenre of the show.
    :param synopsis: the synopsis.
    :param season: the season.
    :param episode: the episode.
    :param cast: the cast of the show.
    :param duration: the duration.
    :param audio_languages: the languages of the audio.
    :param countries: the countries.
    :param age_classification: the age classification.
    :param session_audio_language: the audio language for the current session.
    :param extended_cut: whether or not this is the extended cut.
    :param creators: the list of creators.
    :return: the updated insertion result, or None if there's a fatal error.
    """

    new_show = False

    # Search the ChannelShowDataCorrection
    channel_show_data = db_calls.search_channel_show_data_correction(db_session, channel_id, is_movie, original_title,
                                                                     localized_title, directors=directors, year=year,
                                                                     subgenre=subgenre, creators=creators)

    # If no match was found
    if channel_show_data is None:
        # Insert the ShowData, if necessary
        new_show, show_data = db_calls.insert_if_missing_show_data(db_session, localized_title, cast=cast,
                                                                   original_title=original_title, duration=duration,
                                                                   synopsis=synopsis, year=year, genre=genre,
                                                                   subgenre=subgenre, audio_languages=audio_languages,
                                                                   countries=countries, directors=directors,
                                                                   age_classification=age_classification,
                                                                   is_movie=is_movie, season=season, creators=creators)

        # If it is a new show, search the TMDB
        if new_show:
            insertion_result.nb_new_shows += 1
            tmdb_show = search_tmdb_match(db_session, show_data)

            # If it found a match in TMDB
            if tmdb_show:
                tmdb_show_data = db_calls.get_show_data_tmdb_id(db_session, tmdb_show.id)

                correction_needed = is_correction_needed(show_data, tmdb_show)

                # If an entry with that TMDB id already exists, delete the new one
                if tmdb_show_data is not None:
                    db_session.delete(show_data)
                    show_data = tmdb_show_data

                # If not, update the information
                else:
                    update_show_data_with_tmdb(show_data, tmdb_show)

                # If there are differences between the data from the TMDB and the one in the file
                if correction_needed:
                    db_calls.register_channel_show_data_correction(db_session, channel_id, show_data.id, is_movie,
                                                                   original_title, localized_title,
                                                                   directors=directors, year=year, subgenre=subgenre,
                                                                   creators=creators)
            else:
                print_message('no TMDB match found', True, str(show_data.id))

    # If it found a matching ChannelShowData
    else:
        show_data = db_calls.get_show_data_id(db_session, channel_show_data.show_id)

    # Process a show session
    return process_show_session(db_session, insertion_result, show_data, new_show, season, episode,
                                date_time, channel_id, audio_language=session_audio_language, extended_cut=extended_cut)


def process_show_session(db_session: sqlalchemy.orm.Session, insertion_result: InsertionResult,
                         show_data: models.ShowData, new_show: bool, season: Optional[int], episode: Optional[int],
                         date_time: datetime.datetime, channel_id: int, audio_language: str = None,
                         extended_cut: bool = False) -> Optional[InsertionResult]:
    """
    Process a show session.

    :param db_session: the db session.
    :param insertion_result: the insertion result.
    :param show_data: the corresponding show data.
    :param new_show: whether or not the show data was new.
    :param season: the season.
    :param episode: the episode.
    :param date_time: the datetime.
    :param channel_id: the id of the channel.
    :param audio_language: the audio language.
    :param extended_cut: whether or not this is the extended cut.
    :return: the updated insertion result, or None if there's a fatal error.
    """

    if show_data is None:
        print_message('insertion of Show Data', False, str(date_time))
        return None

    insertion_result.total_nb_sessions_in_file += 1

    # If it is a new show
    if new_show:
        add_show = True
    else:
        existing_show_session = db_calls.search_existing_session(db_session, season, episode, date_time, channel_id,
                                                                 show_data.id)

        # If there's already an existing session
        if existing_show_session is not None:
            add_show = False

            # Update its information
            existing_show_session.date_time = date_time
            existing_show_session.update_timestamp = datetime.datetime.utcnow()
        else:
            add_show = True

    # Insert the new session
    if add_show:
        show_session = db_calls.register_show_session(db_session, season, episode, date_time, channel_id, show_data.id,
                                                      audio_language=audio_language, extended_cut=extended_cut,
                                                      should_commit=False)

        if show_session is None:
            print('Session insertion failed!')
            return insertion_result

        insertion_result.nb_added_sessions += 1
    else:
        insertion_result.nb_updated_sessions += 1

    return insertion_result


def delete_old_sessions(db_session: sqlalchemy.orm.Session, start_datetime: datetime.datetime,
                        end_datetime: datetime.datetime, channels: List[str]) -> int:
    """
    Delete sessions that no longer exist.
    Send emails to the users whose reminders are associated with such sessions.

    :param db_session: the DB session.
    :param start_datetime: the start of the interval of interest.
    :param end_datetime: the end of the interval of interest.
    :param channels: the set of channels.
    :return: the number of deleted sessions.
    """

    nb_deleted_sessions = 0

    # Get the old show sessions
    old_sessions = db_calls.search_old_sessions(db_session, start_datetime, end_datetime, channels)

    for s in old_sessions:
        nb_deleted_sessions += 1

        # Get the reminders associated with this session
        reminders = db_calls.get_reminders_session(db_session, s.id)

        if len(reminders) != 0:
            # Get the session
            show_session = db_calls.get_show_session_complete(db_session, s.id)
            show_result = response_models.LocalShowResult.create_from_show_session(show_session[0], show_session[1],
                                                                                   show_session[2])

            # Warn all users with the reminders for this session
            for r in reminders:
                user = db_calls.get_user_id(db_session, r.user_id)

                process_emails.send_deleted_sessions_email(user.email, [show_result])

                # Delete the reminder
                db_session.delete(r)

        # Delete the session
        db_session.delete(s)

    db_session.commit()

    return nb_deleted_sessions


def search_tmdb_match(db_session: sqlalchemy.orm.Session, show_data: models.ShowData, use_year: bool = True) \
        -> Optional[tmdb_calls.TmdbShow]:
    """
    Search for a TMDB match.

    :param db_session: the DB session.
    :param show_data: the data of the show.
    :param use_year: whether to use the year in the search or not.
    :return: the TMDB show that matches.
    """

    if use_year:
        year = show_data.year
    else:
        year = None

    _, tmdb_shows = tmdb_calls.search_shows_by_text(db_session, show_data.original_title, is_movie=show_data.is_movie,
                                                    year=year)

    # Starting score
    if year is not None:
        starting_score = 5
    else:
        starting_score = 0

    best = None
    best_score = 0

    # Iterate over the results from the
    for t in tmdb_shows:
        score = starting_score

        # If the genre is a match
        if show_data.genre != 'Movie' and show_data.genre != 'Series' and show_data.genre in t.genres:
            score += 5

        # If the title is an exact match
        if t.original_title.casefold() == show_data.original_title.casefold():
            score += 20

        # Otherwise search for the director
        if show_data.director is not None and score < 25:
            directors = show_data.director.split(',')

            crew_list = tmdb_calls.get_show_crew_members(t.id, t.is_movie)

            found_director = False

            for member in crew_list:
                # Check the director's name in a case insensitive manner
                if member.name.casefold() in map(str.casefold, directors):
                    for job in member.jobs:
                        if job == 'Director':
                            score += 20
                            found_director = True
                            break

                    if found_director:
                        break

        # Otherwise search for the creator
        if show_data.creators is not None and score < 25:
            creators = show_data.creators.split(',')

            show_details = tmdb_calls.get_show_using_id(db_session, t.id, t.is_movie)

            for c in creators:
                # Check the creator's name in a case insensitive manner
                if c.casefold() in map(str.casefold, show_details.creators):
                    score += 20
                    break

        # Update the best match
        if score > best_score:
            best = t
            best_score = score

            # End if the score is at least 25
            if score >= 25:
                break

    # If the best it found had at least 20
    if best_score >= 20:
        return best
    else:
        # If it found not results, search again without year
        if use_year and year is not None:
            return search_tmdb_match(db_session, show_data, use_year=False)

        return None


def update_show_data_with_tmdb(show_data: models.ShowData, tmdb_show: tmdb_calls.TmdbShow):
    """
    Update a show data with the data from TMDB.

    :param show_data: the show data in the DB.
    :param tmdb_show: the corresponding TMDB show.
    """

    show_data.tmdb_id = tmdb_show.id
    show_data.tmdb_vote_average = tmdb_show.vote_average
    show_data.tmdb_popularity = tmdb_show.popularity

    show_data.year = tmdb_show.year
    show_data.original_title = tmdb_show.original_title

    if show_data.synopsis is None:
        show_data.synopsis = tmdb_show.overview

    if tmdb_show.creators is not None and len(tmdb_show.creators) > 0:
        show_data.creators = ','.join(tmdb_show.creators)
    else:
        show_data.creators = None

    # Delete information that is no longer useful
    if not show_data.is_movie:
        show_data.director = None
        show_data.cast = None


def is_correction_needed(show_data: models.ShowData, tmdb_show: tmdb_calls.TmdbShow):
    """
    Compare the data in the DB with the one from TMDB to check if a correction is needed.

    :param show_data: the show data in the DB.
    :param tmdb_show: the corresponding TMDB show.
    """

    # If the title is different
    if show_data.original_title.casefold() != tmdb_show.original_title.casefold():
        return True

    # If the creators are not a match
    if tmdb_show.creators is None and show_data.creators is not None:
        return True

    if show_data.creators is not None:
        is_match = False

        for c in show_data.creators:
            if c in tmdb_show.creators:
                is_match = True
                break

        if not is_match:
            return True

    if show_data.is_movie:
        # If the year is not a match
        if tmdb_show.year != show_data.year:
            return True

    return False


def print_message(message: str, warning: bool, identification: str):
    """
    Print a message for a warning or an error in a show.

    :param message: the message.
    :param warning: True, if it is a warning. False, for an error.
    :param identification: a string that identifies the show in the context of the message.
    """

    message_type = 'Warning' if warning else 'Error'

    print('%s: The show |%s| - %s!' % (message_type, identification, message))
