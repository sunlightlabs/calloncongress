import hashlib
import re
import urlparse

from flask import g, request
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


def audio_root_as_url():
    if re.match(r'^https?://', settings.AUDIO_ROOT):
        return settings.AUDIO_ROOT
    else:
        return urlparse.urljoin(request.base_url, settings.AUDIO_ROOT)


def audio_filename_for(text, **kwargs):
    ext = kwargs.get('ext', 'wav')
    slug = slugify(text[:40])
    # hash text with whitespace removed
    hsh = hashlib.md5(re.sub(r'\s', '', text)).hexdigest()
    return "%s-%s.%s?v=%s" % (hsh, slug, ext, getattr(settings, 'STATIC_VERSION', 1))


def translate_audio(filename, **kwargs):
    print kwargs
    if 'language' not in kwargs.keys():
        kwargs.update(language=get_lang(default=settings.DEFAULT_LANGUAGE))
    return "%s/%s/%s" % (audio_root_as_url(), kwargs.get('language'), filename)
