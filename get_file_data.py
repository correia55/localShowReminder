import datetime
import re
import xml.dom.minidom
from typing import List, Optional

import openpyxl
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import models
import process_emails
import response_models

unordered_words = ['The', 'A', 'An', 'I', 'Un', 'Le', 'La', 'Les', 'Um']


class InsertionResult:
    """To store the results of an insertion from a file."""

    start_datetime: datetime.datetime
    end_datetime: datetime.datetime
    total_nb_sessions_in_file: int
    nb_updated_sessions: int
    nb_added_sessions: int
    nb_deleted_sessions: int

    def __init__(self, start_datetime: datetime.datetime = None, end_datetime: datetime.datetime = None,
                 total_nb_sessions_in_file: int = 0, nb_updated_sessions: int = 0, nb_added_sessions: int = 0,
                 nb_deleted_sessions: int = 0):
        self.start_datetime = start_datetime
        self.end_datetime = end_datetime
        self.total_nb_sessions_in_file = total_nb_sessions_in_file
        self.nb_updated_sessions = nb_updated_sessions
        self.nb_added_sessions = nb_added_sessions
        self.nb_deleted_sessions = nb_deleted_sessions


class ChannelInsertion:
    channels: str


class Cinemundo(ChannelInsertion):
    channels = ['Cinemundo']

    @staticmethod
    def process_title(title: str) -> [str, bool]:
        """
        Process the title, removing special markers:
        - VP - for portuguese audio.

        :param title: the title as is in the file.
        :return: a tuple with the clean title and whether or not it is a session with the portuguese voice.
        """

        # Replace all quotation marks for the same quotation mark
        title = re.sub('[´`]', '\'', title)

        # Search for VP in the end of the title
        vp = title.endswith('VP')

        if vp:
            # Remove the VP when it exists
            title = title[:-3]

        return title.strip(), vp

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str) -> Optional[InsertionResult]:
        wb = openpyxl.load_workbook(filename)

        insertion_result = InsertionResult()

        # Skip row 1, with the headers
        for row in wb.active.iter_rows(min_row=3, max_col=12):
            # Skip rows that do not contain a date
            if row[0].value is None:
                continue

            # Get the data
            date = datetime.datetime.strptime(str(row[0].value), '%Y%m%d')
            time = row[1].value
            original_title = str(row[2].value)
            localized_title = str(row[3].value)
            synopsis = row[4].value
            year = int(row[5].value)
            age_classification = row[6].value
            director = row[7].value
            cast = row[8].value
            show_type = row[9].value

            # Combine the date with the time
            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Process the titles
            localized_title, vp = Cinemundo.process_title(localized_title)
            audio_language = 'pt' if vp else None

            original_title, _ = Cinemundo.process_title(original_title)

            # Get the channel id
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == 'Cinemundo').first().id

            # Insert the ShowData, if necessary
            new_show, show_data = db_calls.insert_if_missing_show_data(db_session, localized_title,
                                                                       original_title=original_title, synopsis=synopsis,
                                                                       year=year, show_type=show_type,
                                                                       director=director,
                                                                       cast=cast, age_classification=age_classification,
                                                                       is_movie=True)

            # Process a show session
            insertion_result = process_show_session(db_session, insertion_result, show_data, new_show, original_title,
                                                    None, None, date_time, channel_id, audio_language=audio_language)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Get the start and end of month
            start_of_month = date.replace(day=1)

            if start_of_month.month != 12:
                end_of_month = start_of_month.replace(month=start_of_month.month + 1)
            else:
                end_of_month = start_of_month.replace(year=start_of_month.year, month=1)

            nb_deleted_sessions = delete_old_sessions(db_session, start_of_month, end_of_month, Cinemundo.channels)

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = start_of_month
            insertion_result.end_datetime = end_of_month

            return insertion_result
        else:
            return None


