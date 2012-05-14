import re

from flask import Blueprint, g, request, url_for
from twilio import twiml

from calloncongress import data, settings
from calloncongress.helpers import read_context, write_context, get_zip
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
    if g.request_params.get('Digits') == '0':
        r.redirect(url_for('.members'))
        return r

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
                  To search by bill number, press 2.
                  To return to the previous menu, press 9.""")

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
        if g.request_params['Digits'] == '3':
            pass
        else:
            return handle_selection(r, menu='bill', selection=g.request_params['Digits'],
                                    params={'bill_id': bill['bill_id']})

    ctx = bill['bill_context']

    if len(bill.get('summary', '')) > 800 and not 'Digits' in g.request_params:
        with r.gather(numDigits=1, timeout=2) as rg:
            words = bill['summary'].split()
            rg.say("This bill's summary is %d words. Press 3 now to hear the long version, including the summary." %
                len(words))

    r.say("{bill_type} {bill_number}: {bill_title}".format(**ctx))
    if bill.get('summary') and g.request_params.get('Digits') == '3':
        r.say(bill['summary'])
    if ctx.get('sponsor'):
        r.say(ctx['sponsor'])
    cosponsors = ctx.get('cosponsors')
    if cosponsors:
        if len(bill.get('cosponsor_ids', [])) > 8:
            r.say('This bill has %d cosponsors.' % len(cosponsors))
        else:
            r.say(ctx['cosponsors'])
    if ctx.get('bill_status'):
        r.say(ctx['bill_status'])

    if 'next_url' in g.request_params.keys():
        r.redirect(g.request_params['next_url'])
        return r

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""To get SMS updates about this bill on your mobile phone, press 1.
                  To search for another bill, press 2.
                  To return to the previous menu, press 9.
                  To return to the main menu, press 0.""")

    return r


@voice.route("/bill/subscribe/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, bill_selection)
def subscribe_to_bill_updates():
    pass


@voice.route("/about/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def about():
    r = twiml.Response()
    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='about', selection=g.request_params['Digits'])

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""Thank you for using Call on Congress.
                  To learn more about the Sunlight Foundation, press 1.
                  To sign up for SMS Updates from the Sunlight Foundation, press 2.
                  To leave feedback about Call on Congress, press 3.""")

    return r


@voice.route("/voting/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, zipcode_selection)
def voting():
    r = twiml.Response()
    zipcode = get_zip()
    offices = data.election_offices_for_zip(zipcode)

    if not len(offices):
        r.say("""We're sorry, no offices were found for that zip code.""")
        flush_context('zipcode')
        r.redirect(url_for('.voting'))
        return r

    if 'Digits' in g.request_params.keys():
        return handle_selection(r, menu='voting', selection=g.request_params['Digits'])

    with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT) as rg:
        rg.say("""Voter information, including polling place locations
                  and how to register to vote, is available from:""")
        # TODO: Fix this when the new endpoint is ready
        office = offices[0]
        if office.get('authority_name'):
            rg.say(office['authority_name'])
        if office.get('street'):
            rg.say("Street address: %s, %s %s" % (office['street'], office['city'], office['state']))
        if office.get('mailing_street'):
            rg.say("Mailing address: %s" % office['mailing_street'])
        if office.get('phone'):
            rg.say("Telephone number: %s" % office['phone'])
            rg.say("Press 1 to call your election office.")
        rg.say("""Press 2 to repeat this information.
                  To return to the previous menu, press 9.""")
    return r


@voice.route("/voting/call/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, zipcode_selection)
def call_election_office():
    r = twiml.Response()
    zipcode = get_zip()
    offices = data.election_offices_for_zip(zipcode)
    if not len(offices):
        r.redirect('.voting')
        return r

    office = offices[0]
    if office.get('phone'):
        r.say("Connecting you to your election office at %s" % office['phone'])
        with r.dial() as rd:
            rd.number(office['phone'])
    else:
        r.say("We're sorry, no phone number is available for this office.")
        flush_context('zipcode')
        return next_action(default=url_for('.voting'))

    return r

@voice.route("/about/sunlight/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def about_sunlight():
    r = twiml.Response()
    r.say("""The Sunlight Foundation is a non-partisan, non-profit that
             use cutting-edge technology and ideas to make government
             transparent and accountable. We are committed to improving
             access to government information by making it available online
             to the public and by creating new tools to enable individuals
             and communities to better access information and put it to use.

             Learn more by visiting sunlight foundation dot com or by
             calling 202-742-1520""")

    return next_action(r, default=url_for('.about'))


@voice.route("/about/signup/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def signup():
    r = twiml.Response()
    number = None
    if 'Digits' in g.request_params.keys():
        digits = g.request_params['Digits']
        if digits == '1':
            number = g.call['from']
        elif len(digits) == 10:
            number = '+1' + digits
        else:
            r.say('That number is invalid.')

    if number:
        g.db.smsSignups.insert({
            'url': g.call['from'],
            'timestamp': g.now,
        })
        r.say('Thank you for signing up.')
        if not 'next_url' in g.request_params.keys():
            r.say('You will now be returned to the main menu.')
    else:
        with r.gather(timeout=settings.INPUT_TIMEOUT) as rg:
            rg.say("""To subscribe with the number you've called from, press 1, followed by the #.
                     To subscribe with a different number, enter the 10 digit number now, followed by the #.
                     To return to the previous menu, enter 0, followed by the #.""")

        return r

    return next_action(r, default=url_for('.index'))


@voice.route("/about/feedback/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection)
def feedback():
    r = twiml.Response()
    if 'RecordingUrl' in g.request_params.keys():
        g.db.messages.insert({
            'url': g.request_params['RecordingUrl'],
            'timestamp': g.now,
        })
        if not 'next_url' in g.request_params.keys():
            r.say("Thank you for your feedback. You will now be returned to the main menu.")
    else:
        r.say("""To leave feedback about Call on Congress or to contact the
                 Sunlight Foundation, please leave a message at the tone. Press the # when finished.""")
        r.record(timeout=10, maxLength=120)
        return r

    return next_action(r, default=url_for('.index'))


@voice.route("/test/", methods=['GET', 'POST'])
def test_method():
    r = data.recent_votes({'bioguide_id': 'V000128'})
    return str(r)
