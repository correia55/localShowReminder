import os
from enum import Enum
from typing import Any

import alembic.autogenerate as aleauto
import alembic.command as alecomm
import alembic.config as aleconf
import alembic.migration as alemig
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import models


class AvailableLanguage(Enum):
    PT = 'pt'
    EN = 'en'


base_dir: str

database_url: str
Session: Any

selected_epg: str
channels_url: str
shows_url: str
max_channels_request: int
show_sessions_validity_days: int

same_session_minutes: int

tmdb_max_mb_pages: int
omdb_key: str
tmdb_key: str
trakt_key: str
cache_validity_days: int

bcrypt_rounds: int
secret_key: Any
VERIFICATION_TOKEN_VALIDITY_DAYS: int
DELETION_TOKEN_VALIDITY_DAYS: int
CHANGE_EMAIL_TOKEN_VALIDITY_DAYS: int
PASSWORD_RECOVERY_TOKEN_VALIDITY_DAYS: int
REFRESH_TOKEN_VALIDITY_DAYS: int
ACCESS_TOKEN_VALIDITY_HOURS: int

google_client_id: Any

email_domain: str
email_account: str
email_user: str
email_password: str

application_name: str
application_link: str
AVAILABLE_LANGUAGES: Any

score_highlight_counter = int
new_highlight_counter = int


