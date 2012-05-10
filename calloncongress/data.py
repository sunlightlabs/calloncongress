import datetime
import  re

from dateutil.parser import parse as dateparse
from flask import g
from influenceexplorer import InfluenceExplorer
from sunlightapi import sunlight as sun
from realtimecongress import RTC as rtc
import json
import requests

from calloncongress import settings

TITLES = {
    'Rep': 'Representative',
    'Sen': 'Senator',
}

sun.apikey = settings.SUNLIGHT_KEY
ie = InfluenceExplorer(settings.SUNLIGHT_KEY)
rtc.apikey = settings.SUNLIGHT_KEY


def legislators_for_zip(zipcode):
    """ Find legislators that represent the specified zipcode.
        Results are cached in the datastore for faster lookup.
        If more than one member of the House represents a zipcode,
        both legislators will be returned.

        zipcode: the 5-digit zipcode to search
    """

    # attempt to find cached legislators
    doc = g.db.legislatorsByZipcode.find_one({'zipcode': zipcode})

    if doc is None:

        # load from Sunlight Congress API if not cached locally
        results = sun.legislators.allForZip(zipcode)

        # create a copy of the Legislator object dict
        legislators = [_format_legislator(r) for r in results]

        # sort the legislators by reverse title so Senators are listed
        # before members of the House
        legislators.sort(lambda x, y: -cmp(x['short_title'], y['short_title']))

        # save new zipcode results document
        g.db.legislatorsByZipcode.insert({
            'timestamp': g.now,
            'zipcode': zipcode,
            'legislators': legislators,
        })

    else:

        # get legislators from cache
        legislators = doc['legislators']

    return legislators


def legislator_by_bioguide(bioguide):
    doc = g.db.legislatorByBioguideId.find_one({'bioguide_id': bioguide})

    if doc is None:
        try:
            legislator = _format_legislator(sun.legislators.get(bioguide_id=bioguide))
            g.db.legislatorByBioguideId.insert({
                'timestamp': g.now,
                'bioguide_id': bioguide,
                'legislator': legislator,
            })
        except sun.SunlightApiError:
            legislator = None
    else:
        legislator = doc['legislator']

    return legislator


def _format_legislator(l):
    l = l.__dict__.copy()
    l['short_title'] = l['title']
    l['title'] = TITLES.get(l['title'], 'Representative')
    l['fullname'] = "%s %s %s" % (l['title'], l['firstname'], l['lastname'])

    return l


def resolve_entity_id(crp_id):
    """ Convert a CRP candidate ID into an IE entity ID.
        Cached locally for better performance.
    """

    doc = g.db.crpMapping.find_one({'crp_id': crp_id})

    if doc is None:
        entity_id = ie.entities.id_lookup("urn:crp:recipient", crp_id)[0]['id']
        g.db.crpMapping.insert({
            'crp_id': crp_id,
            'entity_id': entity_id,
        })
    else:
        entity_id = doc['entity_id']

    return entity_id


def top_contributors(legislator):
    entity_id = resolve_entity_id(legislator['crp_id'])
    contribs = ie.pol.contributors(entity_id, cycle='2012', limit=10)
    return contribs


def legislator_bio(legislator):
    entity_id = resolve_entity_id(legislator['crp_id'])
    metadata = ie.entities.metadata(entity_id)
    return metadata['metadata']['bio']


def committee_iter(committees):
    for comm in committees:
        yield comm.name
        if comm.subcommittees:
            for subcomm in comm.subcommittees:
                yield subcomm.name


def committees(legislator):
    comms = sun.committees.allForLegislator(g.legislator['bioguide_id'])
    names = " ".join("%s." % c for c in committee_iter(comms))
    return names


def recent_votes(legislator):

    VOTES = {
        'Yea': 'yes',
        'Nay': 'no',
    }

    url = "http://api.realtimecongress.org/api/v1/votes.json"

    voter_key = "voter_ids.%s" % legislator['bioguide_id']

    params = {
        'per_page': 5,
        'vote_type': 'passage',
        '%s__exists' % voter_key: True,
        'sections': "question,result,%s" % voter_key,
    }

    resp = requests.get(url, params=params, headers={'X-APIKEY': settings.SUNLIGHT_KEY})

    data = json.loads(resp.content)['votes']
    for vote in data:
        voted = vote['voter_ids'][legislator['bioguide_id']]
        vote['voted'] = VOTES.get(voted, voted)
        vote['question'] = vote['question'].split(':')[-1].strip()
        del vote['voter_ids']

    return data


def upcoming_bills(window=settings.UPCOMING_BILL_DAYS):
    timeframe = [datetime.datetime.today(), datetime.datetime.today() + datetime.timedelta(days=window)]
    formatstr = '%Y-%m-%d'
    bills = rtc.getUpcomingBills(legislative_day__gte=timeframe[0].strftime(formatstr),
                                 legislative_day__lte=timeframe[1].strftime(formatstr),
                                 order='legislative_day',
                                 sort='asc')

    return [_format_bill(bill) for bill in bills]


def bill_search(number=None):
    bills = rtc.getBills(number=number, order='last_action_at', sort='desc')[:8]
    return [_format_bill(bill) for bill in bills]


def get_bill_by_id(bill_id=None):
    try:
        return _format_bill(rtc.getBills(bill_id=bill_id)[0])
    except IndexError:
        return None


def _format_bill(bill):
    bill = bill.__dict__.copy()
    btype = bill_type(bill['bill_id'])
    bnumber = bill.get('number') or bill_number(bill['bill_id'])
    bdate = bill.get('legislative_day') or bill.get('last_action_at')
    try:
        bdate = bdate.strftime('%B %e')
    except:
        bdate = 'unknown date'
    title = (bill.get('popular_title') or
             bill.get('short_title') or
             bill.get('official_title') or '')
    ctx = bill.get('context', [])
    bill_context = {
        'date': bdate,
        'chamber': bill['chamber'],
        'bill_type': btype,
        'bill_number': bnumber,
        'bill_title': title.encode('ascii', 'ignore'),
        'bill_description': '\n'.join(ctx).encode('ascii', 'ignore')
    }
    bill.update(bill_context=bill_context)
    return bill


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


def bill_number(abbr):
    return re.split(r'([a-zA-Z.\-]*)', abbr)[2]
