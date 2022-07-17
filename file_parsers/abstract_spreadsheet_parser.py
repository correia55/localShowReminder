import datetime
from typing import Dict, Tuple, Optional

import xlrd

from file_parsers.abstract_channel_file_parser import AbstractChannelFileParser, GenericField


class Header:
    position: int
    field_format: str or None

    def __init__(self, position: int, field_format: str or None):
        self.position = position
        self.field_format = field_format


class AbstractSpreadsheetParser(AbstractChannelFileParser):
    channels_file: Dict[str, Tuple[str, str]]

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
    def parse_headers_row(config_fields: Dict[str, GenericField], data_fields: Dict[str, GenericField],
                          channel_name: str, row) -> (bool, Dict[str, Header]):
        """
        Check if a row is the headers' row and parse it.

        :param config_fields: the configuration fields.
        :param data_fields: the data fields.
        :param channel_name: the name of the channel.
        :param row: the row of data.
        :return: a tuple with the success, and the map of headers.
        """

        # Get the minimum number of fields from the conf
        min_num_fields: int = int(config_fields['_min_num_fields'].field_format)

        headers = []

        # Build the headers dict
        for i in range(len(row)):
            cell_value = str(row[i].value).lower().strip()

            if cell_value and cell_value is not None and cell_value != 'none':
                headers.append((cell_value, i))

        # If this is not the header row
        if len(headers) < min_num_fields:
            return False, None

        headers_map: Dict[str, Header] = dict()

        # Find the correspondence between the fields in the conf and the headers
        unknown_counter = 0

        for h in headers:
            name, pos = h

            if name not in data_fields:
                print('Unexpected "%s" field found!' % name)

                headers_map['Unknown %d' % unknown_counter] = Header(pos, name)
                unknown_counter += 1
            else:
                headers_map[data_fields[name].field_name] = Header(pos, data_fields[name].field_format)

                # Remove the field from the dict
                data_fields.pop(name)

        if len(data_fields) > 0:
            for f in data_fields.values():
                if f.field_name not in headers_map:
                    print('Expected "%s" field not found!' % f.field_name)

        # Add fallback fields
        if 'localized_title' not in headers_map and 'original_title' in headers_map:
            print('%s does not have a definition for \'localized_title\'!\nThe \'original_title\' will '
                  'be used.' % channel_name)
            headers_map['localized_title'] = headers_map['original_title']

        if 'localized_synopsis' not in headers_map and 'synopsis_english' in headers_map:
            print('%s does not have a definition for \'localized_synopsis\'!\nThe \'synopsis_english\' '
                  'will be used.' % channel_name)
            headers_map['localized_synopsis'] = headers_map['synopsis_english']

        if 'subgenre' not in headers_map and 'subgenre_english' in headers_map:
            print('%s does not have a definition for \'subgenre\'!\nThe \'subgenre_english\' will '
                  'be used.' % channel_name)
            headers_map['subgenre'] = headers_map['subgenre_english']

        return True, headers_map
