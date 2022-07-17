import datetime
import re
from typing import Optional, Dict

import openpyxl
import sqlalchemy.orm
import xlrd as xlrd

import auxiliary
import configuration
import db_calls
import get_file_data
from file_parsers.abstract_channel_file_parser import InsertionResult, GenericField
from abstract_spreadsheet_parser import AbstractSpreadsheetParser, Header


class GenericListSpreadsheetParser(AbstractSpreadsheetParser):
    channels_file = {'Nat Geo Wild': ('Nat Geo Wild', 'nat_geo_wild.csv'),
                     'National Geographic': ('National Geographic', 'national_geographic.csv'),
                     'FOX': ('FOX', 'fox.csv'), 'FOX Life': ('FOX Life', 'fox.csv'),
                     'FOX Comedy': ('FOX Comedy', 'fox.csv'), 'FOX Crime': ('FOX Crime', 'fox_crime.csv'),
                     'FOX Movies': ('FOX Movies', 'fox_movies.csv'),
                     'Disney Junior': ('Disney Junior', 'disney_junior.csv'),
                     'Disney Channel': ('Disney Channel', 'disney_junior.csv'),
                     'Hollywood': ('Hollywood', 'hollywood.csv'), 'Blast': ('Blast', 'blast.csv'),
                     'História': ('História', 'historia.csv')}
    channels = list(channels_file.keys())

    @staticmethod
    def process_title(title: str, title_format: str, is_movie: bool) -> str:
        """
        Process the title, removing the year.

        :param title: the title as is in the file.
        :param title_format: the format of the title.
        :param is_movie: whether this entry is a movie.
        :return: the title.
        """

        if not is_movie:
            if 'S_season_at_the_end' in title_format:
                series = re.search(r'S\d+', title.strip())

                if series is not None:
                    title = title[:series.span(0)[0]]
            elif 'season_at_the_end' in title_format:
                series = re.search(r'^(.*) \d+$', title.strip())

                if series is not None:
                    title = series.group(1)
            elif 'season_and_episode_at_the_end' in title_format:
                series = re.search(r'^(.*) T\d+, ?\d+$', title.strip())

                if series is not None:
                    title = series.group(1)

        if 'has_year' in title_format:
            # From the last position of the parenthesis
            search_result = auxiliary.search_chars(title, ['(', ')'])

            for i in range(len(search_result[0]) - 1, -1, -1):
                start_pos = search_result[0][i]
                end_pos = search_result[1][i]

                text = title[start_pos + 1:end_pos]

                # Check if it has an year
                if re.search(r'\d{4}', text.strip()):
                    pass
                else:
                    continue

                # Remove the parenthesis and its context
                title = title[:search_result[0][i]] + title[search_result[1][i] + 1:]

        # Replace all quotation marks for the same quotation mark
        return re.sub('[´`]', '\'', title.strip())

    @staticmethod
    def process_date(date_value: str, date_field_format: str) -> str:
        """
        Process the date, removing unnecessary config.

        :param date_value: the config as is in the file.
        :param date_field_format: the format of the date, as in the configuration file.
        :return: the date as string.
        """

        if date_field_format == 'day_space_date':
            date_value = date_value.split(' ')[-1]
        else:
            print('The date field format: %s is not recognized!' % date_field_format)
            date_value = None

        return date_value

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[InsertionResult]:

        # Channel information
        channel_info = GenericListSpreadsheetParser.channels_file[channel_name]

        channel_name = channel_info[0]
        channel_file = channel_info[1]

        # Get the position and format of the fields for this channel
        data_fields: Dict[str, GenericField]
        config_fields: Dict[str, GenericField]

        data_fields, config_fields = GenericListSpreadsheetParser.process_configuration(channel_file)

        # If it is invalid
        if data_fields is None or config_fields is None:
            return None

        # Get the extension of the file
        file_format = filename.split('.')[-1]

        if file_format != 'xls' and file_format != 'xlsx':
            print('Invalid file format: %s!' % file_format)
            return None

        # Prepare for reading, according to the file extension
        if file_format == 'xls':
            book = xlrd.open_workbook(filename, on_demand=True)
            sheet = book.sheet_by_index(0)
            rows = sheet.nrows
        else:
            # Remark: setting the read_only to true, changes the number of rows
            book = openpyxl.load_workbook(filename, data_only=True)
            sheet = book.active
            rows = sheet.max_row

        # Get the channel id from the DB
        channel_id = db_calls.get_channel_name(db_session, channel_name).id

        # Initialize variables
        insertion_result = InsertionResult()

        first_event_datetime = None
        date_time = None
        date = None

        got_headers = False
        header_map: Dict[str, Header] = dict()

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Iterating over the rows of the file
        for rx in range(rows):
            if file_format == 'xls':
                row = sheet.row(rx)
            else:
                row = sheet[rx + 1]

            # If we haven't found the header row
            if not got_headers:
                got_headers, header_map = GenericListSpreadsheetParser.parse_headers_row(config_fields, data_fields,
                                                                                         channel_name, row)

                continue

            # -- Process the data of the row --
            # ---------------------------------
            if row[header_map['time'].position].value is not None and row[header_map['time'].position].value:
                # Parse time
                time = GenericListSpreadsheetParser.parse_time(row[header_map['time'].position].value,
                                                               header_map['time'].field_format,
                                                               file_format, book)
            else:
                time = None

            # If the date is in a separate row
            if '_date_separate_line' in config_fields:
                cell_value = str(row[0].value)

                # While we don't have a date, skip rows where the date is empty
                if date is None:
                    if cell_value is None or not cell_value:
                        continue

                # If there's a date, update the current date
                if cell_value is not None and cell_value:
                    date_value = GenericListSpreadsheetParser.process_date(cell_value,
                                                                           config_fields[
                                                                               '_date_separate_line'].field_format)

                    # Parse date, and skip the row
                    date = GenericListSpreadsheetParser.parse_date(date_value, config_fields['_date'].field_format,
                                                                   file_format, book)
                    continue

            # Get the date_time
            if 'date_time' in header_map:
                date_time = datetime.datetime.strptime(row[header_map['date_time'].position].value,
                                                       header_map['date_time'].field_format)
            else:
                if time is None:
                    continue

                if '_date_separate_line' not in config_fields:
                    date = GenericListSpreadsheetParser.parse_date(row[header_map['date'].position].value,
                                                                   header_map['date'].field_format,
                                                                   file_format, book)

                if date is None:
                    continue

                # Combine the date with the time
                date_time = date.replace(hour=time.hour, minute=time.minute)

            if 'year' in header_map:
                # Skip the rows in which the year is invalid
                if row[header_map['year'].position].value is None:
                    continue

                try:
                    year = int(row[header_map['year'].position].value)
                except ValueError:
                    continue
            else:
                year = None

            # Add the Lisbon timezone info, then convert it to UTC
            # and then remove the timezone info
            date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                .replace(tzinfo=None)

            # Ignore old sessions
            if date_time < (today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                continue

            if 'original_title' in header_map:
                original_title = str(row[header_map['original_title'].position].value)
            else:
                original_title = None

            localized_title = str(row[header_map['localized_title'].position].value)

            # If it is a placeholder show or temporary program
            if '_temporary_program' in config_fields:
                if str(config_fields['_temporary_program'].field_format) in original_title:
                    continue

            if 'localized_synopsis' in header_map:
                synopsis = str(row[header_map['localized_synopsis'].position].value).strip()
            else:
                synopsis = None

            if 'cast' in header_map:
                cast = row[header_map['cast'].position].value

                if cast is not None:
                    cast = cast.strip()

                    if len(cast) == 0:
                        cast = None
            else:
                cast = None

            if 'directors' in header_map:
                directors = row[header_map['directors'].position].value

                # Process the directors
                if directors is not None:
                    if re.match('^ *$', directors):
                        directors = None
                    else:
                        directors = directors.split(',')

                # If the name of the directors is actually a placeholder
                if '_ignore_directors' in config_fields and directors:
                    if directors[0].strip() == config_fields['_ignore_directors'].field_format:
                        directors = None
            else:
                directors = None

            if 'creators' in header_map:
                creators = row[header_map['creators'].position].value

                # Process the creators
                if creators is not None:
                    if re.match('^ *$', creators):
                        creators = None
                    else:
                        creators = creators.split(',')
            else:
                creators = None

            if 'countries' in header_map:
                countries = row[header_map['countries'].position].value.strip()
            else:
                countries = None

            # Duration
            if 'duration' in header_map:
                if header_map['duration'].field_format == 'seconds':
                    duration = int(int(row[header_map['duration'].position].value) / 60)
                else:
                    if file_format == 'xls':
                        try:
                            duration = xlrd.xldate_as_datetime(row[header_map['duration'].position].value,
                                                               book.datemode)
                        except TypeError:
                            duration = datetime.datetime.strptime(row[header_map['duration'].position].value,
                                                                  header_map['duration'].field_format)
                    else:
                        try:
                            duration = datetime.datetime.strptime(row[header_map['duration'].position].value,
                                                                  header_map['duration'].field_format)
                        except TypeError:
                            duration_time: datetime.time = row[header_map['duration'].position].value
                            duration = datetime.datetime(1, 1, 1, duration_time.hour, duration_time.minute)

                    duration = duration.hour * 60 + duration.minute
            else:
                duration = None

            if 'age_classification' in header_map:
                age_classification = str(row[header_map['age_classification'].position].value).strip()
            else:
                age_classification = None

            if 'subgenre' in header_map:
                subgenre = row[header_map['subgenre'].position].value.strip()
            else:
                subgenre = None

            # Process the audio language of the session
            session_audio_language = None

            if 'session_audio_language' in header_map:
                session_audio_language = row[header_map['session_audio_language'].position].value

                if session_audio_language == 'VP':
                    session_audio_language = 'pt'
                else:
                    session_audio_language = None

            # Get the first event's datetime
            if first_event_datetime is None:
                first_event_datetime = date_time

            if 'season' not in header_map or 'episode' not in header_map:
                season = None
                episode = None
            else:
                if header_map['season'].field_format == 'season_starts_with_T':
                    season_str = row[header_map['season'].position].value

                    if season_str is not None:
                        season = re.search(r'^T([0-9]+)$', str(row[header_map['season'].position].value).strip())

                        if season is not None:
                            season = int(season.group(1))
                    else:
                        season = None
                else:
                    try:
                        season = int(row[header_map['season'].position].value)
                    except ValueError:
                        try:
                            # There are entries with a season 2.5, which will be converted to 2
                            season = int(float(row[header_map['season'].position].value))
                        except ValueError:
                            season = None

                    # Some files use 0 as a placeholder
                    if season == 0:
                        season = None

                    episode = None

                if header_map['episode'].field_format == 'int':
                    try:
                        episode = int(row[header_map['episode'].position].value)
                    except ValueError:
                        episode = None
                elif 'title_with_Ep.' in header_map['episode'].field_format:
                    series = re.search(r'Ep\. [0-9]+', row[header_map['episode'].position].value.strip())

                    if series is not None:
                        episode = int(series.group(0)[4:])

                if season == 0:
                    season = None

            # Determine whether it is a movie
            is_movie = season is None or episode is None

            # Make sure the season and episode are None for movies
            if is_movie:
                season = None
                episode = None

            # Take care of the localized episode synopsis
            if 'localized_episode_synopsis' in header_map:
                if is_movie:
                    synopsis = str(row[header_map['localized_episode_synopsis'].position].value).strip()
                else:
                    synopsis = None

            # Genre is movie, series, documentary, news...
            genre = 'Movie' if is_movie else 'Series'

            # Process the titles
            if original_title is not None:
                original_title = GenericListSpreadsheetParser.process_title(original_title,
                                                                            header_map['original_title'].field_format,
                                                                            is_movie)

            localized_title = GenericListSpreadsheetParser.process_title(localized_title,
                                                                         header_map['localized_title'].field_format,
                                                                         is_movie)

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title, is_movie, genre, date_time, channel_id,
                                                                year, directors, subgenre, synopsis, season, episode,
                                                                cast=cast, duration=duration, countries=countries,
                                                                age_classification=age_classification,
                                                                creators=creators,
                                                                session_audio_language=session_audio_language)

            if insertion_result is None:
                return None

        # Assess the final result
        if insertion_result.total_nb_sessions_in_file != 0:
            db_calls.commit(db_session)

            # Delete old sessions for the same time period
            file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
            file_end_datetime = date_time + datetime.timedelta(minutes=5)

            nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                    [channel_name])

            # Set the remaining information
            insertion_result.nb_deleted_sessions = nb_deleted_sessions
            insertion_result.start_datetime = file_start_datetime
            insertion_result.end_datetime = file_end_datetime

            return insertion_result
        else:
            return None
