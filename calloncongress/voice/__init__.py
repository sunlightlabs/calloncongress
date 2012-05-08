from flask import Blueprint, g, request, url_for
from dateutil.parser import parse as dateparse
from twilio import twiml

from calloncongress import data, logger, settings
from calloncongress.helpers import read_context, write_context, get_lang, get_zip
from calloncongress.decorators import twilioify, validate_before
from calloncongress.voice.menu import MENU
from calloncongress.voice.helpers import *

voice = Blueprint('voice', __name__)


### Voice Routes: Non Twimlet-compatible ###
@voice.route("/", methods=['GET', 'POST'])
@twilioify
@validate_before(language_selection, zipcode_selection)
def index():
    """ Handles an inbound call. This is the default route, which directs initial setup items.
    """

    r = twiml.Response()
    zipcode = get_zip()
    legislators = data.legislators_for_zip(zipcode)
    if legislators:
        if len(legislators) > 3:
            r.say("""Since your zip code covers more than one congressional district,
                     you will be provided with a list of all possible legislators that
                     may represent you. Please select from the following names:""")
        else:
            r.say("""We identified your representatives in Congress. Please select from
                     the following names:""")

        with r.gather(numDigits=1, timeout=settings.INPUT_TIMEOUT, action=url_for('.reps')) as rg:
            options = [(l['fullname'], l['bioguide_id']) for l in legislators]
            script = " ".join("Press %i for %s." % (index + 1, o[0]) for index, o in enumerate(options))
            script += " Press 0 to enter a new zipcode."
            rg.say(script)
    else:
        r.say("I'm sorry, we weren't able to locate any representatives for %s." % (" ".join(zipcode),))
        with r.gather(numDigits=5, timeout=settings.INPUT_TIMEOUT, action=url_for('.zipcode')) as rg:
            rg.say("Please try again or enter a new zip code.")

    return r


@voice.route("/reps/", methods=['GET', 'POST'])
@twilioify
def reps():
    r = twiml.Response()
    if 'Digits' in request.values:
        digits = request.values.get('Digits', None)
        if digits == '0':
            r.redirect(url_for('.index'))
            return r  # shortcut the process and start over
        else:
            selection = int(digits) - 1
            legislator = data.legislators_for_zip(g.zipcode)[selection]
            write_context('legislator', legislator)
    else:
        legislator = g.legislator

    r.say("""Please select one of the following options for information on:""")
    r.say('%s' % legislator['fullname'])
    with r.gather(numDigits=1, timeout=30, action=url_for('.rep')) as rg:
        rg.say("""For a list of top campaign donors, press 1.
                  For recent votes, press 2.
                  For a short biography, press 3.
                  To list the representative's committees, press 4.
                  To forward this call to the representative's Capitol Hill office, press 5.
                  To find out how you can join the Sunlight Foundation's efforts to promote
                    transparency in government, press 9.
                  To go back to the list of representatives, press 0.
               """)

    return r


@voice.route("/next/<next_selection>/", methods=['GET', 'POST'])
@twilioify
def next(next_selection):
    selection = request.values.get('Digits', None)
    if selection == '1':
        return handle_selection(next_selection)
    else:
        r = twiml.Response()
        r.redirect(url_for('.reps'))
        return r


### Routes, Twimlet-like ###
@voice.route("/rep/", methods=['GET', 'POST'])
@twilioify
def rep():
    selection = request.values.get('Digits', None)
    return handle_selection(selection)


@voice.route("/signup/", methods=['GET', 'POST'])
@twilioify
def signup():

    r = twiml.Response()

    selection = request.values.get('Digits', None)

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
        'url': request.values['RecordingUrl'],
        'timestamp': g.now,
    })
    r = twiml.Response()
    r.redirect(url_for('.reps'))
    return r


@voice.route("/upcoming-bills/", methods=['GET', 'POST'])
@twilioify
def upcoming_bills():
    r = twiml.Response()
    bills = data.upcoming_bills()[:9]
    if not len(bills):
        r.say('There are no bills in the news this week.')
    else:
        r.say('The following bills are coming up in the next few days:')
        for bill in bills:
            try:
                ctx = bill.context
            except AttributeError:
                ctx = []
            bill_context = {
                'date': dateparse(bill.legislative_day).strftime('%B %e'),
                'chamber': bill.chamber,
                'bill_type': bill_type(bill.bill_id),
                'bill_number': bill.bill['number'],
                'bill_title': bill.bill['official_title'].encode('ascii', 'ignore'),
                'bill_description': '\n'.join(ctx).encode('ascii', 'ignore')
            }
            r.say('''On {date}, the {chamber} will discuss {bill_type} {bill_number},
                     {bill_title}. {bill_description}
                  '''.format(**bill_context))

    r.redirect(url_for('.reps'))
    return r


@voice.route("/test/", methods=['GET', 'POST'])
def test_method():
    r = data.recent_votes({'bioguide_id': 'V000128'})
    return str(r)


def handle_selection(selection):
    r = twiml.Response()

    if selection == '1':

        contribs = data.top_contributors(g.legislator)
        script = " ".join("%(name)s contributed $%(total_amount)s.\n" % c for c in contribs)

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1.wav')
        r.say(script)

        with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='2')) as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1-out.wav')

    elif selection == '2':

        votes = data.recent_votes(g.legislator)

        script = " ".join("On %(question)s. Voted %(voted)s. . The bill %(result)s.\t" % v for v in votes)

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2.wav')
        r.say("%s. %s" % (g.legislator['fullname'], script))

        with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='3')) as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2-out.wav')

    elif selection == '3':

        bio = data.legislator_bio(g.legislator)

        r.say(bio or ('Sorry, we were unable to locate a biography for %s' % g.legislator['fullname']))

        with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='4')) as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/3-out.wav')

    elif selection == '4':

        comms = data.committees(g.legislator)

        r.say(g.legislator['fullname'])
        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4.wav')
        r.say(comms)

        with r.gather(numDigits=1, timeout=10, action=url_for('.next', next_selection='5')) as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4-out.wav')

    elif selection == '5':

        # connect to the member's office

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-pre.wav')
        r.say(g.legislator['fullname'])
        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-post.wav')

        with r.dial() as rd:
            rd.number(g.legislator['phone'])

    elif selection == '9':

        with r.gather(numDigits=1, timeout=10, action=url_for('.signup')) as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9.wav')

    elif selection == '0':
        r.redirect(url_for('.zipcode'))

    else:
        r.say("I'm sorry, I don't recognize that selection. I will read you the options again.")
        r.redirect(url_for('.reps'))

    return r
