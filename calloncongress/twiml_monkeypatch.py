import twilio.twiml
import requests
from flask import g
from calloncongress.i18n import translate, translate_audio, audio_filename_for
from calloncongress.helpers import get_lang
from calloncongress import settings

ACCENT_MAP = {
    'eo': 'es',
}


class Say(twilio.twiml.Say):
    def __new__(cls, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
            kwargs.update(language=lang)

        lang = kwargs['language']
        kwargs['language'] = ACCENT_MAP.get(lang, lang)

        url = translate_audio(audio_filename_for(text), language=lang)
        print audio_filename_for(text)
        print url
        exists = False
        try:
            exists = (requests.head(url, timeout=1.5).status_code == 200)
        except:
            pass
        # Play audio if it exists. If a voice was passed explicitly, never play audio.
        if exists and 'voice' not in g.request_params.keys():
            play = Play(audio_filename_for(text), **kwargs)
            return play

        return super(Say, cls).__new__(cls, text, **kwargs)

    def __init__(self, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
            kwargs.update(language=lang)

        if 'voice' not in kwargs.keys():
            kwargs.update(voice=g.request_params.get('voice', settings.DEFAULT_VOICE))

        super(Say, self).__init__(text, **kwargs)
        self.body = translate(text, **kwargs)


class Play(twilio.twiml.Play):
    def __init__(self, url, **kwargs):
        super(Play, self).__init__(url, **kwargs)
        self.body = translate_audio(url, **kwargs)

twilio.twiml.Say = Say
twilio.twiml.Play = Play
