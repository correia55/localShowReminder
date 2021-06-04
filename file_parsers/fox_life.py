import datetime
import re
from typing import Optional

import openpyxl
import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data


class FoxLife(get_file_data.ChannelInsertion):
    channels = ['FOX Life']

    @staticmethod
    def process_title(title: str, is_movie: bool) -> str:
        """
        Process the title, removing the season and year.

        :param title: the title as is in the file.
        :param is_movie: whether it is a movie or not.
        :return: the title.
        """

        # Remove the season from the name
        if not is_movie:
            title = re.match('^(.+) [0-9]+$', title).group(1)

        # From the last position of the parenthesis
        search_result = auxiliary.search_chars(title, ['(', ')'])

        for i in range(len(search_result[0]) - 1, -1, -1):
            start_pos = search_result[0][i]
            end_pos = search_result[1][i]

            text = title[start_pos + 1:end_pos]

            # Check if it has an year
            if re.search(r'[0-9]{4}', text.strip()):
                pass
            else:
                continue

            # Remove the parenthesis and its context
            title = title[:search_result[0][i]] + title[search_result[1][i] + 1:]

        return title.strip()

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str) -> Optional[get_file_data.InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :return: the InsertionResult.
        """

        wb = openpyxl.load_workbook(filename)

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Skip row 1, with the headers
        for row in wb.active.iter_rows(min_row=2, max_col=16):
            # Skip the rows in which the year is not a number (header rows)
            if not isinstance(row[9].value, int):
                continue

            # Get the data
            date = datetime.datetime.strptime(row[0].value, '%d/%m/%Y')
            time = datetime.datetime.strptime(row[1].value, '%H:%M')
            localized_title = str(row[2].value)
            original_title = str(row[3].value)

            # Uncasted because they are optional
            season = row[4].value
            episode = row[5].value

            # episode_title = row[7].value
            synopsis = row[8].value
            year = int(row[9].value)
            cast = row[10].value
            directors = row[11].value
            creators = row[12].value

            # Duration comes in the format hh:mm
            duration = datetime.datetime.strptime(row[14].value, '%H:%M')
            duration = duration.hour * 60 + duration.minute

            age_classification = row[15].value

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

            # Check if it is a series
            if re.match('^ *$', season):
                season = None

            is_movie = season is None

            if is_movie:
                episode = None
            else:
                season = int(season)
                episode = int(episode)

            # Process the title
            original_title = FoxLife.process_title(original_title, is_movie)

            # Process the directors
            if directors is not None:
                if re.match('^ *$', directors):
                    directors = None
                else:
                    directors = directors.split(',')

            # Process the creators
            if creators is not None:
                if re.match('^ *$', creators):
                    creators = None
                else:
                    creators = creators.split(',')

            # Genre is movie, series, documentary, news...
            genre = 'Movie' if is_movie else 'Series'

            channel_id = db_calls.get_channel_name(db_session, 'FOX Life').id

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title,
                                                                is_movie, genre, date_time, channel_id, year, directors,
                                                                None,
                                                                synopsis, season, episode, cast=cast, duration=duration,
                                                                age_classification=age_classification,
                                                                creators=creators)

            if insertion_result is None:
                return None

        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Delete old sessions for the same time period
            file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
            file_end_datetime = date_time + datetime.timedelta(minutes=5)

            nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                    FoxLife.channels)

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = file_start_datetime
            insertion_result.end_datetime = file_end_datetime

            return insertion_result
        else:
            return None
