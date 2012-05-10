from flask import Blueprint, g, request, redirect, url_for
from dateutil.parser import parse as dateparse
from twilio import twiml

from calloncongress import data, logger, settings
from calloncongress.helpers import read_context, write_context, get_lang, get_zip, digitless_url
from calloncongress.decorators import twilioify, validate_before
from calloncongress.voice.menu import MENU
from calloncongress.voice.helpers import *

voice = Blueprint('voice', __name__)


@voice.route("/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def index():
    """Handles an inbound call. This is the default route, which directs initial setup items.
    """

    r = twiml.Response()
    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='main', selection=g.request_params['Digits'])

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""To begin, select from the following:
                  Press 1 to find your member of congress.
                  Press 2 to search U.S. House and Senate bills.
                  Press 3 to receive voter information.
                  Press 4 to learn more about the Sunlight Foundation and this service.
                  At any time during this call, you can press 9 to return to the
                  previous menu.""")

    return r


@voice.route("/members/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, zipcode_selection)
def members():
    """Meta-route to make sure legislators can be loaded before selecting by bioguide.
    """
    r = twiml.Response()
    return next_action(r, default=url_for('.member'))


@voice.route("/member/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bioguide_selection)
def member():
    """Menu for a specific member of congress"""

    r = twiml.Response()
    bioguide = g.request_params['bioguide_id']
    legislator = read_context('legislator', load_member_for(bioguide))
    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='member', selection=g.request_params['Digits'], params={'bioguide_id': bioguide})

    r.say(MENU['member']['name'] % legislator['fullname'])
    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT, action=url_for('.member', bioguide_id=bioguide)) as rg:
        rg.say("""Press 1 to hear a short biography.
                  Press 2 for a list of top campaign donors.
                  Press 3 for recent votes in congress.
                  Press 4 to call this representative's Capitol Hill office.
                  To return to the previous menu, press 9.""")

    return r


@voice.route("/member/bio/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bioguide_selection)
def member_bio():
    """Biography for a specific member of congress"""

    r = twiml.Response()
    bioguide = g.request_params['bioguide_id']
    legislator = read_context('legislator', load_member_for(bioguide))
    r.say(data.legislator_bio(legislator))

    return next_action(r, default=url_for('.member', bioguide_id=bioguide))


@voice.route("/member/donors/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bioguide_selection)
def member_donors():
    """Top campaign donors for a member of congress"""

    r = twiml.Response()
    bioguide = g.request_params['bioguide_id']
    legislator = read_context('legislator', load_member_for(bioguide))
    contribs = data.top_contributors(legislator)
    script = " ".join("%(name)s contributed $%(total_amount)s.\n" % c for c in contribs)
    r.say(script)

    return next_action(r, default=url_for('.member', bioguide_id=bioguide))


@voice.route("/member/votes/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bioguide_selection)
def member_votes():
    """Recent votes by a member of congress"""

    r = twiml.Response()
    bioguide = g.request_params['bioguide_id']
    legislator = read_context('legislator', load_member_for(bioguide))
    votes = data.recent_votes(legislator)
    script = " ".join("On %(question)s. Voted %(voted)s. . The bill %(result)s.\t" % v for v in votes)
    r.say("%s. %s" % (legislator['fullname'], script))

    return next_action(r, default=url_for('.member', bioguide_id=bioguide))


@voice.route("/member/call/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bioguide_selection)
def call_member():
    """Calls the DC office of a member of congress"""

    r = twiml.Response()
    bioguide = g.request_params['bioguide_id']
    legislator = read_context('legislator', load_member_for(bioguide))
    r.say("Connecting you to %s at %s" % (legislator['fullname'], legislator['phone']))
    with r.dial() as rd:
        rd.number(legislator['phone'])

    return r


@voice.route("/bills/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def bills():
    """Menu for interacting with bills"""

    r = twiml.Response()
    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='bills', selection=g.request_params['Digits'])

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""To learn about legislation in congress, please select from the following:
                  For upcoming bills in the news, press 1.
                  To search by bill number, press 2.""")

    return r


