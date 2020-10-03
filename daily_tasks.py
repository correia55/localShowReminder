import datetime

import get_data
import processing


def daily_tasks():
    """Run the daily tasks."""

    # Delete old shows from the DB
    processing.clear_show_list()

    # Get the date of the last update
    last_update_date = processing.get_last_update()

    # Update the list of shows in the DB
    if get_data.configuration.selected_epg == 'MEPG':
        get_data.MEPG.update_show_list()

    # Search the shows for the existing reminders
    # The date needs to be the day after because it is at 00:00
    processing.process_reminders(last_update_date + datetime.timedelta(days=1))


if __name__ == '__main__':
    daily_tasks()
