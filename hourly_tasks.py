import sqlalchemy.orm

import configuration
import process_emails
import reminders


def hourly_tasks(db_session: sqlalchemy.orm.Session):
    """
    Run the hourly tasks.

    :param db_session: the db session.
    """

    reminders.process_reminders(db_session)
    print('Reminders processed!')


if __name__ == '__main__':
    configuration.initialize()
    process_emails.initialize()

    session = configuration.Session()

    try:
        hourly_tasks(session)
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()
