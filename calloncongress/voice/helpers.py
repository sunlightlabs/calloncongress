import re

from twilio import twiml
from flask import g, request, url_for
from calloncongress import settings


def language_is_selected():
    if not g.call['context'].get('language'):
        r = twiml.Response()
        if 'Digits' in request.values:
            sel = int(request.values.get('Digits', 1))
            g.call['context']['language'] = settings.LANGUAGES[sel - 1][0]
        else:
            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT,
                          action=url_for('.index'), method='POST') as rg:
                rg.say('Welcome to Call on Congress. Press 1 to continue in English.', language='en')
                rg.say('Presione 2 para continuar en espanol.', language='es')

        return r

    return True


def zipcode_is_selected():
    if not g.call['context'].get('zipcode'):
        r = twiml.Response()
        if 'Digits' in request.values:
            sel = int(request.values.get('Digits', 5))
            g.call['context']['zipcode'] = settings.LANGUAGES[sel - 1][0]
        else:
            with r.gather(numDigits=5, timeout=settings.INPUT_TIMEOUT,
                          action=url_for('.index'), method='POST') as rg:
                rg.play("http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/intro.wav")

        return r

    return True


def bill_type(abbr):
    abbr = re.split(r'([a-zA-Z.\-]*)', abbr)[1].lower().replace('.', '')
    return {
        'hr': 'House Bill',
        'hres': 'House Resolution',
        'hjres': 'House Joint Resolution',
        'hcres': 'House Concurrent Resolution',
        's': 'Senate Bill',
        'sres': 'Senate Resolution',
        'sjres': 'Senate Joint Resolution',
        'scres': 'Senate Concurrent Resolution',
    }.get(abbr)


def rep_choices(**kwargs):
    pass


def selected_rep_name(**kwargs):
    pass


def selected_rep_url(**kwargs):
    pass


def selected_rep_biography_url(**kwargs):
    pass


def selected_rep_donors_url(**kwargs):
    pass


def selected_rep_votes_url(**kwargs):
    pass


def selected_rep_call_office_url(**kwargs):
    pass


def referrer(**kwargs):
    pass


def selected_bill_name(**kwargs):
    pass


def selected_bill_url(**kwargs):
    pass


def selected_bill_choices(**kwargs):
    pass


def parent_url_for(current):
    from calloncongress.voice.menu import MENU
    parent = MENU.get(current).get('parent', 'main')
    try:
        if parent.func_name == 'referrer':
            try:
                parent = parent_url_for(g.referrer)
            except AttributeError:
                parent = 'main'
    except AttributeError:
        pass

    return url_for(MENU.get(parent).get('route'))


def handle_selection(**kwargs):
    pass
