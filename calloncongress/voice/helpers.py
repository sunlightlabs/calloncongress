import re

from twilio import twiml
from flask import g, request, redirect, url_for
from calloncongress import settings, data
from calloncongress.helpers import digitless_url, read_context, write_context, flush_context, get_lang, get_zip


def language_selection():
    if not get_lang():
        errors = []
        r = twiml.Response()

        # Handle twimlet-style params
        if 'language' in g.request_params.keys():
            sel = g.request_params['language']
            try:
                sel = int(sel)
                write_context('language', settings.LANGUAGES[sel - 1][0])
            except ValueError:
                if sel in [lang[0] for lang in settings.LANGUAGES]:
                    write_context('language', sel)

        # Collect and wipe digits if named params are not set
        if 'Digits' in g.request_params.keys():
            sel = int(g.request_params.get('Digits', 1))
            try:
                write_context('language', settings.LANGUAGES[sel - 1][0])
            except:
                errors.append('%d is not a valid selection, please try again.')

            del g.request_params['Digits']

        # Prompt and gather if language is not valid
        if not get_lang():
            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
                if not len(errors):
                    rg.say("""Welcome to Call on Congress, the Sunlight Fuondation's
                              free service that helps you keep our lawmakers accountable
                              with important information about our government.
                           """)
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

        if 'Digits' in g.request_params.keys():
            sel = g.request_params.get('Digits')
            if len(sel) == 5:
                write_context('zipcode', int(sel))
            else:
                errors.append('%s is not a valid zipcode, please try again.' % sel)

            del g.request_params['Digits']

        if not get_zip():
            if request.path.startswith == '/member':
                reason = 'To help us identify your representatives,'
            elif request.path.startswith == '/voting':
                reason = 'To help us find your election office,'
            else:
                reason = None

            with r.gather(numDigits=5, timeout=settings.INPUT_TIMEOUT) as rg:
                if len(errors):
                    rg.say(' '.join(errors))
                if reason:
                    rg.say(reason)
                rg.say("""please use the telephone keypad to enter
                          your five-digit zip code now.""")

            return r

    return True


def bioguide_selection():
    errors = []
    r = twiml.Response()

    # Handle twimlet-style params
    if 'bioguide_id' in g.request_params.keys():
        return True

    # Make sure there's a legislators list in the call context.
    # If not, short-circuit to zip collection and repost to get legislator list
    # before prompting for a selection.
    if 'Digits' in g.request_params.keys():
        if not len(read_context('legislators')):
            del g.request_params['Digits']
            return bioguide_selection()

        sel = g.request_params['Digits']
        del g.request_params['Digits']
        try:
            legislator = read_context('legislators')[sel - 1]
            g.request_params['bioguide_id'] = legislator['bioguide_id']
            return True
        except:
            errors.append('%d is not a valid selection, please try again.')

    if 'bioguide_id' not in g.request_params.keys():
        if not len(read_context('legislators')):
            if not get_zip():
                return zipcode_selection()
            load_members_for(get_zip())

        legislators = read_context('legislators')
        if len(legislators):
            if len(legislators) > 3:
                r.say("""Since your zip code covers more than one congressional district,
                         you will be provided with a list of all possible legislators that
                         may represent you. Please select from the following names:""")
            else:
                r.say("""We identified your representatives in Congress. Please select from
                         the following names:""")

            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
                options = [(l['fullname'], l['bioguide_id']) for l in legislators]
                script = " ".join("Press %i for %s." % (index + 1, o[0]) for index, o in enumerate(options))
                script += " Press 0 to enter a new zipcode."
                rg.say(script)
        else:
            if not get_lang() and g.request_params.get('lanugae'):
                write_context('language', g.request_params.get('language'))

            r.say("I'm sorry, we weren't able to locate any representatives for %s." % get_zip())
            flush_context('zipcode')
            with r.gather(numDigits=5, timeout=settings.INPUT_TIMEOUT, action=url_for('.members', next_url=request.path)) as rg:
                rg.say("Please enter a new zip code.")

        return r

    return True


def bill_selection():
    if 'bill_id' in g.request_params.keys():
        return True

    r = twiml.Response()
    r.redirect(url_for('.bill_search'))
    return r


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


def load_members_for(zipcode):
    legislators = data.legislators_for_zip(zipcode)
    write_context('legislators', legislators)
    return legislators


def load_member_for(bioguide):
    legislator = data.legislator_by_bioguide(bioguide)
    write_context('legislator', legislator)
    return legislator


# def parent_url_for(current):
#     from calloncongress.voice.menu import MENU
#     parent = MENU.get(current).get('parent', 'main')
#     try:
#         if parent.func_name == 'referrer':
#             try:
#                 parent = parent_url_for(g.referrer)
#             except AttributeError:
#                 parent = 'main'
#     except AttributeError:
#         pass

#     return url_for(MENU.get(parent).get('route'))


def handle_selection(response, **kwargs):
    from calloncongress.voice.menu import MENU
    params = kwargs.get('params', {})
    try:
        sel = int(kwargs['selection'])
        menu = MENU[kwargs['menu']]

        if sel == 9:
            parent_menu = MENU[menu['parent']]
            response.redirect(url_for(parent_menu['route']))
            return response

        choice = [choice['action'] for choice in menu['choices'] if choice['key'] == sel][0]
        response.redirect(url_for(choice, **params))
        return response
    except:
        response.say('Sorry, an error occurred.')
        try:
            response.redirect(url_for(MENU[kwargs['menu']]['route']))
            return response
        except:
            pass

    response.redirect(url_for('.index'))
    return response


def next_action(response, **kwargs):
    keys = g.request_params.keys()
    if 'next_url' in keys:
        response.redirect(g.request_params.get('next_url'))
    elif 'default' in keys:
        response.redirect(g.request_params.get('default'))

    response.redirect(url_for('.index'))
