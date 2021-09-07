from contextlib import contextmanager
from enum import Enum

import flask
import flask_httpauth as fh
import flask_limiter as fl
import flask_restful as fr
import webargs
import webargs.flaskparser as fp
from flask_cors import CORS

import authentication
import auxiliary
import configuration
import db_calls
import external_authentication
import process_emails
import processing
import reminders
from processing import ChangeType
from response_models import AlarmType


class FlaskApp(flask.Flask):
    def __init__(self, *args, **kwargs):
        super(FlaskApp, self).__init__(*args, **kwargs)


configuration.initialize()
process_emails.initialize()

basic_auth = fh.HTTPBasicAuth()
token_auth = fh.HTTPTokenAuth()
app = FlaskApp(__name__)
CORS(app, supports_credentials=True, resources={r'*': {'origins': configuration.application_link}})
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


@basic_auth.error_handler
@token_auth.error_handler
def unauthorized():
    """The response of the server when getting unauthorized."""

    return flask.make_response('Unauthorized Access', 403)  # Should be 503


@basic_auth.verify_password
def verify_login_credentials(username, password):
    """
    Verify if the credentials are valid.

    :param username: the username.
    :param password: the password.
    :return: whether or not the credentials are valid.
    """

    with session_scope() as session:
        return processing.check_login(session, username, password)


@token_auth.verify_token
def verify_access_token(token):
    """
    Verify if the access token is valid.

    :param token: the token used in the authentication.
    :return: whether or not the token is valid.
    """

    valid, user_id = authentication.validate_token(token.encode(), authentication.TokenType.ACCESS)

    return valid


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = configuration.Session()

    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


class LoginEP(fr.Resource):
    decorators = [basic_auth.login_required]

    def __init__(self):
        super(LoginEP, self).__init__()

    def post(self):
        """Login made by the user, generating an authentication token."""

        with session_scope() as session:
            auth = flask.request.authorization
            user = processing.get_user_by_email(session, auth['username'])

            if user is not None:
                if user.verified:
                    refresh_token = authentication.generate_token(user.id, authentication.TokenType.REFRESH,
                                                                  session=session)

                    if auth['username'].find('@') != -1:
                        username = auth['username'][:auth['username'].index('@')]
                    else:
                        username = auth['username']

                    return flask.make_response(flask.jsonify({
                        'token': str(refresh_token),
                        'username': username, **processing.get_settings(session, user.id)
                    }), 200)
                else:
                    return flask.make_response('Unverified Account', 400)

            # This should never happen
            else:
                print('ERROR: The user passed the decorator verification!')
                return flask.make_response('Unauthorized Access', 403)  # Should be 503


class ExternalLoginEP(fr.Resource):
    def __init__(self):
        super(ExternalLoginEP, self).__init__()

    login_args = \
        {
            'external_token': webargs.fields.Str(required=True),
            'source': webargs.fields.Str(required=True),
            'language': webargs.fields.Str()
        }

    @fp.use_args(login_args)
    def post(self, args):
        """Login with an external token."""

        external_token = args['external_token']
        source = args['source']

        language = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'language':
                language = v

        with session_scope() as session:
            # Get the email from the token
            email = external_authentication.external_authentication(external_token, source)

            # If we can't get the email
            if email is None:
                return flask.make_response('', 400)

            # Check if there's a user
            user = processing.get_user_by_email(session, email)

            # Register the user
            if user is None:
                user = processing.register_external_user(session, email, source, language=language)

                # If the registration failed
                if user is None:
                    return flask.make_response('', 400)

            # Generate the refresh token
            refresh_token = authentication.generate_token(user.id, authentication.TokenType.REFRESH,
                                                          session=session)

            username = user.email[:user.email.index('@')]

            return flask.make_response(flask.jsonify({
                'token': str(refresh_token),
                'username': username, **processing.get_settings(session, user.id)
            }), 200)


