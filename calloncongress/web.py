# This Python file uses the following encoding: utf-8
from flask import Blueprint, render_template, request
from twilio import twiml

from calloncongress.utils import twilioify

web = Blueprint('web', __name__, template_folder='templates')


@web.route('/')
def index():
    return render_template('index.html')


@web.route('/voice')
@twilioify
def welcome():

    r = twiml.Response()

    if request.method == 'POST':

        options = {
            '1': '/voice/en',
            '2': '/voice/es',
        }

        sel = request.form.get('Digits')
        r.redirect(options.get(sel, '/voice'))

    else:
        with r.gather(numDigits=1, timeout=10, action='/voice', method='POST') as rg:
            rg.say('Welcome to Call on Congress. Press 1 to continue in English.', language='en')
            rg.say('Presione 2 para continuar en espanol.', language='es')

    return str(r)
