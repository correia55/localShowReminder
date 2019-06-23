import flask
import webargs
import threading
import time

import flask_restful as fr
import flask_httpauth as fh
import flask_limiter as fl
import webargs.flaskparser as fp

import processing

basic_auth = fh.HTTPBasicAuth()
app = flask.Flask(__name__)
api = fr.Api(app)

# Limit the number of requests that can be made in a certain time period
limiter = fl.Limiter(
    app,
    key_func=fl.util.get_remote_address,
    default_limits=['5 per second', '50 per minute', '1000 per day']
)


def list_to_json(list_of_objects):
    result = []

    for o in list_of_objects:
        result.append(o.to_dict())

    return result


def update_list():
    """Update the list of movies every day."""

    while True:
        processing.update_show_list()

        processing.process_reminders()

        time.sleep(86400)


@app.before_first_request
def start_update_thread():
    thread = threading.Thread(target=update_list)
    thread.start()


class SearchEP(fr.Resource):
    def __init__(self):
        super(SearchEP, self).__init__()

    search_args = \
        {
            'search_text': webargs.fields.Str(required=True),
            'type': webargs.fields.Str(required=True)
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search_text."""

        search_text = args['search_text']
        type = args['type']

        if len(search_text) < 3:
            return flask.jsonify({'search': 'Search text needs at least three characters!'})

        if type == 'DB':
            db_shows = processing.search_db([search_text], only_between=False)

            if len(db_shows) != 0:
                return flask.jsonify({'search': 'shows', 'shows': list_to_json(db_shows)})
        elif type != 'TRAKT':
            return flask.jsonify({'search': 'Unknown type!'})

        shows = processing.search_show_information(search_text)

        return flask.jsonify({'search': 'trakt', 'shows': shows})


class ReminderEP(fr.Resource):
    def __init__(self):
        super(ReminderEP, self).__init__()

    search_args = \
        {
            'show_id': webargs.fields.Str(required=True),
            'is_show': webargs.fields.Bool(required=True),
            'type': webargs.fields.Str(required=True),
            'show_season': webargs.fields.Int(),
            'show_episode': webargs.fields.Int()
        }

    @fp.use_args(search_args)
    def get(self, args):
        """Get search results for the search id."""

        # Search_id will be either a seriesid or a pid depending on whether its a show or not
        show_id = args['show_id']
        is_show = args['is_show']
        reminder_type = args['type']

        show_season = None
        show_episode = None

        for k, v in args.items():
            if v is None:
                continue

            if k == 'show_season':
                show_season = v
            elif k == 'show_episode':
                show_episode = v

        if reminder_type == 'DB':
            reminder_type = 0
        elif reminder_type == 'TRAKT':
            reminder_type = 1
        else:
            return flask.jsonify({'reminder': 'Unknown type!'})

        processing.register_reminder(show_id, is_show, reminder_type, show_season, show_episode)

        return flask.jsonify({'reminder': 'Reminder successfully registered!'})

    delete_args = \
        {
            'reminder_id': webargs.fields.Int(required=True)
        }

    @fp.use_args(delete_args)
    def delete(self, args):
        """Get search results for the search id."""

        reminder_id = args['reminder_id']

        processing.remove_reminder(reminder_id)

        return flask.jsonify({'reminder': 'Reminder successfully removed!'})


api.add_resource(SearchEP, '/0.1/search', endpoint='search')
api.add_resource(ReminderEP, '/0.1/reminder', endpoint='reminder')


if __name__ == '__main__':
    app.run(debug=True, threaded=True)
