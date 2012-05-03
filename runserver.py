#!/usr/bin/env python
import os

from flask import send_from_directory
from calloncongress import app, settings

PWD = os.path.abspath(os.path.dirname(__file__))


@app.route('/audio/<path:filename>')
def download_file(filename):
    return send_from_directory(os.path.join(PWD, 'audio'), filename)

app.run(debug=settings.DEBUG, host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