class Odisseia(ChannelInsertion):
    channels = ['Odisseia']

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str) -> Optional[InsertionResult]:
        dom_tree = xml.dom.minidom.parse(filename)
        collection = dom_tree.documentElement

        first_event_datetime = None

        # Get all events
        events = collection.getElementsByTagName('Event')

        # If there are no events
        if len(events) == 0:
            return None

        insertion_result = InsertionResult()

        # Process each event
        for event in events:
            begin_time = event.getAttribute('beginTime')
            date_time = datetime.datetime.strptime(begin_time, '%Y%m%d%H%M%S')

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            duration = int(int(event.getAttribute('duration')) / 60)

            epg_production = event.getElementsByTagName('EpgProduction')[0]

            genere_list = epg_production.getElementsByTagName('Genere')

            if len(genere_list) > 0:
                category = genere_list[0].firstChild.nodeValue
            else:
                category = None

            show_type = epg_production.getElementsByTagName('Subgenere')[0].firstChild.nodeValue

            epg_text = epg_production.getElementsByTagName('EpgText')[0]

            portuguese_title = epg_text.getElementsByTagName('Name')[0].firstChild.nodeValue
            broadcast_name = epg_text.getElementsByTagName('BroadcastName')[0].firstChild.nodeValue

            synopsis = None

            # If they are the names are the same, it's a movie
            if broadcast_name == portuguese_title:
                short_description = epg_text.getElementsByTagName('ShortDescription')

                if short_description is not None and short_description[0].firstChild is not None:
                    synopsis = short_description[0].firstChild.nodeValue

            extended_info_elements = epg_text.getElementsByTagName('ExtendedInfo')

            original_title = None
            year = None
            director = None
            countries = None
            season = None
            episode = None

            for extended_info in extended_info_elements:
                attribute = extended_info.getAttribute('name')

                if attribute == 'OriginalEventName' and extended_info.firstChild is not None:
                    original_title = extended_info.firstChild.nodeValue
                elif attribute == 'Year' and extended_info.firstChild is not None:
                    year = int(extended_info.firstChild.nodeValue)
                elif attribute == 'Director' and extended_info.firstChild is not None:
                    director = extended_info.firstChild.nodeValue
                elif attribute == 'Nationality' and extended_info.firstChild is not None:
                    countries = extended_info.firstChild.nodeValue
                elif attribute == 'Cycle' and extended_info.firstChild is not None:
                    season = extended_info.firstChild.nodeValue
                elif attribute == 'EpisodeNumber' and extended_info.firstChild is not None:
                    episode = extended_info.firstChild.nodeValue

            if episode is not None:
                if season is None:
                    print('Found episode but no season for show: %s' % str(event.getAttribute('beginTime')))
                    season = 1

            channel_name = 'Odisseia'
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            # Insert the ShowData, if necessary
            new_show, show_data = db_calls.insert_if_missing_show_data(db_session, portuguese_title,
                                                                       original_title=original_title, duration=duration,
                                                                       synopsis=synopsis, year=year,
                                                                       show_type=show_type, director=director,
                                                                       countries=countries, category=category,
                                                                       is_movie=episode is None)

            # Process a show session
            insertion_result = process_show_session(db_session, insertion_result, show_data, new_show, original_title,
                                                    season, episode, date_time, channel_id)

            if insertion_result is None:
                return None

        db_calls.commit(db_session)

        first_day_at_start = first_event_datetime.replace(hour=0, minute=0, second=0)
        end_day_at_start = (date_time + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=0) \
                           - datetime.timedelta(seconds=1)

        nb_deleted_sessions = delete_old_sessions(db_session, first_day_at_start, end_day_at_start, Odisseia.channels)

        # Set the remaining information
        insertion_result.nb_deleted_sessions = nb_deleted_sessions
        insertion_result.start_datetime = first_day_at_start
        insertion_result.end_datetime = end_day_at_start

        return insertion_result


