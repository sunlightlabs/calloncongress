# This Python file uses the following encoding: utf-8
from flask import Blueprint, render_template

from calloncongress import logger

web = Blueprint('web', __name__, template_folder='templates')


@web.route('/')
def index():
    return render_template('index.html')
