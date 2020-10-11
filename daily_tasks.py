import datetime

import configuration
import get_data
import processing


def daily_tasks(session):
    """
    Run the daily tasks.

    :param session: the db session.
    """

    # Delete old shows from the DB
    processing.clear_show_list(session)

    # Update the list of channels
    get_data.update_channel_list(session)

    # Get the date of the last update
    last_update_date = processing.get_last_update(session)

    # Update the list of shows in the DB
    if get_data.configuration.selected_epg == 'MEPG':
        get_data.MEPG.update_show_list(session)

    # Search the shows for the existing reminders
    # The date needs to be the day after because it is at 00:00
    processing.process_reminders(session, last_update_date + datetime.timedelta(days=1))


if __name__ == '__main__':
    session = configuration.Session()

    try:
        daily_tasks(session)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
