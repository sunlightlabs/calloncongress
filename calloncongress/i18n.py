import hashlib

from flask import g
from calloncongress import settings


def lang_url(fn):
    lang = g.call.get['language']
    return "%s/%s/%s" % (settings.AUDIO_ROOT, lang, fn)


def translate(s):
    hsh = hashlib.md5(s).hexdigest()
    trans = g.db.translations.find_one({'hash': hsh, 'lang': g.call.get['language']})
    if trans:
        return trans.translation
    return s
