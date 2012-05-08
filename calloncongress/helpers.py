import urllib

from flask import g, request


def digitless_querystring():
    querydict = request.values.to_dict()
    try:
        querydict = delattr(querydict, 'Digits')
    except AttributeError:
        pass

    return urllib.urlencode(querydict)


def digitless_url():
    return "%s?%s" % (request.path, digitless_querystring())


def log_redirect_url():
    write_context('redirect_to', "%s?%s" % (request.path, digitless_querystring()))


def reset_redirect_url():
    flush_context('redirect_to')


def read_context(key, default=None):
    try:
        return g.call['context'][key]
    except:
        return default


def write_context(key, value):
    try:
        g.call['context'][key] = value
        return True
    except:
        return False


def flush_context(key):
    try:
        del g.call['context'][key]
        return True
    except:
        return False


def get_lang(**kwargs):
    return read_context('language', kwargs.get('default', None))


def get_zip():
    return read_context('zipcode')
