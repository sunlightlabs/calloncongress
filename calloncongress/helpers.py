import urllib
import re

from flask import g, request

TITLES = {
    'rep': 'Representative',
    'sen': 'Senator',
}
PARTIES = {
    'r': 'Republican',
    'd': 'Democrat',
    'i': 'Independent',
}
STATES = {
    'al': 'Alabama',
    'ak': 'Alaska',
    'az': 'Arizona',
    'ar': 'Arkansas',
    'ca': 'California',
    'co': 'Colorado',
    'ct': 'Connecticut',
    'de': 'Delaware',
    'fl': 'Florida',
    'ga': 'Georgia',
    'hi': 'Hawaii',
    'id': 'Idaho',
    'il': 'Illinois',
    'in': 'Indiana',
    'ia': 'Iowa',
    'ks': 'Kansas',
    'ky': 'Kentucky',
    'la': 'Louisiana',
    'me': 'Maine',
    'md': 'Maryland',
    'ma': 'Massachussetts',
    'mi': 'Michigan',
    'mn': 'Minnesota',
    'ms': 'Mississippi',
    'mo': 'Missouri',
    'mt': 'Montana',
    'ne': 'Nebraska',
    'nv': 'Nevada',
    'nh': 'New Hampshire',
    'nj': 'New Jersey',
    'nm': 'New Mexico',
    'ny': 'New York',
    'nc': 'North Carolina',
    'nd': 'North Dakota',
    'oh': 'Ohio',
    'ok': 'Oklahoma',
    'or': 'Oregon',
    'pa': 'Pennsylvania',
    'ri': 'Rhode Island',
    'sc': 'South Carolina',
    'sd': 'South Dakota',
    'tn': 'Tennessee',
    'tx': 'Texas',
    'ut': 'Utah',
    'vt': 'Vermont',
    'va': 'Virginia',
    'wa': 'Washington',
    'wv': 'West Virginia',
    'wi': 'Wisconsin',
    'wy': 'Wyoming',
    'dc': 'District of Columbia',
    'as': 'American Samoa',
    'gu': 'Guam',
    'mp': 'Northern Mariana Islands',
    'pr': 'Puerto Rico',
    'vi': 'U.S. Virgin Islands',
    'fm': 'Federated States of Micronesia',
    'mh': 'Marshall Islands',
    'pw': 'Palau',
}
BILL_TYPES = {
    'hr': 'House Bill',
    'hres': 'House Resolution',
    'hjres': 'House Joint Resolution',
    'hcres': 'House Concurrent Resolution',
    's': 'Senate Bill',
    'sres': 'Senate Resolution',
    'sjres': 'Senate Joint Resolution',
    'scres': 'Senate Concurrent Resolution',
}


def bill_type_for(abbr):
    abbr = re.split(r'([a-zA-Z.\-]*)', abbr)[1].lower().replace('.', '')
    return BILL_TYPES.get(abbr)


def party_for(abbr):
    return PARTIES.get(abbr.lower(), abbr)


def rep_title_for(abbr):
    return TITLES.get(abbr.lower(), 'Representative')


def state_for(abbr):
    return STATES.get(abbr.lower())


def bill_number_for(abbr):
    try:
        return re.split(r'([a-zA-Z.\-]*)', abbr)[2]
    except:
        return None


def digitless_querystring():
    querydict = request.values.to_dict()
    try:
        querydict = delattr(querydict, 'Digits')
    except AttributeError:
        pass

    return urllib.urlencode(querydict)


def digitless_url():
    return "%s?%s" % (request.path, digitless_querystring())


def log_redirect_url():
    write_context('redirect_to', "%s?%s" % (request.path, digitless_querystring()))


def reset_redirect_url():
    flush_context('redirect_to')


def read_context(key, default=None):
    try:
        return g.call['context'][key]
    except:
        return default


def write_context(key, value):
    try:
        g.call['context'][key] = value
        return True
    except:
        return False


def flush_context(key):
    try:
        del g.call['context'][key]
        return True
    except:
        return False


def get_lang(**kwargs):
    return read_context('language', kwargs.get('default', None))


def get_zip():
    return read_context('zipcode')