class LogoutEP(fr.Resource):
    def __init__(self):
        super(LogoutEP, self).__init__()

    logout_args = \
        {
            'refresh_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(logout_args)
    def post(self, args):
        """Logout of a user's account."""

        with session_scope() as session:
            refresh_token = args['refresh_token']

            processing.logout(session, refresh_token)

            return flask.make_response('', 200)


class RecoverPasswordEP(fr.Resource):
    def __init__(self):
        super(RecoverPasswordEP, self).__init__()

    recover_args = \
        {
            'token': webargs.fields.Str(required=True),
            'password': webargs.fields.Str(required=True)
        }

    @fp.use_args(recover_args)
    def put(self, args):
        """Change the password after a password recovery."""

        token = args['token']
        password = args['password']

        with session_scope() as session:
            if processing.recover_password(session, token, password):
                return flask.make_response('', 200)
            else:
                return flask.make_response('Invalid Token', 400)


class RemindersEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(RemindersEP, self).__init__()

    def get(self):
        """Get the list of reminders of the user."""

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            reminder_list = reminders.get_reminders(session, user_id)

            return flask.make_response(flask.jsonify({'reminder_list': auxiliary.list_to_json(reminder_list)}), 200)

    register_args = \
        {
            'show_session_id': webargs.fields.Int(required=True),
            'anticipation_minutes': webargs.fields.Int(required=True,
                                                       validate=[webargs.validate.Range(min=60, max=1440)])
        }

    @fp.use_args(register_args)
    def post(self, args):
        """Register a reminder."""

        show_session_id = args['show_session_id']
        anticipation_minutes = args['anticipation_minutes']

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            if reminders.register_reminder(session, show_session_id, anticipation_minutes, user_id) is not None:
                return flask.make_response(
                    flask.jsonify({
                        'reminder_list': auxiliary.list_to_json(reminders.get_reminders(session, user_id))
                    }), 201)
            else:
                return flask.make_response('Invalid reminder', 400)

    update_args = \
        {
            'reminder_id': webargs.fields.Int(required=True),
            'anticipation_minutes': webargs.fields.Int(required=True,
                                                       validate=[webargs.validate.Range(min=60, max=1440)])
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Update a reminder."""

        reminder_id = args['reminder_id']
        anticipation_minutes = args['anticipation_minutes']

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            success, msg = reminders.update_reminder(session, reminder_id, anticipation_minutes, user_id)

            if success:
                return flask.make_response(
                    flask.jsonify({
                        'reminder_list': auxiliary.list_to_json(reminders.get_reminders(session, user_id))
                    }), 201)
            else:
                if msg == 'Not found':
                    return flask.make_response('', 404)
                else:
                    return flask.make_response(msg, 400)

    delete_args = \
        {
            'reminder_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args, location='query')
    def delete(self, args):
        """Delete a reminder."""

        reminder_id = args['reminder_id']

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            if db_calls.delete_reminder(session, reminder_id, user_id):
                return flask.make_response(flask.jsonify({
                    'reminder_list': auxiliary.list_to_json(reminders.get_reminders(session, user_id))
                }), 200)
            else:
                return flask.make_response('', 404)


class AlarmsEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(AlarmsEP, self).__init__()

    def get(self):
        """Get the list of alarms of the user."""

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            alarms = processing.get_alarms(session, user_id)

            return flask.make_response(flask.jsonify({'alarm_list': auxiliary.list_to_json(alarms)}), 200)

    register_args = \
        {
            'show_name': webargs.fields.Str(required=True),
            'is_movie': webargs.fields.Bool(required=True),
            'type': webargs.fields.Str(required=True),
            'trakt_id': webargs.fields.Int(),
            'show_language': webargs.fields.Str(),  # TODO: NOT BEING UTILIZED
            'show_season': webargs.fields.Int(validate=[webargs.validate.Range(min=1, max=50)]),
            'show_episode': webargs.fields.Int(validate=[webargs.validate.Range(min=1)])
        }

    @fp.use_args(register_args)
    def post(self, args):
        """Register an alarm."""

        show_name = args['show_name']
        is_movie = args['is_movie']
        alarm_type = args['type']
        trakt_id = None
        show_season = None
        show_episode = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'show_season':
                show_season = v
            elif k == 'show_episode':
                show_episode = v
            elif k == 'trakt_id':
                trakt_id = v

        with session_scope() as session:
            try:
                alarm_type = AlarmType[alarm_type]
            except KeyError:
                return flask.make_response('Invalid Alarm Type', 400)

            # Alarms for Listings are no longer valid
            if alarm_type == AlarmType.LISTINGS:
                return flask.make_response('Invalid Alarm Type', 400)

            if alarm_type == AlarmType.DB and trakt_id is None:
                return flask.make_response('Missing Trakt Id', 400)

            if not is_movie and (show_season is None or show_episode is None):
                return flask.make_response('Missing Season Episode', 400)

            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            if db_calls.register_alarm(session, show_name, trakt_id, is_movie, alarm_type, show_season,
                                       show_episode, user_id) is not None:
                return flask.make_response(
                    flask.jsonify({
                        'alarm_list': auxiliary.list_to_json(processing.get_alarms(session, user_id))
                    }), 201)
            else:
                return flask.make_response('Alarm Already Exists', 400)

    update_args = \
        {
            'alarm_id': webargs.fields.Int(required=True),
            'show_season': webargs.fields.Int(required=True, validate=[webargs.validate.Range(min=1, max=50)]),
            'show_episode': webargs.fields.Int(required=True, validate=[webargs.validate.Range(min=1)])
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Update an alarm."""

        alarm_id = args['alarm_id']
        show_season = args['show_season']
        show_episode = args['show_episode']

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            if processing.update_alarm(session, alarm_id, show_season, show_episode, user_id):
                return flask.make_response(
                    flask.jsonify({
                        'alarm_list': auxiliary.list_to_json(processing.get_alarms(session, user_id))
                    }), 201)
            else:
                return flask.make_response('', 404)

    delete_args = \
        {
            'alarm_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args, location='query')
    def delete(self, args):
        """Delete a alarm."""

        alarm_id = args['alarm_id']

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            processing.remove_alarm(session, alarm_id, user_id)

            return flask.make_response(flask.jsonify({
                'alarm_list': auxiliary.list_to_json(processing.get_alarms(session, user_id))
            }), 200)


class SendEmailEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(SendEmailEP, self).__init__()

    class EmailType(Enum):
        DELETION = 0
        CHANGE_OLD = 1

    email_args = \
        {
            'type': webargs.fields.Str(required=True)
        }

    @fp.use_args(email_args)
    def post(self, args):
        """Send settings email."""

        with session_scope() as session:
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            email_type = args['type']

            # Get the user id from the token
            user_id = authentication.get_token_field(token.encode(), 'user')

            # If it is a user's deletion email request
            if email_type == SendEmailEP.EmailType.DELETION.name:
                if processing.send_deletion_email(session, user_id):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('', 400)

            # If it is an email change email request
            elif email_type == SendEmailEP.EmailType.CHANGE_OLD.name:
                if processing.send_change_email_old(session, user_id):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('', 400)

            # If something else is sent
            else:
                return flask.make_response('', 400)


class SendChangeEmailEP(fr.Resource):
    def __init__(self):
        super(SendChangeEmailEP, self).__init__()

    email_args = \
        {
            'change_token': webargs.fields.Str(required=True),
            'new_email': webargs.fields.Str(required=True)
        }

    @fp.use_args(email_args)
    def post(self, args):
        """Send 'change email' email to new email address."""

        change_token = args['change_token']
        new_email = args['new_email']

        with session_scope() as session:
            success, already_exists = processing.send_change_email_new(session, change_token, new_email)

            if success or already_exists:
                # Even though this means it's a failure, returning a different message from success
                # would result in revealing that there's an associated account
                if already_exists:
                    # TODO: SEND WARNING EMAIL
                    pass

                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)


class SendPasswordRecoveryEmailEP(fr.Resource):
    def __init__(self):
        super(SendPasswordRecoveryEmailEP, self).__init__()

    logout_args = \
        {
            'email': webargs.fields.Str(required=True),
        }

    @fp.use_args(logout_args)
    def post(self, args):
        """Logout of a user's account."""

        email = args['email']

        with session_scope() as session:
            user = processing.get_user_by_email(session, email)

            if user is not None:
                processing.send_password_recovery_email(session, user.id)

            return flask.make_response('', 200)


class SendVerificationEmailEP(fr.Resource):
    def __init__(self):
        super(SendVerificationEmailEP, self).__init__()

    send_args = \
        {
            'email': webargs.fields.Str(required=True)
        }

    @fp.use_args(send_args)
    def post(self, args):
        """Send verification email."""

        email = args['email']

        with session_scope() as session:
            user = processing.get_user_by_email(session, email)

            if user is not None and not user.verified:
                if processing.send_verification_email(user):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('', 400)
            else:
                return flask.make_response('', 400)


class AccessEP(fr.Resource):
    def __init__(self):
        super(AccessEP, self).__init__()

    access_args = \
        {
            'refresh_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(access_args)
    def post(self, args):
        """Getting a new access token."""

        refresh_token = args['refresh_token']

        with session_scope() as session:
            valid, access_token = authentication.generate_access_token(session, refresh_token.encode())

            if valid:
                return flask.make_response(flask.jsonify({'token': str(access_token)}), 200)
            else:
                return flask.make_response('Invalid Token', 403)  # Should be 503


class ChannelsEP(fr.Resource):
    def __init__(self):
        super(ChannelsEP, self).__init__()

    def get(self):
        """Get a list of all available channels."""

        with session_scope() as session:
            channel_list = db_calls.get_channel_list(session)
            return flask.make_response(flask.jsonify(auxiliary.list_to_json(channel_list)), 200)


class ShowsEP(fr.Resource):
    def __init__(self):
        super(ShowsEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True),
            'is_movie': webargs.fields.Bool(),
            'language': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args, location='query')
    def get(self, args):
        """Get search results for the search_text, using the Trakt API."""

        search_text = args['search_text']
        language = args['language']
        is_movie = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'is_movie':
                is_movie = v

        if len(search_text) < 2:
            return flask.make_response('Search Text Too Small', 400)

        with session_scope() as session:
            search_adult = False

            # Get the user settings of whether it should look in channels with adult content or not
            if 'HTTP_AUTHORIZATION' in flask.request.headers.environ:
                token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
                user_id = authentication.get_token_field(token.encode(), 'user')

                user = db_calls.get_user_id(session, user_id)
                search_adult = user.show_adult if user is not None else False

            if search_text[0] == '"' and search_text[-1] == '"':
                search_text = search_text[1:-1]
                exact_name = True
            else:
                exact_name = False

            more_results, shows = processing.search_show_information(session, search_text, is_movie, language,
                                                                     search_adult, exact_name)

            response_dict = {'show_list': shows}

            # Add a remark when there are more results than those on the response
            if more_results and not exact_name:
                response_dict['remark'] = 'Incomplete List'

            return flask.make_response(flask.jsonify(response_dict), 200)


class LocalShowsEP(fr.Resource):
    def __init__(self):
        super(LocalShowsEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(),
            'show_id': webargs.fields.Int(),
            'is_movie': webargs.fields.Bool(),
        }

    @fp.use_args(search_args, location='query')
    def get(self, args):
        """Get search results for the search_text or the show_id, in the listings and streaming services."""

        search_text = None
        show_id = None
        is_movie = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'search_text':
                search_text = v.strip()

            if k == 'show_id':
                show_id = v

            if k == 'is_movie':
                is_movie = v

        if search_text is None and show_id is None:
            return flask.make_response('Invalid request', 400)

        with session_scope() as session:
            search_adult = False

            # Get the user settings of whether it should look in channels with adult content or not
            if 'HTTP_AUTHORIZATION' in flask.request.headers.environ:
                token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
                user_id = authentication.get_token_field(token.encode(), 'user')

                user = db_calls.get_user_id(session, user_id)
                search_adult = user.show_adult if user is not None else False

            # Check whether it is a request by id or by text
            if show_id is not None:
                if is_movie is None:
                    return flask.make_response('Invalid request', 400)

                titles = processing.get_show_titles(session, show_id, is_movie)

                db_shows = processing.search_sessions_db_with_tmdb_id(session, show_id, is_movie)
            else:
                if len(search_text) < 2:
                    return flask.make_response('Search Text Too Small', 400)

                titles = [search_text]

                db_shows = []

            # If it is a search with id
            # - we only want exact title matches
            # - for those results that don't have a TMDB id
            complete_title = show_id is not None
            ignore_with_tmdb_id = show_id is not None

            # db_shows += processing.search_streaming_services_shows_db(session, titles, is_movie=is_movie,
            #                                                          complete_title=complete_title,
            #                                                          search_adult=search_adult,
            #                                                          ignore_with_tmdb_id=ignore_with_tmdb_id)

            db_shows += processing.search_sessions_db(session, titles, is_movie=is_movie, complete_title=complete_title,
                                                      search_adult=search_adult,
                                                      ignore_with_tmdb_id=ignore_with_tmdb_id)

            if len(db_shows) != 0:
                return flask.make_response(flask.jsonify({'show_list': auxiliary.list_to_json(db_shows)}), 200)

            return flask.make_response('Not Found', 404)


class UsersEP(fr.Resource):
    def __init__(self):
        super(UsersEP, self).__init__()

    registration_args = \
        {
            'email': webargs.fields.Email(required=True),
            'password': webargs.fields.Str(required=True),
            'language': webargs.fields.Str()
        }

    @fp.use_args(registration_args)
    def post(self, args):
        """Create a new user's account."""

        email = args['email']
        password = args['password']

        language = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'language':
                language = v

        with session_scope() as session:
            if processing.register_user(session, email, password, language):
                return flask.make_response('', 200)
            else:
                return flask.make_response('', 400)

    update_args = \
        {
            'change_token': webargs.fields.Str(),
            'verification_token': webargs.fields.Str(),
            'current_email': webargs.fields.Str(),
            'new_email': webargs.fields.Str()
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings that require a token."""

        change_token = None
        verification_token = None
        current_email = None
        new_email = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'change_token':
                change_token = v
            elif k == 'verification_token':
                verification_token = v
            elif k == 'current_email':
                current_email = v
            elif k == 'new_email':
                new_email = v

        with session_scope() as session:
            # Update something, that requires email confirmation, on the account
            if change_token is not None:
                if processing.change_user_settings_token(session, change_token):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('Invalid Token', 400)

            # Verify the account
            elif verification_token is not None:
                verified = processing.verify_user(session, verification_token)

                if verified:
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('Invalid Token', 400)

            # Correct email before verification
            elif current_email is not None and new_email is not None:
                user = processing.get_user_by_email(session, current_email)

                # No user was found with that email
                # or user has already verified its account
                if user is None or user.verified:
                    return flask.make_response('', 400)

                if processing.change_user_settings(session, {ChangeType.NEW_EMAIL.value: new_email}, user.id):
                    if processing.send_verification_email(user):
                        return flask.make_response('', 200)
                    else:
                        return flask.make_response('Invalid email', 400)

                else:
                    return flask.make_response('', 400)

            # No parameters
            else:
                return flask.make_response('Missing Parameter', 400)

    deletion_args = \
        {
            'deletion_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(deletion_args, location='query')
    def delete(self, args):
        """Delete a user's account."""

        deletion_token = args['deletion_token']

        with session_scope() as session:
            if processing.delete_user(session, deletion_token):
                return flask.make_response('', 200)
            else:
                return flask.make_response('Invalid Token', 400)


class UsersSettingsEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(UsersSettingsEP, self).__init__()

    def get(self):
        """Get the user's settings, that don't require anything."""

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            settings = processing.get_settings(session, user_id)

            if settings != {}:
                return flask.make_response(flask.jsonify(settings), 200)
            else:
                return flask.make_response('', 404)

    update_args = \
        {
            'include_adult_channels': webargs.fields.Bool(),
            'language': webargs.fields.Str(),
            'excluded_channel_list': webargs.fields.List(webargs.fields.Int())
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings, that don't require anything."""

        include_adult_channels = None
        language = None
        excluded_channel_list = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'include_adult_channels':
                include_adult_channels = v
            elif k == 'language':
                language = v
            elif k == 'excluded_channel_list':
                excluded_channel_list = v

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            changes = {}

            # Update include_adult_channels
            if include_adult_channels is not None:
                changes[ChangeType.INCLUDE_ADULT_CHANNELS.value] = include_adult_channels

            # Update language
            if language is not None and language in configuration.AVAILABLE_LANGUAGES:
                changes[ChangeType.LANGUAGE.value] = language

            # Update excluded channel list
            if excluded_channel_list is not None:
                changes[ChangeType.EXCLUDED_CHANNELS.value] = excluded_channel_list

            # If there are changes to be made
            if changes != {}:
                if processing.change_user_settings(session, changes, user_id):
                    return flask.make_response(flask.jsonify(processing.get_settings(session, user_id)), 200)
                else:
                    return flask.make_response('', 400)

            # If there are no changes to be made
            else:
                return flask.make_response('Invalid Parameters', 400)


class UsersBASettingsEP(fr.Resource):
    decorators = [token_auth.login_required]

    def __init__(self):
        super(UsersBASettingsEP, self).__init__()

    update_args = \
        {
            'password': webargs.fields.Str(required=True),
            'new_password': webargs.fields.Str()
        }

    @fp.use_args(update_args)
    def put(self, args):
        """Change user's settings, that require the password to be sent."""

        password = args['password']

        new_password = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'new_password':
                new_password = v

        with session_scope() as session:
            # Get the user id from the token
            token = flask.request.headers.environ['HTTP_AUTHORIZATION'][7:]
            user_id = authentication.get_token_field(token.encode(), 'user')

            user = db_calls.get_user_id(session, user_id)

            # Check if the password is valid
            valid = verify_login_credentials(user.email, password)

            if not valid:
                return flask.make_response('Unauthorized Access', 403)  # Should be 503

            # Update new_password
            if new_password is not None:
                if password == new_password:
                    return flask.make_response('Same Password', 400)

                if processing.change_user_settings(session, {ChangeType.NEW_PASSWORD.value: new_password}, user_id):
                    return flask.make_response('', 200)
                else:
                    return flask.make_response('', 400)

            # No parameters
            else:
                return flask.make_response('Missing Parameter', 400)


class HighlightsEP(fr.Resource):
    def __init__(self):
        super(HighlightsEP, self).__init__()

    get_args = \
        {
            'year': webargs.fields.Int(required=True),
            'week': webargs.fields.Int(required=True)
        }

    @fp.use_args(get_args, location='query')
    def get(self, args):
        """Get the list of highlights."""

        year = args['year']
        week = args['week']

        with session_scope() as session:
            highlights = processing.get_response_highlights_week(session, year, week)
            return flask.make_response(flask.jsonify({'highlight_list': auxiliary.list_to_json(highlights)}), 200)


# Functions
api.add_resource(LoginEP, '/login', endpoint='login')
api.add_resource(ExternalLoginEP, '/external-login', endpoint='external_login')
api.add_resource(LogoutEP, '/logout', endpoint='logout')
api.add_resource(RecoverPasswordEP, '/recover-password', endpoint='recover_password')
api.add_resource(SendEmailEP, '/send-email', endpoint='send_email')
api.add_resource(SendChangeEmailEP, '/send-change-email', endpoint='send_change_email')
api.add_resource(SendPasswordRecoveryEmailEP, '/send-password-recovery-email', endpoint='send_password_recovery_email')
api.add_resource(SendVerificationEmailEP, '/send-verification-email', endpoint='send_verification_email')

# Resources
api.add_resource(AlarmsEP, '/alarms', endpoint='alarms')
api.add_resource(RemindersEP, '/reminders', endpoint='reminders')
api.add_resource(AccessEP, '/access', endpoint='access')
api.add_resource(ChannelsEP, '/channels', endpoint='channels')
api.add_resource(ShowsEP, '/shows', endpoint='shows')
api.add_resource(LocalShowsEP, '/local-shows', endpoint='local-shows')
api.add_resource(UsersEP, '/users', endpoint='users')
api.add_resource(UsersSettingsEP, '/users-settings', endpoint='users-settings')
api.add_resource(UsersBASettingsEP, '/users-ba-settings', endpoint='users-ba-settings')
api.add_resource(HighlightsEP, '/highlights', endpoint='highlights')

if __name__ == '__main__':
    app.run(debug=True, threaded=True, use_reloader=False)
