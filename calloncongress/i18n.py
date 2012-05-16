import hashlib
import os
import re

from flask import g
from pyglot import Translator, GTranslatorError

from calloncongress.helpers import get_lang, slugify
from calloncongress import settings

translator = Translator(key=settings.GOOGLE_SERVICES_KEY)


def translate(s, **kwargs):
    query = {
        'lang': kwargs.get('language', get_lang(default=settings.DEFAULT_LANGUAGE)),
        'hash': hashlib.md5(s).hexdigest(),
    }

    if query.get('lang') == 'en':
        return s

    trans = g.db.translations.find_one(query)
    if trans:
        return trans['translation']
    else:
        try:
            trans = translator.translate(s, target=query.get('lang'))
            query.update(translation=trans.translatedText)
            s = query.get('translation')
            g.db.translations.save(query)
        except GTranslatorError:
            pass
    return s


def translate_audio(text, **kwargs):
    if 'language' not in kwargs.keys():
        kwargs.update(language=get_lang(default=settings.DEFAULT_LANGUAGE))
    if settings.AUDIO_ROOT.startswith('/'):
        return os.path.join(settings.AUDIO_ROOT, kwargs.get('language'), audio_filename_for(text))
    elif re.match(r'^https?://', settings.AUDIO_ROOT):
        return "%s/%s/%s" % (settings.AUDIO_ROOT, kwargs.get('language'), audio_filename_for(text))
    else:
        return os.path.join(settings.PROJECT_ROOT, settings.AUDIO_ROOT, kwargs.get('language'), audio_filename_for(text))


def audio_filename_for(text, **kwargs):
    ext = kwargs.get('ext', 'mp3')
    slug = slugify(text[:20])
    hsh = hashlib.md5(text).hexdigest()
    return "%s-%s.%s" % (hsh, slug, ext)
