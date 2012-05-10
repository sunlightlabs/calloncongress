import re

from twilio import twiml
from flask import g, request, redirect, url_for
from calloncongress import settings, data
from calloncongress.helpers import digitless_url, read_context, write_context, flush_context, get_lang, get_zip


def language_selection():
    """Ensures a language has been selected before proceeding with call flow, by:
        - If a get param is sent, store it and return.
        - If the context already has a language, return.
        - If a language choice was passed back, pull it out of settings, store it and return.
        - If nothing was sent, prompt the user with available choices.
       This only needs to be set once during the life of a call.
    """

    # Twimlet-style params always override language settings
    if 'language' in g.request_params.keys():
        sel = g.request_params['language']
        try:
            sel = int(sel)
            write_context('language', settings.LANGUAGES[sel - 1][0])
        except ValueError:
            if sel in [lang[0] for lang in settings.LANGUAGES]:
                write_context('language', sel)

    # Internal app use
    if not get_lang():
        errors = []
        r = twiml.Response()

        # Collect and wipe digits if a choice was submitted
        if 'Digits' in g.request_params.keys():
            sel = int(g.request_params.get('Digits', 1))
            try:
                write_context('language', settings.LANGUAGES[sel - 1][0])
            except:
                errors.append('%d is not a valid selection, please try again.')

            del g.request_params['Digits']

        # Prompt and gather if language is not valid or no choice was submitted
        if not get_lang():
            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
                if not len(errors):
                    rg.say("""Welcome to Call on Congress, the Sunlight Foundation's
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
    """Ensures a zipcode has been selected before proceeding with call flow, by:
        - If a get param is sent, store it and return.
        - If the context already has a zipcode, return.
        - If a language choice was passed back, pull it out of settings, store it and return.
        - If nothing was sent, prompt the user with available choices.
       This only needs to be set once during the life of a call.
    """

    # Twimlet use
    if 'zipcode' in g.request_params.keys():
        write_context('zipcode', int(sel))

    # Internal app use
    if not get_zip():
        errors = []
        r = twiml.Response()

        # Collect and wipe digits if a choice was submitted
        if 'Digits' in g.request_params.keys():
            sel = g.request_params.get('Digits')
            if len(sel) == 5:
                write_context('zipcode', int(sel))
            else:
                errors.append('%s is not a valid zipcode, please try again.' % sel)

            del g.request_params['Digits']

        # Prompt and gather if zip is not valid or no choice was submitted
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
    """Ensures a Bioguide ID is present in request params before proceeding with call flow.
       This is not stored in the context, only passed in params. Logic as follows:
        - If a get param is sent, return.
        - If a list of possible legislators is stored in context, and a choice was passed,
            append the choice's Bioguide ID to params and return.
        - If no list of legislators is present in context, prompt for zipcode and load legislators,
            then prompt for a selection.
    """
    r = twiml.Response()

    # Handle twimlet-style params
    if 'bioguide_id' in g.request_params.keys():
        return True

    # If Digits = 9 or 0, we're going back
    if g.request_params.get('Digits') in ['9', '0']:
        return True

    # Make sure there's a legislators list in the call context.
    # If not, short-circuit to zip collection and repost to get legislator list
    # before prompting for a selection.
    legislators = read_context('legislators', [])
    if 'Digits' in g.request_params.keys() and len(legislators):
        sel = int(g.request_params['Digits'])
        del g.request_params['Digits']
        try:
            legislator = read_context('legislators')[sel - 1]
            g.request_params['bioguide_id'] = legislator['bioguide_id']

            return True
        except:
            r.say('%d is not a valid selection, please try again.' % sel)

    # If we don't have a bioguide, or legislators, or a zip selection,
    # skip this and get a zip code first.
    if not len(legislators) and not get_zip() and not 'Digits' in g.request_params.keys():
        return zipcode_selection()

    # If we do have a zip code selection, store it before trying to get legislators.
    if not len(legislators) and not get_zip():
        zipcode_selection()

    # If we have a zip and no legislators, load them.
    if not len(legislators):
        load_members_for(get_zip())
        legislators = read_context('legislators', [])

    # If there are legislators, prompt for a choice. If still nothing, fail and get a new zip.
    if len(legislators):
        with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
            if len(legislators) > 3:
                rg.say("""Since your zip code covers more than one congressional district,
                          you will be provided with a list of all possible legislators that
                          may represent you. Please select from the following names:""")
            else:
                rg.say("""We identified your representatives in Congress. Please select from
                          the following names:""")
            options = [(l['fullname'], l['bioguide_id']) for l in legislators]
            script = " ".join("Press %i for %s." % (index + 1, o[0]) for index, o in enumerate(options))
            script += " Press 0 to enter a new zipcode."
            rg.say(script)
    else:
        r.say("I'm sorry, we weren't able to locate any representatives for %s." % get_zip())
        flush_context('zipcode')
        try:
            del g.request_params['Digits']
        except:
            pass

    return r


def bill_selection():
    if 'bill_id' in g.request_params.keys():
        return True

    r = twiml.Response()
    r.redirect(url_for('.search_bills'))
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
    for legislator in read_context('legislators', []):
        if legislator['bioguide_id'] == bioguide:
            write_context('legislator', legislator)
            return legislator
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
    try:
        sel = int(kwargs['selection'])
        menu = MENU[kwargs['menu']]

        if sel == 9:
            parent_menu = MENU[menu['parent']]
            response.redirect(url_for(parent_menu['route']))
            return response

        choice = [choice for choice in menu['choices'] if choice['key'] == sel][0]
        params = kwargs.get('params', {})
        allowed_params = choice.get('params', [])
        for key, val in params.items():
            if key not in allowed_params:
                del params['key']

        response.redirect(url_for(choice['action'], **params))
        return response

    except Exception, e:
        response.say('Sorry, an error occurred: %s' % e)
        try:
            response.redirect(url_for(MENU[kwargs['menu']]['route']))
            return response
        except:
            pass

    response.redirect(url_for('.index'))
    return response


def next_action(response, **kwargs):
    if 'next_url' in g.request_params.keys():
        response.redirect(g.request_params['next_url'])
    elif 'default' in kwargs:
        response.redirect(kwargs['default'])
    else:
        response.redirect(url_for('.index'))

    return response