class TVCine(ChannelInsertion):
    channels = ['TVCine Top', 'TVCine Edition', 'TVCine Emotion', 'TVCine Action']

    @staticmethod
    def process_title(title: str) -> [str, bool, bool]:
        """
        Process the title, removing special markers and reformatting the title:
        - (VP) - for portuguese audio;
        - (VO) - for original audio;
        - (extended cut) or (versão alargada) - for extended cut;
        - some of the words come unordered, thus the unordered list of words.

        :param title: the title as is in the file.
        :return: a tuple with the clean title, whether or not it is a session with the portuguese voice and whether or
        not it is a session with the extended cut.
        """

        # Replace all quotation marks for the same quotation mark
        title = re.sub('[´`]', '\'', title)

        search_result = auxiliary.search_chars(title, ['(', ')', ','])
        vp = False
        extended_cut = False

        # If there's at least a comma in the title - it would always be at the end
        if len(search_result[2]) > 0:
            last_comma = search_result[2][-1]

            after_comma = title[last_comma + 1:].strip()

            # If it's one of the unordered words
            if after_comma in unordered_words:
                title = after_comma + ' ' + title[:last_comma]

        # If the number of opening parenthesis is not the same as the closing ones
        if len(search_result[0]) != len(search_result[1]):
            return title.strip(), vp

        # From the last position of the parenthesis
        for i in range(len(search_result[0]) - 1, -1, -1):
            start_pos = search_result[0][i]
            end_pos = search_result[1][i]

            text = title[start_pos + 1:end_pos]

            if text == 'VP':
                vp = True
            elif text == 'VO':
                vp = False
            elif text == 'versão alargada' or text == 'extended cut':
                extended_cut = True
            elif re.search(r'[0-9]{4}', text.strip()):
                pass
            else:
                continue

            # Remove the parenthesis and its context
            title = title[:search_result[0][i]] + title[search_result[1][i] + 1:]

        return title.strip(), vp, extended_cut

    @staticmethod
    def update_show_list(db_session: sqlalchemy.orm.Session, filename: str) -> Optional[InsertionResult]:
        wb = openpyxl.load_workbook(filename)

        insertion_result = InsertionResult()

        # Skip row 1, with the headers
        for row in wb.active.iter_rows(min_row=2, max_col=15):
            # Skip rows that contain only the date
            if row[0].value is None:
                continue

            # Skip the rows in which the year is not a number (header rows)
            if not isinstance(row[4].value, int):
                continue

            # Get the data
            channel_name = row[0].value
            date = row[1].value
            time = row[2].value
            original_title = str(row[3].value)
            year = int(row[4].value)
            age_classification = row[5].value
            show_type = row[6].value
            duration = int(row[7].value)
            languages = row[8].value
            countries = row[9].value
            synopsis = row[10].value
            director = row[11].value
            cast = row[12].value
            title = str(row[13].value)
            # episode_title = row[14].value

            # Combine the date with the time
            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Check if it matches the regex of a series
            series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', title.strip())

            audio_language = None

            # If it is a series, extract it's season and episode
            if series:
                title = series.group(1)
                is_movie = False

                season = int(series.group(2))
                episode = int(series.group(3))

                # episode_synopsis = synopsis
                synopsis = None

                # Also get the original title without the season and episode
                series = re.search('(.+) T([0-9]+),[ ]+([0-9]+)', original_title.strip())

                if series:
                    original_title = series.group(1)
            else:
                season = None
                episode = None
                # episode_synopsis = None

                # Process the titles
                title, vp, extended_cut = TVCine.process_title(title)
                audio_language = 'pt' if vp else None

                original_title, _, _ = TVCine.process_title(original_title)

                is_movie = True

            # Sometimes the cast is switched with the director
            if cast is not None and director is not None:
                cast_commas = auxiliary.search_chars(cast, [','])[0]
                director_commas = auxiliary.search_chars(director, [','])[0]

                # When that happens, switch them
                if len(cast_commas) < len(director_commas):
                    aux = cast
                    cast = director
                    director = aux

            channel_name = 'TVCine ' + channel_name.strip().split()[1]
            channel_id = db_session.query(models.Channel).filter(models.Channel.name == channel_name).first().id

            # Insert the ShowData, if necessary
            new_show, show_data = db_calls.insert_if_missing_show_data(db_session, title, original_title=original_title,
                                                                       duration=duration, synopsis=synopsis, year=year,
                                                                       show_type=show_type, director=director,
                                                                       cast=cast, audio_languages=languages,
                                                                       countries=countries,
                                                                       age_classification=age_classification,
                                                                       is_movie=is_movie)

            # Process a show session
            insertion_result = process_show_session(db_session, insertion_result, show_data, new_show, original_title,
                                                    season, episode, date_time, channel_id,
                                                    audio_language=audio_language, extended_cut=extended_cut)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Get the start and end of month
            start_of_month = date.replace(day=1)

            if start_of_month.month != 12:
                end_of_month = start_of_month.replace(month=start_of_month.month + 1)
            else:
                end_of_month = start_of_month.replace(year=start_of_month.year, month=1)

            nb_deleted_sessions = delete_old_sessions(db_session, start_of_month, end_of_month, TVCine.channels)

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = start_of_month
            insertion_result.end_datetime = end_of_month

            return insertion_result
        else:
            return None


