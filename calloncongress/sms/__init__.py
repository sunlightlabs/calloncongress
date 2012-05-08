from flask import Blueprint
from calloncongress.utils import twilioify

sms = Blueprint('sms', __name__)


@twilioify
@sms.route('/')
def index():
    pass
