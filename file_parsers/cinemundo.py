import datetime
import re
from typing import Optional

import openpyxl
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data


class Cinemundo(get_file_data.ChannelInsertion):
    channels = ['Cinemundo']

    @staticmethod
    def process_title(title: str) -> [str, bool, int]:
        """
        Process the title, removing special markers:
        - VP - for portuguese audio.

        :param title: the title as is in the file.
        :return: a tuple with the clean title, whether it is a session with the portuguese voice and the season,
        when applicable.
        """

        # Replace all quotation marks for the same quotation mark
        title = re.sub('[´`]', '\'', title)

        # Search for VP in the end of the title
        vp = title.endswith('VP')

        if vp:
            # Remove the VP when it exists
            title = title[:-3]

        # Sometimes the title contains multiple titles
        char_pos = auxiliary.search_chars(title, ['/'])

        # Get the first title
        if len(char_pos[0]) > 0:
            title = title[:char_pos[0][0]]

        # Check if it is a series
        series = re.search(r'S[0-9]+', title.strip())

        if series is not None:
            season = int(series.group(0)[1:])
            title = title[:series.span(0)[0]]
        else:
            season = None

        return title.strip(), vp, season

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[get_file_data.InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel.
        :return: the InsertionResult.
        """

        wb = openpyxl.load_workbook(filename)

        first_event_datetime = None
        date_time = None

        insertion_result = get_file_data.InsertionResult()

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

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

            # If there's an invalid year, ignore this entry
            try:
                year = int(row[5].value)
            except ValueError:
                print('The \"' + original_title + '\" show had an invalid year!')
                continue

            age_classification = row[6].value
            directors = row[7].value
            cast = row[8].value
            subgenre = row[9].value  # Obtained in portuguese

            # Combine the date with the time
            date_time = date.replace(hour=time.hour, minute=time.minute)

            # Add the Lisbon timezone info, then convert it to UTC
            # and then remove the timezone info
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                .replace(tzinfo=None)

            # Ignore old sessions
            if date_time < (today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                continue

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            # Process the titles
            localized_title, vp, _ = Cinemundo.process_title(localized_title)
            audio_language = 'pt' if vp else None

            original_title, _, season = Cinemundo.process_title(original_title)

            if season is not None:
                is_movie = False
                genre = 'Series'
            else:
                is_movie = True
                genre = 'Movie'

            # Process the directors
            if directors is not None:
                directors = re.split(',| e ', directors)

            # Get the channel's id
            channel_id = db_calls.get_channel_name(db_session, 'Cinemundo').id

            # Process an entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title,
                                                                is_movie, genre, date_time, channel_id, year, directors,
                                                                subgenre,
                                                                synopsis, season, None, cast=cast,
                                                                age_classification=age_classification,
                                                                audio_languages=audio_language)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Delete old sessions for the same time period
            file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
            file_end_datetime = date_time + datetime.timedelta(minutes=5)

            nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                    Cinemundo.channels)

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = file_start_datetime
            insertion_result.end_datetime = file_end_datetime

            return insertion_result
        else:
            return None
