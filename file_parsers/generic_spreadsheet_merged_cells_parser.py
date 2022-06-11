import csv
import datetime
import os
import re
from typing import Optional, Dict, List

import sqlalchemy.orm
import xlrd as xlrd

import auxiliary
import configuration
import db_calls
import get_file_data


class GenericMergedField:
    name: str
    mandatory: bool
    field_format: str
    value: str

    def __init__(self, name: str, mandatory: bool, field_format: str):
        self.name = name
        self.mandatory = mandatory
        self.field_format = field_format


class GenericSpreadsheetMergedCellsParser(get_file_data.ChannelParser):
    channels_file = {'História': ('História', 'historia.csv')}
    channels = list(channels_file.keys())

    @staticmethod
    def process_configuration(channel_name: str) -> (List[GenericMergedField], Dict[str, str]) or None:
        """
        Process the configurations file corresponding to the channel name in parameter.

        :param channel_name: the name of the channel in parameter.
        :return: a dictionary with the fields of interest, or None if invalid.
        """

        file_name = GenericSpreadsheetMergedCellsParser.channels_file[channel_name][1]

        fields:List[GenericMergedField] = list()
        fields_dict:Dict[str, GenericMergedField] = dict()
        config:Dict[str, str] = dict()

        with open(os.path.join(configuration.base_dir, 'file_parsers/channel_config', file_name)) as csvfile:
            content = csv.reader(csvfile, delimiter=';')

            # Skip the headers
            next(content, None)

            num_mandatory = 0

            for row in content:
                # Check if it is a configuration entry
                if row[0].startswith('_'):
                    config[row[0]] = row[2]
                else:
                    # Count the number of mandatory fields
                    mandatory = row[1] == 'True'

                    if mandatory:
                        num_mandatory += 1

                    # Store the field in the list
                    field = GenericMergedField(row[0], mandatory, row[2])

                    fields.append(field)
                    fields_dict[row[0]] = field

            # Store the number of mandatory fields in the config dict
            config['_num_mandatory'] = str(num_mandatory)

        # Check if the essential fields are present
        if 'date' not in fields_dict and 'date_time' not in fields_dict and '_date' not in config:
            print('%s does not have a definition for \'date\' nor \'date_time\'!' % channel_name)
            return None

        if 'time' not in fields_dict and 'date_time' not in fields_dict:
            print('%s does not have a definition for \'time\' nor \'date_time\'!' % channel_name)
            return None

        if 'original_title' not in fields_dict:
            print('%s does not have a definition for \'original_title\'!' % channel_name)

        if 'year' not in fields_dict:
            print('%s does not have a definition for \'year\'!' % channel_name)

        if 'localized_title' not in fields_dict:
            print('%s does not have a definition for \'localized_title\'!' % channel_name)

            if 'original_title' in fields_dict:
                print('The \'original_title\' will be used.')

        if 'localized_synopsis' not in fields_dict:
            print('%s does not have a definition for \'localized_synopsis\'!' % channel_name)

            if 'synopsis_english' in fields_dict:
                print('The \'synopsis_english\' will be used.')

        if 'subgenre' not in fields_dict:
            print('%s does not have a definition for \'subgenre\'!' % channel_name)

            if 'subgenre_english' in fields_dict:
                print('The \'subgenre_english\' will be used.')

        return fields, config

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
                series = re.search(r'S[0-9]+', title.strip())

                if series is not None:
                    title = title[:series.span(0)[0]]
            elif 'season_at_the_end' in title_format:
                series = re.search(r'^(.*) [0-9]+$', title.strip())

                if series is not None:
                    title = series.group(1)
            elif 'season_and_episode_at_the_end' in title_format:
                series = re.search(r'^(.*) T[0-9]+, ?[0-9]+$', title.strip())

                if series is not None:
                    title = series.group(1)

        if 'has_year' in title_format:
            # From the last position of the parenthesis
            search_result = auxiliary.search_chars(title, ['(', ')'])

            for i in range(len(search_result[0]) - 1, -1, -1):
                start_pos = search_result[0][i]
                end_pos = search_result[1][i]

                text = title[start_pos + 1:end_pos]

                # Check if it has a year
                if re.search(r'[0-9]{4}', text.strip()):
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
    def parse_time(time_value, time_format: str, file_format: str, book: xlrd.book.Book) -> Optional[datetime.time]:
        """
        Parse the time.

        :param time_value: the time as is in the file.
        :param time_format: the format of the time, as in the configuration file.
        :param file_format: the format of the file.
        :param book: the book, of the file (when it is a .xls file).
        :return: the parsed time.
        """

        try:
            if file_format == '.xls':
                try:
                    #  If the time comes in the time format
                    time = xlrd.xldate_as_datetime(time_value, book.datemode)
                except TypeError:
                    # If the time comes as text
                    time = datetime.datetime.strptime(time_value, time_format)
            else:
                try:
                    time = datetime.datetime.strptime(time_value, time_format)
                except TypeError:
                    try:
                        #  If the time already comes in the time format
                        time = time_value
                    except TypeError:
                        time = None
        except ValueError:
            time = None

        return time

    @staticmethod
    def parse_date(date_value, date_format: str, file_format: str, book: xlrd.book.Book) -> datetime.date or None:
        """
        Parse the date.

        :param date_value: the date as is in the file.
        :param date_format: the format of the date, as in the configuration file.
        :param file_format: the format of the file.
        :param book: the book, of the file (when it is a .xls file).
        :return: the parsed date.
        """

        if file_format == '.xls':
            try:
                #  If the date comes in the date format
                date = xlrd.xldate_as_datetime(date_value, book.datemode)
            except TypeError:
                date = None
        else:
            date = None

        if date is None:
            try:
                # If the date comes as text
                date = datetime.datetime.strptime(date_value, date_format)
            except (TypeError, ValueError):
                #  If the date already comes in the date format
                if isinstance(date_value, datetime.date):
                    date: datetime.date = date_value

        return date

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str, channel_name: str) \
            -> Optional[get_file_data.InsertionResult]:
        """
        Add the config, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel.
        :return: the InsertionResult.
        """

        # Get the position and format of the fields for this channel
        fields: List[GenericMergedField]
        config: Dict[str, str]

        (fields, config) = GenericSpreadsheetMergedCellsParser.process_configuration(channel_name)
        channel_name = GenericSpreadsheetMergedCellsParser.channels_file[channel_name][0]

        # If it is invalid
        if fields is None:
            return None

        if '_file_format' in config:
            file_format = config['_file_format']
        else:
            file_format = '.xlsx'

        if file_format == '.xls':
            book = xlrd.open_workbook(filename, formatting_info=True)
            sheet = book.sheets()[0]
            rows = sheet.nrows
        else:
            return None

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None
        date = None

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Get the number of mandatory fields
        num_mandatory = int(config['_num_mandatory'])

        # Iterate over the values
        for rx in range(rows):
            row = sheet.row(rx)

            # Used to store all values of a single row
            current_row = []

            for i in range(len(row)):
                cell_str = row[i].value

                # Skip cells without data
                if not cell_str or cell_str is None:
                    continue

                current_row.append(cell_str)

            if len(current_row) == 0:
                continue

            # If the number of elements is less than the mandatory fields, then it isn't a data row
            if len(current_row) < num_mandatory:
                # If the date is in a separate row
                if '_date_separate_line' in config:
                    # If there's a date, update the current date
                    date_value = GenericSpreadsheetMergedCellsParser.process_date(current_row[0],
                                                                                  config[
                                                                                      '_date_separate_line'])

                    # Parse date, and skip the row
                    date = GenericSpreadsheetMergedCellsParser.parse_date(date_value, config['_date'],
                                                                          file_format, book)
                    continue

            # Otherwise, process the row
            # Used to store all values in the row
            cell_dict: Dict[str, GenericMergedField] = dict()

            current_field = 0
            valid_row = True

            for i in range(len(current_row)):
                cell_str = current_row[i]

                found_matching_field = False

                for j in range(current_field, len(fields)):
                    field = fields[j]
                    current_field += 1

                    if field.mandatory:
                        field.value = cell_str
                        cell_dict[field.name] = field

                        found_matching_field = True

                        break

                    else:
                        # If the field is a match to the current cell
                        if re.match(field.field_format, cell_str):
                            field.value = cell_str
                            cell_dict[field.name] = field

                            found_matching_field = True

                            break

                # The row is invalid
                if not found_matching_field:
                    valid_row = False
                    break

            # If it is a valid row, parse the date and add it to the DB
            if valid_row:
                if cell_dict['time'].value is not None and cell_dict['time'].value:
                    # Parse time
                    time = GenericSpreadsheetMergedCellsParser.parse_time(cell_dict['time'].value,
                                                                          cell_dict['time'].field_format,
                                                                          file_format, book)
                else:
                    time = None

                # Get the date_time
                if 'date_time' in cell_dict:
                    date_time = datetime.datetime.strptime(cell_dict['date_time'].value,
                                                           cell_dict['date_time'].field_format)
                else:
                    if time is None:
                        continue

                    if '_date_separate_line' not in config:
                        date = GenericSpreadsheetMergedCellsParser.parse_date(cell_dict['date'].value,
                                                                              cell_dict['date'].field_format,
                                                                              file_format, book)

                    if date is None:
                        continue

                    # Combine the date with the time
                    date_time = date.replace(hour=time.hour, minute=time.minute)

                if 'year' in cell_dict:
                    # Skip the rows in which the year is invalid
                    if cell_dict['year'].value is None:
                        continue

                    try:
                        year = int(cell_dict['year'].value)
                    except ValueError:
                        continue
                else:
                    year = None

                # Add the Lisbon timezone info, then convert it to UTC
                # and then remove the timezone info
                date_time = auxiliary.convert_datetime_to_utc(auxiliary.get_datetime_with_tz_offset(date_time)) \
                    .replace(tzinfo=None)

                # Ignore old sessions
                if date_time < (
                        today_00_00 - datetime.timedelta(days=configuration.show_sessions_validity_days)):
                    continue

                if 'localized_title' in cell_dict:
                    localized_title = str(cell_dict['localized_title'].value)
                else:
                    localized_title = None

                if 'original_title' in cell_dict:
                    original_title = str(cell_dict['original_title'].value)

                    if localized_title is None:
                        localized_title = original_title
                else:
                    original_title = None

                # If it is a placeholder show or temporary program
                if '_temporary_program' in cell_dict:
                    if str(cell_dict['_temporary_program'].field_format) in original_title:
                        continue

                if 'localized_synopsis' in cell_dict:
                    synopsis = str(cell_dict['localized_synopsis'].value).strip()
                else:
                    if 'synopsis_english' in cell_dict:
                        synopsis = str(cell_dict['synopsis_english'].value).strip()
                    else:
                        synopsis = None

                if 'cast' in cell_dict:
                    cast = cell_dict['cast'].value

                    if cast is not None:
                        cast = cast.strip()

                        if len(cast) == 0:
                            cast = None
                else:
                    cast = None

                if 'directors' in cell_dict:
                    directors = cell_dict['directors'].value

                    # Process the directors
                    if directors is not None:
                        if re.match('^ *$', directors):
                            directors = None
                        else:
                            directors = directors.split(',')

                    # If the name of the directors is actually a placeholder
                    if '_ignore_directors' in cell_dict and directors:
                        if directors[0].strip() == cell_dict['_ignore_directors'].field_format:
                            directors = None
                else:
                    directors = None

                if 'creators' in cell_dict:
                    creators = cell_dict['creators'].value

                    # Process the creators
                    if creators is not None:
                        if re.match('^ *$', creators):
                            creators = None
                        else:
                            creators = creators.split(',')
                else:
                    creators = None

                if 'countries' in cell_dict:
                    countries = cell_dict['countries'].value.strip()
                else:
                    countries = None

                # Duration
                if 'duration' in cell_dict:
                    if cell_dict['duration'].field_format == 'seconds':
                        duration = int(int(cell_dict['duration'].value) / 60)
                    else:
                        try:
                            duration = xlrd.xldate_as_datetime(cell_dict['duration'].value, book.datemode)
                        except TypeError:
                            duration = datetime.datetime.strptime(cell_dict['duration'].value,
                                                                  cell_dict['duration'].field_format)

                        duration = duration.hour * 60 + duration.minute
                else:
                    duration = None

                if 'age_classification' in cell_dict:
                    age_classification = str(cell_dict['age_classification'].value).strip()
                else:
                    age_classification = None

                if 'subgenre' in cell_dict:
                    subgenre = cell_dict['subgenre'].value.strip()
                else:
                    if 'subgenre_english' in cell_dict:
                        subgenre = cell_dict['subgenre_english'].value.strip()
                    else:
                        subgenre = None

                # Process the audio language of the session
                session_audio_language = None

                if 'session_audio_language' in cell_dict:
                    session_audio_language = cell_dict['session_audio_language'].value

                    if session_audio_language == 'VP':
                        session_audio_language = 'pt'
                    else:
                        session_audio_language = None

                # Get the first event's datetime
                if first_event_datetime is None:
                    first_event_datetime = date_time

                if 'season' not in cell_dict or 'episode' not in cell_dict:
                    season = None
                    episode = None
                else:
                    try:
                        season = int(cell_dict['season'].value)
                    except ValueError:
                        season = None

                    # Some files use 0 as a placeholder
                    if season == 0:
                        season = None

                    try:
                        episode = int(cell_dict['episode'].value)
                    except ValueError:
                        episode = None

                # Determine whether it is a movie
                is_movie = season is None or episode is None

                # Make sure the season and episode are None for movies
                if is_movie:
                    season = None
                    episode = None

                # Take care of the localized episode synopsis
                if 'localized_episode_synopsis' in cell_dict:
                    if is_movie:
                        synopsis = str(cell_dict['localized_episode_synopsis'].value).strip()
                    else:
                        synopsis = None

                # Genre is movie, series, documentary, news...
                genre = 'Movie' if is_movie else 'Series'

                # Process the titles
                if original_title is not None:
                    original_title = GenericSpreadsheetMergedCellsParser.process_title(original_title,
                                                                                       cell_dict[
                                                                                           'original_title'].field_format,
                                                                                       is_movie)

                localized_title = GenericSpreadsheetMergedCellsParser.process_title(localized_title,
                                                                                    cell_dict[
                                                                                        'localized_title'].field_format,
                                                                                    is_movie)

                channel_id = db_calls.get_channel_name(db_session, channel_name).id

                # Process file entry
                insertion_result = get_file_data.process_file_entry(db_session, insertion_result,
                                                                    original_title,
                                                                    localized_title, is_movie, genre, date_time,
                                                                    channel_id,
                                                                    year, directors, subgenre, synopsis, season,
                                                                    episode,
                                                                    cast=cast, duration=duration,
                                                                    countries=countries,
                                                                    age_classification=age_classification,
                                                                    creators=creators,
                                                                    session_audio_language=session_audio_language)

                if insertion_result is None:
                    return None

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
