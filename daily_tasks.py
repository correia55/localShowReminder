import sqlalchemy.orm

import configuration
import db_calls
import get_webservice_data
import processing


def daily_tasks(db_session: sqlalchemy.orm.Session):
    """
    Run the daily tasks.

    :param db_session: the db session.
    """

    # Delete old shows from the DB
    processing.clear_show_list(db_session)
    print('Shows list cleared!')

    # Delete invalid cache
    db_calls.clear_cache(db_session)
    print('Cache cleared!')

    # Update the list of channels
    get_webservice_data.update_channel_list(db_session)

    # Update the list of shows in the DB
    if get_webservice_data.configuration.selected_epg == 'MEPG':
        get_webservice_data.MEPG.update_show_list(db_session)

    print('Shows list updated!')

    # Search the shows for the existing alarms
    # The date needs to be the day after because it is at 00:00
    processing.process_alarms(db_session)
    print('Alarms processed!')


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
