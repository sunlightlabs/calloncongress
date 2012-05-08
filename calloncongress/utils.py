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
        if 'CallSid' not in request.values:
            return abort(401, 'Request must be a signed Twilio request.')

        validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
        sig_header = request.headers.get('X-Twilio-Signature', '')

        if request.method == 'POST':
            vparams = request.form
            vurl = request.base_url
        else:
            vparams = {}
            vurl = request.url

        # validator params are called URL, POST vars, and signature
        # if not validator.validate(vurl, vparams, sig_header):
        #     return abort(401)

        # load the call from Mongo or create if one does not exist
        g.call = load_call(request.values['CallSid'], request.values)

        g.zipcode = g.call['context'].get('zipcode', None)
        g.legislator = g.call['context'].get('legislator', None)

        twilio_response = func(*args, **kwargs)

        return Response(str(twilio_response), mimetype='application/xml')

    return decorated


def validate_before(*args):
    """
    Decorator that makes sure required callbacks have been run and appropriate values provided.
    """
    dependencies = args

    def decorator(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            for dep in dependencies:
                valid = dep()
                if valid is not True:
                    return str(valid)

            return func(*args, **kwargs)
        return decorated
    return decorator


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
