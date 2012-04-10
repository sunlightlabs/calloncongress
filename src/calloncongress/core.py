from functools import wraps

from flask import abort, g, request, Response
from twilio.util import RequestValidator

def twilioify(func):
    """
        This decorator method is used to validate Twilio calls
        and create the call context in the request.
    """

    @wraps(func)
    def decorated(*args, **kwargs):

        if 'CallSid' not in request.form:
            return abort(404)

        validator = RequestValidator(settings.AUTH_TOKEN)
        sig_header = request.headers.get('X-Twilio-Signature', '')

        # validator params are called URL, POST vars, and signature
        if not validator.validate(request.base_url, request.form, sig_header):
            return abort(401)

        # load the call from Mongo or create if one does not exist
        g.call = data.load_call(request.form['CallSid'], request.form)

        g.zipcode = g.call['context'].get('zipcode', None)
        g.legislator = g.call['context'].get('legislator', None)

        twilio_response = func(*args, **kwargs)

        return Response(str(twilio_response), mimetype='application/xml')

    return decorated