def initialize():
    """ Initialize this module, preparing all of the variables. """

    # region General
    global base_dir

    base_dir = os.environ.get('BASE_DIR', None)

    # endregion

    # region Database
    global database_url, Session

    # Get the database url saved in the environment variable
    database_url = os.environ.get('DATABASE_URL', None)

    if database_url is None:
        print('Warning: Unable to find database url!')
        exit(1)

    engine = create_engine(database_url, encoding='utf-8', pool_recycle=280)
    Session = sessionmaker(bind=engine)

    MIGRATIONS_DIR = os.path.join(base_dir, 'migrations')

    config = aleconf.Config(file_=os.path.join(MIGRATIONS_DIR, 'alembic.ini'))
    config.set_main_option('script_location', MIGRATIONS_DIR)
    config.set_main_option('sqlalchemy.url', database_url)

    # Create tables if they don't exist
    if not os.path.isdir(MIGRATIONS_DIR):
        alecomm.init(config, MIGRATIONS_DIR)

        env_file = open('%s/env.py' % MIGRATIONS_DIR, 'r+')
        text = env_file.read()
        text = text.replace('target_metadata=target_metadata', 'target_metadata=target_metadata, compare_type=True')
        text = text.replace('target_metadata = None', 'import models\ntarget_metadata = models.Base.metadata')
        env_file.seek(0)
        env_file.write(text)
        env_file.close()

    # Makes sure the database is up to date
    alecomm.upgrade(config, 'head')

    # Check for changes in the database
    mc = alemig.MigrationContext.configure(engine.connect())
    diff_list = aleauto.compare_metadata(mc, models.Base.metadata)

    # Update the database
    if diff_list:
        alecomm.revision(config, None, autogenerate=True)
        alecomm.upgrade(config, 'head')

    # endregion

    # region Data Gathering
    global selected_epg, channels_url, shows_url, max_channels_request, show_sessions_validity_days

    # Get the selected EPG
    selected_epg = os.environ.get('EPG', None)

    # Get urls for the selected EPG
    channels_url = os.environ.get('CHANNELS_URL', None)
    shows_url = os.environ.get('SHOWS_URL', None)

    # Max channels per request
    max_channels_request = os.environ.get('MAX_CHANNELS_REQUEST', '90')

    # Number of days after the date in which the sessions are still kept
    show_sessions_validity_days = os.environ.get('SHOW_SESSIONS_VALIDITY_DAYS', 7)

    # endregion

    # region Data Gathering from file
    global same_session_minutes

    # Get the number of minutes to be used for searching for changes in a session
    same_session_minutes = os.environ.get('SAME_SESSION_MINUTES', None)

    if same_session_minutes is None:
        same_session_minutes = 30
    else:
        same_session_minutes = int(same_session_minutes)

    # endregion

    # region Shows Information Services
    global trakt_key, cache_validity_days, omdb_key, tmdb_key, tmdb_max_mb_pages

    # Get the api key for trakt
    trakt_key = os.environ.get('TRAKT_KEY', None)

    if trakt_key is None:
        print('Warning: Unable to find trakt key!')

    # Cache validity, in days
    cache_validity_days = os.environ.get('CACHE_VALIDITY', None)

    if cache_validity_days is None:
        print('Warning: Unable to find CACHE_VALIDITY key!')

        # Set 1 days as the default value
        cache_validity_days = 1

    # Get the api key for omdb
    omdb_key = os.environ.get('OMDB_KEY', None)

    if omdb_key is None:
        print('Warning: Unable to find omdb key!')

    # Get the api key for omdb
    tmdb_key = os.environ.get('TMDB_KEY', None)

    if tmdb_key is None:
        print('Warning: Unable to find tmdb key!')
        exit(1)

    # Get the number of pages that should be retrieved from TMDB
    tmdb_max_mb_pages = os.environ.get('TMDB_MAX_NB_PAGES', None)

    if tmdb_max_mb_pages is None:
        print('Warning: Unable to find tmdb max number of pages!')

        # Set 2 pages as the default value
        tmdb_max_mb_pages = 2

    # endregion

    # region Information Security
    global bcrypt_rounds, secret_key, REFRESH_TOKEN_VALIDITY_DAYS, ACCESS_TOKEN_VALIDITY_HOURS, \
        VERIFICATION_TOKEN_VALIDITY_DAYS, DELETION_TOKEN_VALIDITY_DAYS, CHANGE_EMAIL_TOKEN_VALIDITY_DAYS, \
        PASSWORD_RECOVERY_TOKEN_VALIDITY_DAYS

    # Get the configuration for the number of rounds used in the bcrypt
    bcrypt_rounds = os.environ.get('BCRYPT_ROUNDS', None)

    if bcrypt_rounds is None:
        bcrypt_rounds = 10

    # Get the secret key used to generate tokens
    secret_key = os.environ.get('SECRET_KEY', None)

    if secret_key is None:
        print('Warning: Unable to find secret key!')
        exit(1)

    # Validity of the different types of token
    REFRESH_TOKEN_VALIDITY_DAYS = 365
    ACCESS_TOKEN_VALIDITY_HOURS = 1
    VERIFICATION_TOKEN_VALIDITY_DAYS = 2
    DELETION_TOKEN_VALIDITY_DAYS = 2
    CHANGE_EMAIL_TOKEN_VALIDITY_DAYS = 2
    PASSWORD_RECOVERY_TOKEN_VALIDITY_DAYS = 2

    # endregion

    # region External Login

    # Get the client id for Google
    global google_client_id

    google_client_id = os.environ.get('GOOGLE_CLIENT_ID', None)

    if google_client_id is None:
        print('Warning: Unable to find google client id!')
        exit(1)

    # endregion

    # region Email
    global email_domain, email_account, email_user, email_password

    email_domain = os.environ.get('EMAIL_DOMAIN', None)
    email_account = os.environ.get('EMAIL_ACCOUNT', None)
    email_user = os.environ.get('EMAIL_USER', None)
    email_password = os.environ.get('EMAIL_PASSWORD', None)

    # endregion

    # region Highlights
    global score_highlight_counter, new_highlight_counter

    score_highlight_counter = os.environ.get('SCORE_HIGHLIGHT_COUNTER', None)

    if score_highlight_counter is None:
        score_highlight_counter = 5

    new_highlight_counter = os.environ.get('NEW_HIGHLIGHT_COUNTER', None)

    if new_highlight_counter is None:
        new_highlight_counter = 50

    # endregion

    # region Application
    global application_name, application_link, AVAILABLE_LANGUAGES

    application_name = os.environ.get('APPLICATION_NAME', None)
    application_link = os.environ.get('APPLICATION_LINK', None)

    AVAILABLE_LANGUAGES = [item.value for item in AvailableLanguage]

    # endregion
