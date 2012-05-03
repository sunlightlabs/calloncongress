from functools import wraps

from flask import abort, g, request, Response
from twilio.util import RequestValidator

from calloncongress import settings


def twilioify(func):
    """
    Decorator that validates Twilio calls and creates the call context in the request.
    """

    @wraps(func)
    def decorated(*args, **kwargs):

        params = request.form if request.method == 'POST' else request.args

        if 'CallSid' not in params:
            return abort(404)

        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        sig_header = request.headers.get('X-Twilio-Signature', '')

        print request.base_url, params, sig_header

        # validator params are called URL, POST vars, and signature
        if not validator.validate(request.base_url, params, sig_header):
            return abort(401)

        # load the call from Mongo or create if one does not exist
        g.call = load_call(request.form['CallSid'], params)

        g.zipcode = g.call['context'].get('zipcode', None)
        g.legislator = g.call['context'].get('legislator', None)

        twilio_response = func(*args, **kwargs)

        return Response(str(twilio_response), mimetype='application/xml')

    return decorated


def load_call(sid, params):
    """ Loads a call from the datastore or creates a new one if one
        does not exist. Appends the current call status to the list
        of requests involved in this call.

        sid: the unique call ID from Twilio
        params: the POSTed request parameters
    """

    # find existing call
    doc = g.db.calls.find_one({'call_sid': sid})

    if doc is None:
        # create new call if call does not exist
        doc = {
            'call_sid': sid,
            'from': params['From'],
            'to': params['To'],
            'caller_name': params.get('CallerName', None),
            'context': {
                'zipcode': None,
                'legislator': None,
            },
            'language': '',
        }
        g.db.calls.insert(doc)

    # create array for requests list
    if 'requests' not in doc:
        doc['requests'] = []

    # append current request information and update current status
    doc['requests'].append({
        'timestamp': g.now,
        'call_status': params['CallStatus']
    })
    doc['current_status'] = params['CallStatus']

    return doc
