import datetime
import re
import xml.dom.minidom
from typing import Optional

import sqlalchemy.orm

import auxiliary
import configuration
import db_calls
import get_file_data


class Odisseia(get_file_data.ChannelInsertion):
    channels = ['Odisseia']

    @staticmethod
    def process_title(title: str) -> str:
        """ Process the title, removing special markers and reformatting the title. """

        # Replace all quotation marks for the same quotation mark
        return re.sub('[´`]', '\'', title)

    @staticmethod
    def add_file_data(db_session: sqlalchemy.orm.Session, filename: str) -> Optional[get_file_data.InsertionResult]:
        """
        Add the data, in the file, to the DB.

        :param db_session: the DB session.
        :param filename: the path to the file.
        :return: the InsertionResult.
        """

        dom_tree = xml.dom.minidom.parse(filename)
        collection = dom_tree.documentElement

        # Get all events
        events = collection.getElementsByTagName('Event')

        # If there are no events
        if len(events) == 0:
            return None

        first_event_datetime = None
        date_time = None

        insertion_result = get_file_data.InsertionResult()

        today_00_00 = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        # Process each event
        for event in events:
            # --- START DATA GATHERING ---
            # Get the date and time
            begin_time = event.getAttribute('beginTime')
            date_time = datetime.datetime.strptime(begin_time, '%Y%m%d%H%M%S')

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

            # Get the event's duration in minutes
            duration = int(int(event.getAttribute('duration')) / 60)

            # Inside the Event -> EpgProduction
            epg_production = event.getElementsByTagName('EpgProduction')[0]

            # Get the genre
            genre_list = epg_production.getElementsByTagName('Genere')

            # Check if it is the genre that we are assuming it always is
            if len(genre_list) > 0 and 'Document' not in genre_list[0].firstChild.nodeValue:
                get_file_data.print_message('not a documentary', True, str(event.getAttribute('beginTime')))

            # Subgenre is in portuguese
            subgenre = epg_production.getElementsByTagName('Subgenere')[0].firstChild.nodeValue

            # Age classification
            age_classification = epg_production.getElementsByTagName('ParentalRating')[0].firstChild.nodeValue

            # Inside the Event -> EpgProduction -> EpgText
            epg_text = epg_production.getElementsByTagName('EpgText')[0]

            # Get the localized title, in this case the portuguese one
            localized_title = epg_text.getElementsByTagName('Name')[0].firstChild.nodeValue

            # Get the localized synopsis, in this case the portuguese one
            short_description = epg_text.getElementsByTagName('ShortDescription')

            if short_description is not None and short_description[0].firstChild is not None:
                synopsis = short_description[0].firstChild.nodeValue
            else:
                synopsis = None

            # Iterate over the ExtendedInfo elements
            extended_info_elements = epg_text.getElementsByTagName('ExtendedInfo')

            original_title = None
            directors = None
            season = None
            episode = None
            year = None
            countries = None
            cast = None

            for extended_info in extended_info_elements:
                attribute = extended_info.getAttribute('name')

                if attribute == 'OriginalEventName' and extended_info.firstChild is not None:
                    original_title = extended_info.firstChild.nodeValue
                elif attribute == 'Year' and extended_info.firstChild is not None:
                    year = int(extended_info.firstChild.nodeValue)

                    # Sometimes the year is 0
                    if year == 0:
                        year = None
                elif attribute == 'Director' and extended_info.firstChild is not None:
                    directors = extended_info.firstChild.nodeValue
                elif attribute == 'Casting' and extended_info.firstChild is not None:
                    cast = extended_info.firstChild.nodeValue
                elif attribute == 'Nationality' and extended_info.firstChild is not None:
                    countries = extended_info.firstChild.nodeValue
                elif attribute == 'Cycle' and extended_info.firstChild is not None:
                    season = int(extended_info.firstChild.nodeValue)
                elif attribute == 'EpisodeNumber' and extended_info.firstChild is not None:
                    episode = int(extended_info.firstChild.nodeValue)

            # Get the channel's id
            channel_id = db_calls.get_channel_name(db_session, 'Odisseia').id

            # Process titles
            original_title = Odisseia.process_title(original_title)
            localized_title = Odisseia.process_title(localized_title)

            # Process the directors
            if directors is not None:
                directors = directors.split(',')

            is_movie = season is None
            genre = 'Documentary'

            # --- END DATA GATHERING ---

            # Process file entry
            insertion_result = get_file_data.process_file_entry(db_session, insertion_result, original_title,
                                                                localized_title,
                                                                is_movie, genre, date_time, channel_id, year, directors,
                                                                subgenre,
                                                                synopsis, season, episode, cast=cast, duration=duration,
                                                                countries=countries,
                                                                age_classification=age_classification)

            if insertion_result is None:
                return None

        # If there only invalid sessions
        if first_event_datetime is None:
            return None

        db_calls.commit(db_session)

        # Delete old sessions for the same time period
        file_start_datetime = first_event_datetime - datetime.timedelta(minutes=5)
        file_end_datetime = date_time + datetime.timedelta(minutes=5)

        nb_deleted_sessions = get_file_data.delete_old_sessions(db_session, file_start_datetime, file_end_datetime,
                                                                Odisseia.channels)

        # Set the remaining information
        insertion_result.nb_deleted_sessions = nb_deleted_sessions
        insertion_result.start_datetime = file_start_datetime
        insertion_result.end_datetime = file_end_datetime

        return insertion_result
