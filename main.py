import flask
import webargs
import threading
import datetime

from flask_cors import CORS, cross_origin

import flask_restful as fr
import flask_httpauth as fh
import flask_limiter as fl
import webargs.flaskparser as fp

import authentication
import processing


def daily_tasks():
    """Run the daily tasks."""

    # Get the date of the last update
    last_update_date = processing.get_last_update()

    processing.clear_show_list()

    processing.update_show_list()

    processing.process_reminders(last_update_date)

    # Schedule the new update
    next_update = datetime.datetime.now() + datetime.timedelta(days=1)
    next_update = next_update.replace(hour=10, minute=0)
    threading.Timer((next_update - datetime.datetime.now()).seconds, daily_tasks).start()


class FlaskApp(flask.Flask):
    def __init__(self, *args, **kwargs):
        # TODO: UNCOMMENT THIS WHEN UPDATE IS NEEDED
        # threading.Timer(10, daily_tasks).start()
        super(FlaskApp, self).__init__(*args, **kwargs)


basic_auth = fh.HTTPBasicAuth()
app = FlaskApp(__name__)
CORS(app, support_credentials=True)
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


@basic_auth.error_handler
def unauthorized():
    """The response of the server when getting unauthorized."""

    return flask.make_response('Unauthorized Access', 403)


@basic_auth.verify_password
def verify_auth_token(token, unused):
    """
    Verify if the access token is valid.

    :param token: the token used in the authentication.
    :param unused: placeholder necessary for the @auth.verify_password.
    :return: whether or not the token is valid.
    """

    valid, user_id = authentication.validate_token(token.encode(), authentication.TokenType.ACCESS)

    return valid


class RegistrationEP(fr.Resource):
    def __init__(self):
        super(RegistrationEP, self).__init__()

    registration_args = \
        {
            'email': webargs.fields.Str(required=True),
            'password': webargs.fields.Str(required=True)
        }

    @fp.use_args(registration_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Register a new user."""

        email = args['email']
        password = args['password']

        processing.register_user(email, password)

        return flask.jsonify({'registration': 'The registration was a success, check your email!'})


class LoginEP(fr.Resource):
    def __init__(self):
        super(LoginEP, self).__init__()

    login_args = \
        {
            'email': webargs.fields.Str(required=True),
            'password': webargs.fields.Str(required=True)
        }

    @fp.use_args(login_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Login made by the user, generating an authentication token."""

        email = args['email']
        password = args['password']

        valid, user_id = processing.check_login(email, password)

        if valid:
            auth_token = authentication.generate_token(user_id, authentication.TokenType.AUTHENTICATION).decode()
            return flask.jsonify({'login': 'The login was a success!', 'token': str(auth_token)})
        else:
            return flask.jsonify({'login': 'The login failed!'})


class LogoutEP(fr.Resource):
    def __init__(self):
        super(LogoutEP, self).__init__()

    logout_args = \
        {
            'auth_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(logout_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Logout of a user's account."""

        auth_token = args['auth_token']

        processing.logout(auth_token)

        return flask.jsonify({'logout': 'The logout was successful!'})


class AccessEP(fr.Resource):
    def __init__(self):
        super(AccessEP, self).__init__()

    access_args = \
        {
            'auth_token': webargs.fields.Str(required=True)
        }

    @fp.use_args(access_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Getting a new access token."""

        auth_token = args['auth_token']

        valid, access_token = authentication.generate_access_token(auth_token.encode())

        if valid:
            return flask.jsonify({'access': 'valid token', 'token': str(access_token.decode())})
        else:
            return flask.jsonify({'access': 'invalid token', 'token': access_token})


class SearchEP(fr.Resource):
    def __init__(self):
        super(SearchEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True),
            'type': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    @cross_origin(supports_credentials=True)
    def get(self, args):
        """Get search results for the search_text."""

        search_text = args['search_text']
        source_type = args['type']

        if len(search_text) < 3:
            return flask.jsonify({'search': 'Search text needs at least three characters!'})

        if source_type == 'DB':
            db_shows = processing.search_db([search_text], only_between=False)

            if len(db_shows) != 0:
                return flask.jsonify({'search': 'shows', 'shows': processing.list_to_json(db_shows)})
        elif source_type != 'TRAKT':
            return flask.jsonify({'search': 'Unknown type!'})

        shows = processing.search_show_information(search_text)

        return flask.jsonify({'search': 'trakt', 'shows': shows})


class ReminderEP(fr.Resource):
    decorators = [basic_auth.login_required]

    def __init__(self):
        super(ReminderEP, self).__init__()

    search_args = \
        {
            'show_id': webargs.fields.Str(required=True),
            'is_show': webargs.fields.Bool(required=True),
            'type': webargs.fields.Str(required=True),
            'show_season': webargs.fields.Int(),
            'show_episode': webargs.fields.Int(),
            'comparison_type': webargs.fields.Int()
        }

    @fp.use_args(search_args)
    @cross_origin(supports_credentials=True)
    def post(self, args):
        """Get search results for the search id."""

        # Search_id will be either a seriesid or a pid depending on whether its a show or not
        show_id = args['show_id']
        is_show = args['is_show']
        reminder_type = args['type']

        show_season = None
        show_episode = None
        comparison_type = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'show_season':
                show_season = v
            elif k == 'show_episode':
                show_episode = v
            elif k == 'comparison_type':
                comparison_type = v

        if reminder_type == 'DB':
            reminder_type = 0
        elif reminder_type == 'TRAKT':
            reminder_type = 1
        else:
            return flask.jsonify({'reminder': 'Unknown type!'})

        processing.register_reminder(show_id, is_show, reminder_type, show_season, show_episode, comparison_type)

        return flask.jsonify({'reminder': 'Reminder successfully registered!'})

    delete_args = \
        {
            'reminder_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args)
    @cross_origin(supports_credentials=True)
    def delete(self, args):
        """Get search results for the search id."""

        reminder_id = args['reminder_id']

        processing.remove_reminder(reminder_id)

        return flask.jsonify({'reminder': 'Reminder successfully removed!'})


api.add_resource(RegistrationEP, '/0.1/registration', endpoint='registration')
api.add_resource(LoginEP, '/0.1/login', endpoint='login')
api.add_resource(LogoutEP, '/0.1/logout', endpoint='logout')
api.add_resource(AccessEP, '/0.1/access', endpoint='access')
api.add_resource(SearchEP, '/0.1/search', endpoint='search')
api.add_resource(ReminderEP, '/0.1/reminder', endpoint='reminder')

if __name__ == '__main__':
    app.run(debug=True, threaded=True, use_reloader=False)