channel_insertion_list = [Cinemundo, Odisseia, TVCine]


def process_show_session(db_session: sqlalchemy.orm.Session, insertion_result: InsertionResult,
                         show_data: models.ShowData, new_show: bool, original_title: str, season: Optional[int],
                         episode: Optional[int], date_time: datetime.datetime, channel_id: int,
                         audio_language: str = None, extended_cut: bool = False) -> Optional[InsertionResult]:
    """
    Process a show session.

    :param db_session: the db session.
    :param insertion_result: the insertion result.
    :param show_data: the corresponding show data.
    :param new_show: whether or not the show data was new.
    :param original_title: the original title of the show.
    :param season: the season.
    :param episode: the episode.
    :param date_time: the datetime.
    :param channel_id: the id of the channel.
    :param audio_language: the audio language.
    :param extended_cut: whether or not this is the extended cut.
    :return: the updated insertion result, or None if there's a fatal error.
    """

    if show_data is None:
        print('Error: Insertion of Show Data %s failed!' % original_title)
        return None

    if show_data.director is None:
        print('Warning: Director not provided for: %s!' % original_title)

    insertion_result.total_nb_sessions_in_file += 1

    # If it is a new show
    if new_show:
        add_show = True
    else:
        existing_show_session = db_calls.search_existing_session(db_session, season, episode, date_time,
                                                                 channel_id, show_data.id)

        # If there's already an existing session
        if existing_show_session is not None:
            add_show = False

            existing_show_session.date_time = date_time
            existing_show_session.update_timestamp = datetime.datetime.now()
        else:
            add_show = True

    # Insert the new session
    if add_show:
        db_calls.register_show_session(db_session, season, episode, date_time, channel_id, show_data.id,
                                       audio_language=audio_language, extended_cut=extended_cut, should_commit=False)

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


def update_show_list(db_session: sqlalchemy.orm.Session, channel_set: int, filename: str) -> ():
    """
    Select the function according to the channel set.

    :param db_session: the DB session.
    :param channel_set: the set of channels of the file.
    :param filename: the name of the file.
    """

    print('Processing file...')

    result = channel_insertion_list[channel_set].update_show_list(db_session, filename)

    if result is not None:
        print('complete!\n')
        print('The file contained %d show sessions!' % result.total_nb_sessions_in_file)
        print('Shows\' interval from %s to %s.\n' % (str(result.start_datetime), str(result.end_datetime)))

        print('%4d show sessions updated!' % result.nb_updated_sessions)
        print('%4d show sessions added!' % result.nb_added_sessions)
        print('%4d show sessions deleted!' % result.nb_deleted_sessions)


def execute_data_insertion():
    """ Execute a data insertion. """

    question = 'Choose one channel set for the data being inserted:\n'

    for i in range(len(channel_insertion_list)):
        question += '%d - %s\n' % (i, channel_insertion_list[i].channels)

    input_channel_set = int(input(question))

    input_filename = input('What is the path to the file?\n')

    session = configuration.Session()

    try:
        update_show_list(session, input_channel_set, input_filename)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == '__main__':
    execute_data_insertion()
