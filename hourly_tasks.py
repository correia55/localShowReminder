import configuration
import processing


def daily_tasks(session):
    """
    Run the hourly tasks.

    :param session: the db session.
    """

    processing.process_alarms(session)


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
