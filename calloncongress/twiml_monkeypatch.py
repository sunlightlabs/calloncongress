import twilio.twiml
from twilio.twiml import Say, Play
from calloncongress.i18n import translate, translate_audio
from calloncongress.helpers import get_lang
from calloncongress import settings


class PolyglotSay(Say):
    def __init__(self, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
        if 'voice' not in kwargs.keys():
            kwargs.update(language=lang, voice=settings.DEFAULT_VOICE)
        super(Say, self).__init__(**kwargs)
        self.body = translate(text)


class PolyglotPlay(Play):
    def __init__(self, url, **kwargs):
        super(Play, self).__init__(**kwargs)
        self.body = translate_audio(url)

twilio.twiml.Say = PolyglotSay
twilio.twiml.Play = PolyglotPlay
