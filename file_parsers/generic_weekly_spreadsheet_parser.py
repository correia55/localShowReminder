import csv
import datetime
import os
import re
from typing import Optional, Dict, List

import openpyxl
import sqlalchemy.orm
import xlrd as xlrd

import auxiliary
import configuration
import db_calls
import get_file_data


class GenericField:
    field_name: str
    field_format: str

    def __init__(self, field_name: str, field_format: str):
        self.field_name = field_name
        self.field_format = field_format


class Header:
    position: int
    field_format: str

    def __init__(self, position: int, field_format: str):
        self.position = position
        self.field_format = field_format


class FileSession:
    date_time: datetime.datetime or None
    name: str or None
    translation: str or None
    episode: int or None
    localized_episode_title: str or None

    def __init__(self, date_time: datetime.datetime):
        self.date_time = date_time
        self.name = None
        self.translation = None
        self.episode = None
        self.localized_episode_title = None

    def add_info(self, config_fields: Dict[str, GenericField], book: xlrd.Book, cell, cell_value):
        """
        Add the value in the cell, in the correct field.

        :param config_fields: the configuration dict.
        :param book: the book.
        :param cell: the cell.
        :param cell_value: the value in the cell.
        """

        if cell_value is None:
            return

        if '_translation' in config_fields and config_fields['_translation'].field_format == 'italic':
            italic_translation = True
        else:
            italic_translation = False

        # If it is italic
        if italic_translation and book.font_list[book.xf_list[cell.xf_index].font_index].italic != 0:
            self.translation = cell_value
        # If it is bold
        elif book.font_list[book.xf_list[cell.xf_index].font_index].weight == 700:
            series = re.search(r'^(.*) - Ep\. ([0-9]+).*$', cell_value)

            if series is not None:
                self.name = series.group(1)
                self.episode = int(series.group(2))
            else:
                if self.name is None:
                    self.name = cell_value
                else:
                    self.name = self.name + ' ' + cell_value
        else:
            series = re.search(r'^.*Ep\. ([0-9]+).*$', cell_value)

            if series is not None:
                self.episode = int(series.group(1))
            else:
                self.localized_episode_title = cell_value


