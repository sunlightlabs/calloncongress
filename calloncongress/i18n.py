from flask import g
from twilio import twiml
import hashlib


class LanguageResponse(twiml.Response):

    def say(self, *args, **kwargs):
        return super(LanguageResponse, self).say(*args, **kwargs)


def lang_url(fn):
    lang = getattr(g, 'language_code', 'en')
    return "%s/%s" % (lang, fn)


def translate(s):
    hsh = hashlib.md5(s).hexdigest()
    trans = g.db.translations.find_one({'hash': hsh, 'lang': getattr(g, 'language_code', 'en')})
    if trans:
        return trans.translation
    return s
