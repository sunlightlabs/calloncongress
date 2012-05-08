import hashlib

from flask import g
from calloncongress.helpers import get_lang
from calloncongress import settings


def translate(s, **kwargs):
    query = {
        'lang': kwargs.get('language', get_lang(default=settings.DEFAULT_LANGUAGE)),
        'hash': hashlib.md5(s).hexdigest(),
    }
    trans = g.db.translations.find_one(**query)
    if trans:
        return trans.translation
    return s


def translate_audio(fn, **kwargs):
    if 'language' not in kwargs.keys():
        kwargs.update(language=get_lang(default=settings.DEFAULT_LANGUAGE))
    return "%s/%s/%s/" % (settings.AUDIO_ROOT, kwargs.get('language'), fn)
