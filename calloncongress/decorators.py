from functools import wraps

from flask import abort, g, request, Response
from twilio.util import RequestValidator

from calloncongress.helpers import read_context, write_context
from calloncongress import settings, load_call


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
        if not validator.validate(vurl, vparams, sig_header):
            return abort(401)

        # load the call from Mongo or create if one does not exist
        g.call = load_call(request.values['CallSid'], request.values)

        g.zipcode = read_context('zipcode', None)
        g.legislator = read_context('legislator', None)

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
