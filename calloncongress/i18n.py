import hashlib

from flask import g
import pyglot

from calloncongress.helpers import get_lang
from calloncongress import settings

translator = pyglot.Translator(key=settings.GOOGLE_SERVICES_KEY)


def translate(s, **kwargs):
    query = {
        'lang': kwargs.get('language', get_lang(default=settings.DEFAULT_LANGUAGE)),
        'hash': hashlib.md5(s).hexdigest(),
    }

    if query.get('lang') == 'en':
        return s

    trans = g.db.translations.find_one(**query)
    if trans:
        return trans.translation
    else:
        trans = translator.translate(s, target=query.get('lang'))
        query.update(translation=trans.translatedText)
        s = query.get('translation')
        g.db.translations.save(query)

    return s


def translate_audio(fn, **kwargs):
    if 'language' not in kwargs.keys():
        kwargs.update(language=get_lang(default=settings.DEFAULT_LANGUAGE))
    return "%s/%s/%s/" % (settings.AUDIO_ROOT, kwargs.get('language'), fn)
