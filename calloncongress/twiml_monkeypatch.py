import twilio.twiml
import requests
from calloncongress.i18n import translate, translate_audio, audio_filename_for
from calloncongress.helpers import get_lang
from calloncongress import settings


class Say(twilio.twiml.Say):
    def __new__(cls, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
            kwargs.update(language=lang)

        url = translate_audio(audio_filename_for(text))
        if requests.head(url, timeout=1).status_code == 200:
            play = Play(audio_filename_for(text), **kwargs)
            return play
        return super(Say, cls).__new__(cls, text, **kwargs)

    def __init__(self, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
            kwargs.update(language=lang)

        if 'voice' not in kwargs.keys():
            kwargs.update(voice=settings.DEFAULT_VOICE)
        super(Say, self).__init__(text, **kwargs)
        self.body = translate(text)


class Play(twilio.twiml.Play):
    def __init__(self, url, **kwargs):
        super(Play, self).__init__(url, **kwargs)
        self.body = translate_audio(url)

twilio.twiml.Say = Say
twilio.twiml.Play = Play
