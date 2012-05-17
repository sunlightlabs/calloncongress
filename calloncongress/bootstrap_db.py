"""This is a convenience file for connecting to the db via heroku"""

import pymongo
import urlparse
from calloncongress import settings

mongo_uri = getattr(settings, 'MONGO_URI', None)
if not mongo_uri:
    mongo_uri = getattr(settings, 'MONGOLAB_URI', None)
if not mongo_uri:
    mongo_uri = getattr(settings, 'MONGOHQ_URI', None)
if mongo_uri:
    conn = pymongo.Connection(host=mongo_uri)
else:
    conn = pymongo.Connection()
try:
    db_name = urlparse.urlparse(mongo_uri).path.strip('/')
except AttributeError:
    db_name = 'capitolphone'

db = getattr(conn, db_name)
if db:
    print 'Database connection opened and stored as db.'
