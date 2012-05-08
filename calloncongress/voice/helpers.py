import re

from twilio import twiml
from flask import g, request, url_for
from calloncongress import settings
from calloncongress.helpers import digitless_url, read_context, write_context, get_lang, get_zip


def language_selection():
    if not get_lang():
        errors = []
        r = twiml.Response()

        # Handle twimlet-style params
        if 'language' in request.values.keys():
            sel = request.values['language']
            try:
                sel = int(sel)
                write_context('language', settings.LANGUAGES[sel - 1][0])
            except ValueError:
                if sel in [lang[0] for lang in settings.LANGUAGES]:
                    write_context('language', sel)

        # Collect collect digits if named params are not set
        if 'Digits' in request.values:
            sel = int(request.values.get('Digits', 1))
            try:
                write_context('language', settings.LANGUAGES[sel - 1][0])
            except:
                errors.append('%d is not a valid selection, please try again.')

        # Prompt and gather if language is not valid
        if not get_lang():
            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT,
                          action=digitless_url(), method='POST') as rg:
                if not len(errors):
                    rg.say('Welcome to Call on Congress.')
                else:
                    rg.say(' '.join(errors))
                rg.say('Press 1 to continue in English.', language='en')
                rg.say('Presione 2 para continuar en espanol.', language='es')

            return r

    return True


def zipcode_selection():
    if not get_zip():
        errors = []
        r = twiml.Response()
        if 'Digits' in request.values:
            sel = request.values.get('Digits')
            if len(sel) == 5:
                write_context('zipcode', int(sel))
            else:
                errors.append('%d is not a valid zipcode, please try again.')

        if not get_zip():
            with r.gather(numDigits=5, timeout=settings.INPUT_TIMEOUT,
                          action=digitless_url(), method='POST') as rg:
                rg.say("""To help us identify your representatives,
                          please use the telephone keypad to enter
                          your five-digit zip code now.""")

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
