import datetime
import re
from typing import Optional, Dict

import openpyxl
import sqlalchemy.orm
import xlrd as xlrd

import auxiliary
import db_calls
import get_file_data
from file_parsers.abstract_channel_file_parser import InsertionResult, GenericField
from abstract_spreadsheet_parser import AbstractSpreadsheetParser, Header


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


class GenericWeeklySpreadsheetParser(AbstractSpreadsheetParser):
    channels_file = {'SIC': ('SIC', 'sic.csv')}
    channels = list(channels_file.keys())

    @staticmethod
    def parse_headers_row(config_fields: Dict[str, GenericField], data_fields: Dict[str, GenericField],
                          channel_name: str, row) -> (bool, Dict[str, Header]):

        got_headers, headers_map = AbstractSpreadsheetParser.parse_headers_row(config_fields, data_fields,
                                                                               channel_name, row)

        # If something failed, just return it
        if not got_headers:
            return got_headers, headers_map

        # Add the time header
        header = headers_map['Unknown %d' % int(config_fields['_time_pos'].field_format)]

        headers_map['time'] = Header(header.position, config_fields['_time_format'].field_format)

        # Add the week header
        if '_week_from_header' in config_fields:
            header = headers_map['Unknown %d' % int(config_fields['_week_from_header'].field_format)]

            headers_map['week'] = Header(header.position, header.field_format)

        return True, headers_map

    @staticmethod
    def process_session(db_session: sqlalchemy.orm.Session, insertion_result: InsertionResult,
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
            -> Optional[InsertionResult]:
        """
        Add the config, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :param channel_name: the name of the channel.
        :return: the InsertionResult.
        """

        # Channel information
        channel_info = GenericWeeklySpreadsheetParser.channels_file[channel_name]

        channel_name = channel_info[0]
        channel_file = channel_info[1]

        # Get the position and format of the fields for this channel
        data_fields: Dict[str, GenericField]
        config_fields: Dict[str, GenericField]

        data_fields, config_fields = GenericWeeklySpreadsheetParser.process_configuration(channel_file)

        # If it is invalid
        if data_fields is None or config_fields is None:
            return None

        # _time_pos is a mandatory field in the conf
        if '_time_pos' not in config_fields or '_time_format' not in config_fields:
            return None

        # Get the extension of the file
        file_format = filename.split('.')[-1]

        if file_format != 'xls':
            print('Invalid file format: %s!' % file_format)
            return None

        # Prepare for reading, according to the file extension
        if file_format == 'xls':
            book = xlrd.open_workbook(filename, on_demand=True, formatting_info=True)
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

        got_headers = False
        headers_map: Dict[str, Header] = dict()

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        current_week = int(today_00_00.isocalendar()[1])

        bottom_border_style = 0

        # Get the strings to ignore
        if '_strings_to_ignore' in config_fields:
            strings_to_ignore = config_fields['_strings_to_ignore'].field_format.split(',')
        else:
            strings_to_ignore = []

        # Initialize the file sessions for each day
        file_session_weekday = {'monday': FileSession(None), 'tuesday': FileSession(None),
                                'wednesday': FileSession(None), 'thursday': FileSession(None),
                                'friday': FileSession(None), 'saturday': FileSession(None), 'sunday': FileSession(None)}

        date_weekday = {}

        # Iterating over the rows of the file
        for rx in range(rows):
            if file_format == 'xls':
                row = sheet.row(rx)
            else:
                row = sheet[rx + 1]

            # If we haven't found the header row
            if not got_headers:
                got_headers, headers_map = GenericWeeklySpreadsheetParser.parse_headers_row(config_fields, data_fields,
                                                                                            channel_name, row)

                # If the week comes from the headers
                if got_headers and 'week' in headers_map:
                    # Get the week of the data
                    data_week = int(float(headers_map['week'].field_format))

                    # Get the year of the data
                    if data_week > current_week + 10:
                        year = today_00_00.year - 1
                    else:
                        year = today_00_00.year

                continue

            # -- Process the data of the row --
            # ---------------------------------
            if row[headers_map['time'].position].value is not None and row[headers_map['time'].position].value:
                # Parse time
                time = GenericWeeklySpreadsheetParser.parse_time(row[headers_map['time'].position].value,
                                                                 headers_map['time'].field_format, file_format, book)
            else:
                time = None

            # If the time does not exist, then it isn't a data row
            if time is None:
                continue

            # Process each weekday's column
            for h_name in headers_map:
                if 'week' in headers_map and h_name not in date_weekday:
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

                    if index == -1:
                        continue

                    # Get the date
                    date_weekday[h_name] = datetime.date.fromisocalendar(year, data_week, index)

                # Combine the date with the time
                date = date_weekday[h_name]
                date_time = time.replace(day=date.day, month=date.month, year=date.year)

                # Get the first event's datetime
                if first_event_datetime is None:
                    first_event_datetime = date_time

                # Get the cell
                cell = row[headers_map[h_name].position]

                # Get the value, or ignore it if invalid
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
                if file_session_weekday[h_name].date_time is None:
                    file_session_weekday[h_name].date_time = date_time

                # Add the new info to the session
                if bottom_border_style != 0:
                    file_session_weekday[h_name].add_info(config_fields, book, cell, cell_value)

                    GenericWeeklySpreadsheetParser.process_session(db_session, insertion_result, channel_id,
                                                                   file_session_weekday[h_name])

                    file_session_weekday[h_name] = FileSession(None)
                elif top_border_style != 0:
                    GenericWeeklySpreadsheetParser.process_session(db_session, insertion_result, channel_id,
                                                                   file_session_weekday[h_name])

                    file_session_weekday[h_name] = FileSession(date_time)
                    file_session_weekday[h_name].add_info(config_fields, book, cell, cell_value)
                else:
                    file_session_weekday[h_name].add_info(config_fields, book, cell, cell_value)

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
