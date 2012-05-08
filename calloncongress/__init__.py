import datetime
import pymongo
import urlparse
import logging
logger = logging.getLogger(__name__)

from raven.contrib.flask import Sentry
from raven.conf import setup_logging
from raven.handlers.logging import SentryHandler
from flask import Flask, g, request
from calloncongress import settings

from calloncongress import twiml_monkeypatch
from calloncongress.web import web
from calloncongress.voice import voice
# from calloncongress.sms import sms

app = Flask(__name__)
app.register_blueprint(web)
app.register_blueprint(voice, url_prefix='/voice')
# app.register_blueprint(sms, url_prefix='/sms')

# init sentry if a DSN is present
try:
    app.config['SENTRY_DSN'] = settings.SENTRY_DSN
    sentry = Sentry(app)
    handler = SentryHandler(settings.SENTRY_DSN)
    setup_logging(handler)
except AttributeError:
    pass


@app.before_request
def before_request():
    """
    Sets up request context by setting current request time (UTC),
    creating MongoDB connection and reference to collection.
    """
    mongo_uri = getattr(settings, 'MONGO_URI', None)
    if not mongo_uri:
        mongo_uri = getattr(settings, 'MONGOLAB_URI', None)
    if not mongo_uri:
        mongo_uri = getattr(settings, 'MONGOHQ_URI', None)
    if mongo_uri:
        g.conn = pymongo.Connection(host=mongo_uri)
    else:
        g.conn = pymongo.Connection()
    try:
        db_name = urlparse.urlparse(mongo_uri).path.strip('/')
    except AttributeError:
        db_name = 'capitolphone'

    g.now = datetime.datetime.utcnow()
    g.db = getattr(g.conn, db_name)


@app.after_request
def after_request(response):
    """
    Saves the call object from the request context if one exists.
    """
    if hasattr(g, 'call') and g.call is not None:
        g.db.calls.save(g.call)
    return response


@app.teardown_request
def teardown_request(exception):
    """
    Disconnects from the MongoDB instance.
    """
    g.conn.disconnect()
