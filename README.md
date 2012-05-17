Call on Congress
================

A Twilio application for connecting to congressional data via telephone.


Installation
------------

Call on Congress targets Heroku, but can be run on other servers using gunicorn. To run:

* Clone the repo
* `pip install -r requirements.txt`
* `cp calloncongress/local_settings.example.py calloncongress/local_settings.py`
* Add your keys
* `foreman start` (if you have foreman installed) or `./runserver.py` (will only use a single thread)