@voice.route("/bills/upcoming/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def upcoming_bills():
    """Bills on the floor this week"""

    r = twiml.Response()
    bills = data.upcoming_bills()[:9]
    if not len(bills):
        r.say('There are no bills in the news this week.')
    else:
        r.say('The following bills are coming up in the next few days:')
        for bill in bills:
            r.say('''On {date}, the {chamber} will discuss {bill_type} {bill_number},
                     {bill_title}. {bill_description}
                  '''.format(**bill['bill_context']))

    return next_action(r, default=url_for('.bills'))


@voice.route("/bills/search/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def search_bills():
    """Search route for bills"""

    r = twiml.Response()
    if 'Digits' in g.request_params.keys():
        # Go back to previous menu if 0
        if g.request_params['Digits'] == '0':
            r.redirect(url_for('.bills'))
            return r

        bills = data.bill_search(int(g.request_params['Digits']))
        if bills:
            query = {}
            if len(bills) == 1:
                query.update(bill_id=bills[0].bill_id)
                r.redirect(url_for('.bill', **query))
                return r

            write_context('bills', bills)
            with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT,
                          action=url_for('.select_bill', **query)) as rg:
                rg.say("Multiple bills were found. Please select from the following:")
                for i, bill in enumerate(bills):
                    bill['bill_context']['button'] = i + 1
                    rg.say("Press {button} for {bill_type} {bill_number}, {bill_title}".format(**bill['bill_context']))
                    rg.say("Press 0 to search for another number.")
            return r

        else:
            r.say('No bills were found matching that number.')

    with r.gather(timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""Enter the number of the bill to search for, followed by the #.
                  Exclude any prefixes such as H.R. or S.
                  To return to the previous menu, press 0, followed by the #.
               """)

    return r


@voice.route("/bills/select/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def select_bill():
    """Meta-route for handling multiple bills returned from search"""

    r = twiml.Response()
    query = {}
    bills = read_context('bills')
    if 'Digits' in g.request_params.keys() and bills:
        if g.request_params['Digits'] == '0':
            flush_context('bills')
            r.redirect(url_for('.search_bills'))
        try:
            sel = int(g.request_params['Digits'])
            bill = bills[sel - 1]
            query.update(bill_id=bill['bill_id'])
            r.redirect(url_for('.bill', **query))
            return r
        except:
            r.say("No bill matched your selection.")

    r.redirect(url_for('.search_bills', **query))
    return r


@voice.route("/bill/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bill_selection)
def bill():
    """Details about, and options for, a specific bill"""

    r = twiml.Response()
    bill = data.get_bill_by_id(g.request_params['bill_id'])
    if not bill:
        r.say("No bill was found matching %s" % g.request_params['bill_id'])
        r.redirect(url_for('.bills'))
        return r

    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='bill', selection=g.request_params['Digits'],
                                params={'bill_id': bill['bill_id']})

    script = "Ask someone what to say about %s" % bill['bill_id']
    r.say(script)
    if 'next_url' in g.request_params.keys():
        r.redirect(g.request_params['next_url'])
        return r

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""To get SMS updates about this bill on your mobile phone, press 1.
                  To search for another bill, press 2.
                  To return to the previous menu, press 9.
                  To return to the main menu, press 0.""")

    return r


@voice.route("/bill/subscribe", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bill_selection)
def subscribe_to_bill_updates():
    pass


@voice.route("/signup/", methods=['GET', 'POST'])
@twilioify
def signup():

    r = twiml.Response()

    selection = g.request_params.get('Digits', None)

    if selection == '1':

        g.db.smsSignups.insert({
            'url': g.call['from'],
            'timestamp': g.now,
        })

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-1.wav')

        r.redirect(url_for('.reps'))

    elif selection == '2':

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-2.wav')
        r.record(action=url_for('.message'), timeout=10, maxLength=120)
        r.redirect(url_for('.reps'))

    elif selection == '3':

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-3.wav')
        r.redirect(url_for('.reps'))

    else:
        r.redirect(url_for('.reps'))

    return r


@voice.route("/message/", methods=['GET', 'POST'])
@twilioify
def message():
    g.db.messages.insert({
        'url': g.request_params['RecordingUrl'],
        'timestamp': g.now,
    })
    r = twiml.Response()
    r.redirect(url_for('.reps'))
    return r


@voice.route("/test/", methods=['GET', 'POST'])
def test_method():
    r = data.recent_votes({'bioguide_id': 'V000128'})
    return str(r)


# def handle_selection(selection):
#     r = twiml.Response()

#     if selection == '1':

#         contribs = data.top_contributors(g.legislator)
#         script = " ".join("%(name)s contributed $%(total_amount)s.\n" % c for c in contribs)

#         r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1.wav')
#         r.say(script)

#         with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='2')) as rg:
#             rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1-out.wav')

#     elif selection == '2':

#         votes = data.recent_votes(g.legislator)

#         script = " ".join("On %(question)s. Voted %(voted)s. . The bill %(result)s.\t" % v for v in votes)

#         r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2.wav')
#         r.say("%s. %s" % (g.legislator['fullname'], script))

#         with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='3')) as rg:
#             rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2-out.wav')

#     elif selection == '3':

#         bio = data.legislator_bio(g.legislator)

#         r.say(bio or ('Sorry, we were unable to locate a biography for %s' % g.legislator['fullname']))

#         with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='4')) as rg:
#             rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/3-out.wav')

#     elif selection == '4':

#         comms = data.committees(g.legislator)

#         r.say(g.legislator['fullname'])
#         r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4.wav')
#         r.say(comms)

#         with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='5')) as rg:
#             rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4-out.wav')

#     elif selection == '5':

#         # connect to the member's office

#         r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-pre.wav')
#         r.say(g.legislator['fullname'])
#         r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-post.wav')

#         with r.dial() as rd:
#             rd.number(g.legislator['phone'])

#     elif selection == '9':

#         with r.gather(numDigits=1, timeout=10, action=url_for('.signup')) as rg:
#             rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9.wav')

#     elif selection == '0':
#         r.redirect(url_for('.zipcode'))

#     else:
#         r.say("I'm sorry, I don't recognize that selection. I will read you the options again.")
#         r.redirect(url_for('.reps'))

#     return r
