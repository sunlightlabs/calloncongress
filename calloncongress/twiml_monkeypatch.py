import twilio.twiml
from calloncongress.i18n import translate, translate_audio
from calloncongress.helpers import get_lang
from calloncongress import settings


class Say(twilio.twiml.Say):
    def __init__(self, text, **kwargs):
        if 'language' not in kwargs.keys():
            lang = get_lang(default=settings.DEFAULT_LANGUAGE)
        if 'voice' not in kwargs.keys():
            kwargs.update(language=lang, voice=settings.DEFAULT_VOICE)
        super(Say, self).__init__(text, **kwargs)
        self.body = translate(text)


class Play(twilio.twiml.Play):
    def __init__(self, url, **kwargs):
        super(Play, self).__init__(url, **kwargs)
        self.body = translate_audio(url)

twilio.twiml.Say = Say
twilio.twiml.Play = Play