class GenericWeeklySpreadsheetParser(get_file_data.ChannelParser):
    channels_file = {'SIC': ('SIC', 'sic.csv')}
    channels = list(channels_file.keys())

    @staticmethod
    def process_configuration(channel_name: str) -> (Dict[str, GenericField], Dict[str, GenericField]):
        """
        Process the configurations file corresponding to the channel name in parameter.

        :param channel_name: the name of the channel in parameter.
        :return: a dictionary with the fields of interest, or None if invalid.
        """

        file_name = GenericWeeklySpreadsheetParser.channels_file[channel_name][1]

        fields = dict()
        config = dict()

        with open(os.path.join(configuration.base_dir, 'file_parsers/channel_config', file_name)) as csvfile:
            content = csv.reader(csvfile, delimiter=';')

            # Skip the headers
            next(content, None)

            for row in content:

                if row[0].startswith('_'):
                    config[row[0]] = GenericField(row[1], row[2])
                else:
                    fields[row[1].lower()] = GenericField(row[0], row[2])

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
    def parse_time(time_value, time_format: str, file_format: str, book: xlrd.book.Book) -> Optional[datetime.time]:
        """
        Parse the time.

        :param time_value: the time as is in the file.
        :param time_format: the format of the time, as in the configuration file.
        :param file_format: the format of the file.
        :param book: the book, of the file (when it is a xls file).
        :return: the parsed time.
        """

        try:
            if file_format == 'xls':
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
        :param book: the book, of the file (when it is a xls file).
        :return: the parsed date.
        """

        if file_format == 'xls':
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
    def process_session(db_session: sqlalchemy.orm.Session, insertion_result: get_file_data.InsertionResult,
                        channel_id: int, file_session: FileSession):
        """
        Process a session, inserting it into the DB.

        :param db_session: the DB session.
        :param insertion_result: the insertion result.
        :param channel_id: the id of the channel.
        :param file_session: the session information.
        :return: the insertion result.
        """

        if file_session.name is None:
            return

        # Get the original title
        if file_session.translation is not None:
            original_title = file_session.translation
        else:
            original_title = file_session.name

        # The remaining information
        localized_title = file_session.name
        is_movie = file_session.episode is None
        season = 1 if file_session.episode is not None else None
        genre = 'Movie' if is_movie else 'Series'

        # Process file entry
        insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                            localized_title, is_movie, genre, file_session.date_time,
                                                            channel_id, None, None, None, None, season,
                                                            file_session.episode)

        if insertion_result is None:
            return None

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
        data_fields: Dict[str, GenericField]
        config_fields: Dict[str, GenericField]

        data_fields, config_fields = GenericWeeklySpreadsheetParser.process_configuration(channel_name)
        channel_name = GenericWeeklySpreadsheetParser.channels_file[channel_name][0]

        # If it is invalid
        if data_fields is None or config_fields is None:
            return None

        # Get the extension of the file
        file_format = filename.split('.')[-1]

        if file_format != 'xls' and file_format != 'xlsx':
            print('Invalid file format!')
            return None

        # Get the channel id from the DB
        channel_id = db_calls.get_channel_name(db_session, channel_name).id

        min_num_fields: int = int(config_fields['_min_num_fields'].field_format)

        if file_format == 'xls':
            book = xlrd.open_workbook(filename, on_demand=True, formatting_info=True)
            sheet = book.sheet_by_index(0)
            rows = sheet.nrows
        else:
            # Remark: setting the read_only to true, changes the number of rows
            book = openpyxl.load_workbook(filename, data_only=True)
            sheet = book.active
            rows = sheet.max_row

        insertion_result = get_file_data.InsertionResult()

        first_event_datetime = None
        date_time = None

        got_headers = False
        headers: List[(str, int)]
        header_map: Dict[str, Header] = dict()

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = int(today_00_00.isocalendar()[1])

        bottom_border_style = 0

        file_session_day = {}

        # Get the strings to ignore
        if '_strings_to_ignore' in config_fields:
            strings_to_ignore = config_fields['_strings_to_ignore'].field_format.split(',')
        else:
            strings_to_ignore = []

        for rx in range(rows):
            if file_format == 'xls':
                row = sheet.row(rx)
            else:
                row = sheet[rx + 1]

            # If we haven't found the header row
            if not got_headers:
                headers = []

                # Build the headers dict
                for i in range(len(row)):
                    cell_value = str(row[i].value).lower().strip()

                    if cell_value and cell_value is not None and cell_value != 'none':
                        headers.append((cell_value, i))

                # If this is the header row
                if len(headers) >= min_num_fields:
                    # Find the correspondence between the fields in the conf and the headers
                    for h in headers:
                        name, pos = h

                        # Assumes the time is the first header
                        if len(header_map) == 0:
                            header_map['time'] = Header(pos, data_fields['time'].field_format)
                            header_map['week'] = Header(pos, name)
                        else:

                            if name not in data_fields:
                                print('Unexpected "%s" field found!' % name)
                            else:
                                header_map[data_fields[name].field_name] = Header(pos, data_fields[name].field_format)

                                # Remove the field from the dict
                                data_fields.pop(name)

                    if len(data_fields) > 0:
                        for f in data_fields.values():
                            if f.field_name not in header_map:
                                print('Expected "%s" field not found!' % f.field_name)

                    # Add fallback fields
                    if 'localized_title' not in header_map and 'original_title' in header_map:
                        print('%s does not have a definition for \'localized_title\'!\nThe \'original_title\' will '
                              'be used.' % channel_name)
                        header_map['localized_title'] = header_map['original_title']

                    if 'localized_synopsis' not in header_map and 'synopsis_english' in header_map:
                        print('%s does not have a definition for \'localized_synopsis\'!\nThe \'synopsis_english\' '
                              'will be used.' % channel_name)
                        header_map['localized_synopsis'] = header_map['synopsis_english']

                    if 'subgenre' not in header_map and 'subgenre_english' in header_map:
                        print('%s does not have a definition for \'subgenre\'!\nThe \'subgenre_english\' will '
                              'be used.' % channel_name)
                        header_map['subgenre'] = header_map['subgenre_english']

                    for h in header_map.keys():
                        file_session_day[h] = FileSession(None)

                    # Get the week of the data
                    data_week = int(float(header_map['week'].field_format))

                    # Get the year of the data
                    if data_week > current_week + 10:
                        year = today_00_00.year - 1
                    else:
                        year = today_00_00.year

                    got_headers = True

                continue

            # -- Process the data of the row --
            # ---------------------------------
            if row[header_map['time'].position].value is not None and row[header_map['time'].position].value:
                # Parse time
                time = GenericWeeklySpreadsheetParser.parse_time(row[header_map['time'].position].value,
                                                                 header_map['time'].field_format, file_format, book)
            else:
                time = None

            # If the time does not exist, then it isn't a data row
            if time is None:
                continue

            for h_name in header_map:
                h_value = header_map[h_name]

                if h_name == 'time' or h_name == 'week':
                    continue

                # Get the correct index according to the day
                index = -1

                if h_name == 'monday':
                    index = 1
                elif h_name == 'tuesday':
                    index = 2
                elif h_name == 'wednesday':
                    index = 3
                elif h_name == 'thursday':
                    index = 4
                elif h_name == 'friday':
                    index = 5
                elif h_name == 'saturday':
                    index = 6
                elif h_name == 'sunday':
                    index = 7

                # Get the date
                date = datetime.date.fromisocalendar(year, data_week, index)

                # Combine the date with the time
                date_time = time.replace(day=date.day, month=date.month, year=date.year)

                # Get the first event's datetime
                if first_event_datetime is None:
                    first_event_datetime = date_time

                # Get the cell
                cell = row[h_value.position]

                # Get the value, or ignore if invalid
                if cell.value is not None and cell.value and cell.value not in strings_to_ignore:
                    cell_value = cell.value
                else:
                    cell_value = None

                # If the previous cell already had a bottom border
                if bottom_border_style == 0:
                    top_border_style = book.xf_list[cell.xf_index].border.top_line_style
                else:
                    top_border_style = 0

                bottom_border_style = book.xf_list[cell.xf_index].border.bottom_line_style

                # Set the date time if it is still missing
                if file_session_day[h_name].date_time is None:
                    file_session_day[h_name].date_time = date_time

                if bottom_border_style != 0:
                    file_session_day[h_name].add_info(config_fields, book, cell, cell_value)

                    GenericWeeklySpreadsheetParser.process_session(db_session, insertion_result, channel_id,
                                                                   file_session_day[h_name])

                    file_session_day[h_name] = FileSession(None)
                elif top_border_style != 0:
                    GenericWeeklySpreadsheetParser.process_session(db_session, insertion_result, channel_id,
                                                                   file_session_day[h_name])

                    file_session_day[h_name] = FileSession(date_time)
                    file_session_day[h_name].add_info(config_fields, book, cell, cell_value)
                else:
                    file_session_day[h_name].add_info(config_fields, book, cell, cell_value)

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
