import re

from flask import Blueprint, g, request, url_for
from dateutil.parser import parse as dateparse
from twilio import twiml

from calloncongress import data, logger
from calloncongress.utils import twilioify

voice = Blueprint('voice', __name__)


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


def handle_selection(selection):
    r = twiml.Response()

    if selection == '1':

        contribs = data.top_contributors(g.legislator)
        script = " ".join("%(name)s contributed $%(total_amount)s.\n" % c for c in contribs)

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1.wav')
        r.say(script)

        with r.gather(numDigits=1, timeout=10, action='/next/2') as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/1-out.wav')

    elif selection == '2':

        votes = data.recent_votes(g.legislator)

        script = " ".join("On %(question)s. Voted %(voted)s. . The bill %(result)s.\t" % v for v in votes)

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2.wav')
        r.say("%s. %s" % (g.legislator['fullname'], script))

        with r.gather(numDigits=1, timeout=10, action='/next/3') as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/2-out.wav')

    elif selection == '3':

        bio = data.legislator_bio(g.legislator)

        r.say(bio or ('Sorry, we were unable to locate a biography for %s' % g.legislator['fullname']))

        with r.gather(numDigits=1, timeout=10, action='/next/4') as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/3-out.wav')

    elif selection == '4':

        comms = data.committees(g.legislator)

        r.say(g.legislator['fullname'])
        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4.wav')
        r.say(comms)

        with r.gather(numDigits=1, timeout=10, action='/next/5') as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/4-out.wav')

    elif selection == '5':

        # connect to the member's office

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-pre.wav')
        r.say(g.legislator['fullname'])
        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/5-post.wav')

        with r.dial() as rd:
            rd.number(g.legislator['phone'])

    elif selection == '9':

        with r.gather(numDigits=1, timeout=10, action='/signup') as rg:
            rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9.wav')

    elif selection == '0':
        r.redirect(url_for('.zipcode'))

    else:
        r.say("I'm sorry, I don't recognize that selection. I will read you the options again.")
        r.redirect(url_for('.reps'))

    return r


@voice.route("/", methods=['GET', 'POST'])
@twilioify
def index():

    r = twiml.Response()

    if request.method == 'POST':

        options = {
            '1': 'en',
            '2': 'es',
        }

        sel = request.form.get('Digits')
        g.call['language'] = options.get(sel, 'en')

        r.redirect(url_for('.welcome'))

    else:
        with r.gather(numDigits=1, timeout=10, action=url_for('.index'), method='POST') as rg:
            rg.say('Welcome to Call on Congress. Press 1 to continue in English.', language='en')
            rg.say('Presione 2 para continuar en espanol.', language='es')

    return str(r)


@voice.route("/welcome/", methods=['GET', 'POST'])
@twilioify
def welcome():
    """ Initiate a new call. Welcomes the user and prompts for zipcode.
    """

    r = twiml.Response()
    #r.say("Welcome to CapitolPhone brought to you by the Sunlight Foundation.")
    #with r.gather(numDigits=5, timeout=10, action='/zipcode') as rg:
        #rg.say("In order to locate your representatives, please enter your five digit zipcode now.")

    r.play("http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/intro.wav")
    r.gather(numDigits=5, timeout=10, action='/zipcode')

    return r


@voice.route("/zipcode/", methods=['POST'])
@twilioify
def zipcode():
    """ Handles POSTed zipcode and prompts for legislator selection.
    """

    zipcode = request.form.get('Digits', g.zipcode)
    r = twiml.Response()

    if zipcode == '00000':

        r.say("""
            Welcome to movie phone.
            You seem like the type of person that would enjoy The Twilight Saga: Breaking Dawn Part 1.
            The best showings are during the day, but you'll be stuck in middle school.
            Ha ha ha. Loser.
        """)

    else:

        g.call['context']['zipcode'] = zipcode

        legislators = data.legislators_for_zip(zipcode)

        if legislators:

            options = [(l['fullname'], l['bioguide_id']) for l in legislators]
            script = " ".join("Press %i for %s." % (index + 1, o[0]) for index, o in enumerate(options))
            script += " Press 0 to enter a new zipcode."

            if len(legislators) > 3:
                r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/selectlegalt.wav')
            else:
                r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/selectleg.wav')

            with r.gather(numDigits=1, timeout=10, action='/reps') as rg:
                rg.say(script)

        else:

            r.say("I'm sorry, I wasn't able to locate any representatives for %s." % (" ".join(zipcode),))
            with r.gather(numDigits=5, timeout=10, action='/zipcode') as rg:
                rg.say("Please try again or enter a new zipcode.")

    return r


@voice.route("/reps/", methods=['POST'])
@twilioify
def reps():
    r = twiml.Response()

    if 'Digits' in request.form:

        digits = request.form.get('Digits', None)

        if digits == '0':

            r.redirect(url_for('.index'))
            return r  # shortcut the process and start over

        else:

            selection = int(digits) - 1
            legislator = data.legislators_for_zip(g.zipcode)[selection]
            g.call['context']['legislator'] = legislator

    else:
        legislator = g.legislator

    r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/mainmenu-intro.wav')
    r.say('%s' % legislator['fullname'])
    with r.gather(numDigits=1, timeout=30, action='/rep') as rg:
        rg.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/mainmenu.wav')

    return r


@voice.route("/rep/", methods=['POST'])
@twilioify
def rep():
    selection = request.form.get('Digits', None)
    return handle_selection(selection)


@voice.route("/next/<next_selection>/", methods=['POST'])
@twilioify
def next(next_selection):
    selection = request.form.get('Digits', None)
    if selection == '1':
        return handle_selection(next_selection)
    else:
        r = twiml.Response()
        r.redirect(url_for('.reps'))
        return r


@voice.route("/signup/", methods=['POST'])
@twilioify
def signup():

    r = twiml.Response()

    selection = request.form.get('Digits', None)

    if selection == '1':

        g.db.smsSignups.insert({
            'url': g.call['from'],
            'timestamp': g.now,
        })

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-1.wav')

        r.redirect(url_for('.reps'))

    elif selection == '2':

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-2.wav')
        r.record(action='/message', timeout=10, maxLength=120)
        r.redirect(url_for('.reps'))

    elif selection == '3':

        r.play('http://assets.sunlightfoundation.com/projects/transparencyconnect/audio/9-3.wav')
        r.redirect(url_for('.reps'))

    else:
        r.redirect(url_for('.reps'))

    return r


@voice.route("/message/", methods=['POST'])
@twilioify
def message():
    g.db.messages.insert({
        'url': request.form['RecordingUrl'],
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

    return r


@voice.route("/test/", methods=['GET'])
def test_method():
    r = data.recent_votes({'bioguide_id': 'V000128'})
    return str(r)
