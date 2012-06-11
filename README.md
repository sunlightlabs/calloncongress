# Call on Congress

Call on Congress is a free telephone service that helps you learn more about what Congress is doing. Find out how your representatives are voting on bills and raising campaign money. You can also be connected with your lawmakers’ Capitol Hill offices or get details on where to vote on Election Day.

## Installation

Call on Congress targets Heroku, but can be run on other servers using gunicorn. To run:

* Clone the repo
* `pip install -r requirements.txt`
* `cp calloncongress/local_settings.example.py calloncongress/local_settings.py`
* Add your keys
* `foreman start` (if you have foreman installed) or `./runserver.py` (will only use a single thread)

### Keys

You will need API keys and account tokens for the following services:

* [Twilio](http://www.twilio.com/)
* [Google Translate](https://developers.google.com/translate/)
* [Sunlight API](http://services.sunlightlabs.com/)

### Twilio

Log in to your Twilio account and create or edit a phone number. Set the *Voice Request URL* field to:

    http://<your domain>/voice/

Though either GET or POST will work, we recommend setting the initial request type to GET. Save your changes and you are ready to go!

## Languages

Call on Congress supports a default language set of English, Spanish, and Esperanto. To add a new language:

1. Add the language code and name to the LANGUAGES dict in `calloncongress/settings.py`.
1. Check the languages supported by the Twilio [Say command](http://www.twilio.com/docs/api/twiml/say). If your language is not supported, select the closest approximation and add it to the ACCENT_MAP dict in `calloncongress/twiml_monkeypatch.py`.
1. `data/script.json` maps lines in the spoken script to a pre-generated file name. Set your audio files to the names specified in the mapping file and place them in the following directory:

        static/audio/<language code>/