import datetime
import json
import re
import urllib

from dateutil.parser import parse as dateparse
from flask import g
from influenceexplorer import InfluenceExplorer
import requests
import sunlight

from calloncongress import settings
from calloncongress.helpers import (bill_type_for, bill_number_for, state_for,
                                    rep_title_for, party_for)

sunlight.config.API_KEY = settings.SUNLIGHT_KEY
ie = InfluenceExplorer(settings.SUNLIGHT_KEY)


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
        results = sunlight.congress.locate_legislators_by_zip(zipcode)

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
    """ Finds and caches a legislator with the given bioguide id. """
    doc = g.db.legislatorByBioguideId.find_one({'bioguide_id': bioguide})

    if doc is None:
        try:
            legislator = _format_legislator(sunlight.congress.legislator(bioguide))
            g.db.legislatorByBioguideId.insert({
                'timestamp': g.now,
                'bioguide_id': bioguide,
                'legislator': legislator,
            })
        except sunlight.errors.SunlightException:
            legislator = None
    else:
        legislator = doc['legislator']

    return legislator


def _format_legislator(l):
    try:
        l = l.__dict__.copy()
    except AttributeError:
        pass
    l['short_title'] = l['title']
    l['title'] = rep_title_for(l['title'])
    l['fullname'] = "%s %s %s" % (l['title'],
                                  l.get('firstname') or l.get('first_name'),
                                  l.get('lastname') or l.get('last_name'))

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
    return metadata['metadata']['bio'].encode('ascii', 'xmlcharrefreplace')


def committee_iter(committees):
    for comm in committees:
        yield comm.name
        if comm.subcommittees:
            for subcomm in comm.subcommittees:
                yield subcomm.name


def committees(legislator):
    comms = sunlight.congress.committees(member_ids=g.legislator['bioguide_id'])
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

    result_keys = (('', 'passed'), ('was', 'rejected'), ('', 'failed'))
    data = json.loads(resp.content)['votes']
    for vote in data:
        voted = vote['voter_ids'][legislator['bioguide_id']]
        vote['voted'] = VOTES.get(voted, voted)
        vote['question'] = vote['question'].split(':')[-1].strip()
        if vote['question'].lower().startswith('on '):
            vote['question'] = vote['question'][3:]
        for key in result_keys:
            try:
                vote_result_index = vote['result'].lower().index(key[1])
                vote['result'] = "%s %s" % (key[0], vote['result'][vote_result_index:])
            except ValueError:
                continue
        del vote['voter_ids']

    return data


def upcoming_bills(window=settings.UPCOMING_BILL_DAYS):
    timeframe = [datetime.datetime.today(), datetime.datetime.today() + datetime.timedelta(days=window)]
    formatstr = '%Y-%m-%d'
    bills = sunlight.congress.upcoming_bills(
                                legislative_day__gte=timeframe[0].strftime(formatstr),
                                legislative_day__lte=timeframe[1].strftime(formatstr),
                                order='legislative_day__asc')

    return [_format_bill(bill) for bill in bills]


def bill_search(number=None):
    bills = sunlight.congress.bills(number=number, order='last_action_at__desc')[:8]
    return [_format_bill(bill) for bill in bills]


def get_bill_by_id(bill_id=None):
    try:
        return _format_bill(sunlight.congress.bills(bill_id=bill_id)[0])
    except IndexError:
        return None


def _format_bill(bill):
    bill = bill.__dict__.copy()
    btype = bill_type_for(bill['bill_id'])
    bnumber = bill.get('number') or bill_number_for(bill['bill_id'])
    bdate = bill.get('legislative_day') or bill.get('last_action_at')
    try:
        bdate = dateparse(bdate).strftime('%B %e')
    except:
        bdate = 'unknown date'
    title = (bill.get('popular_title') or
             bill.get('short_title') or
             bill.get('official_title') or '')
    ctx = bill.get('context', [])
    bill['summary'] = bill.get('summary') or ''
    bill_context = {
        'date': bdate,
        'chamber': bill['chamber'],
        'bill_type': btype,
        'bill_number': bnumber,
        'bill_title': title.encode('ascii', 'ignore'),
        'bill_description': '\n'.join(ctx).encode('ascii', 'ignore'),
    }
    if len(bill.get('actions', [])):
        bill_context.update(bill_status="%s on %s" % (bill['last_action'].get('text'),
                                                      dateparse(bill['last_action'].get('acted_at')).strftime('%B %e, %Y')))
    else:
        bill_context.update(bill_status='No known actions taken yet.')

    sponsor = bill.get('sponsor')
    if sponsor:
        bill_context.update(sponsor="Sponsored by: %s, %s, %s" % (_format_legislator(sponsor)['fullname'],
                                                                  party_for(sponsor['party']),
                                                                  state_for(sponsor['state'])))

    cosponsors = bill.get('cosponsors', [])
    if len(cosponsors):
        bill_context.update(cosponsors="Cosponsored by: %s" %
            ', '.join(["%s, %s, %s" % (_format_legislator(cs)['fullname'],
                                       party_for(cs['party']),
                                       state_for(cs['state'])) for cs in cosponsors]))

    bill.update(bill_context=bill_context)
    return bill


def election_offices_for_zip(zipcode):
    doc = g.db.electionOfficesByZipcode.find_one({'zipcode': zipcode})

    if doc is None:
        try:
            turbovote_url = "https://turbovote.org/api/clerk/%s?token=%s"
            offices = [_format_election_office(office) for office in json.loads(requests.get(turbovote_url % (zipcode, settings.TURBOVOTE_KEY)).content)['result']]
            doc = {
                'timestamp': g.now,
                'zipcode': zipcode,
                'offices': offices
            }
            if isinstance(doc['offices'], dict):
                doc['offices'] = [doc['offices']]
            g.db.electionOfficesByZipcode.insert(doc)
        except:
            return []

    return doc['offices']


def _format_election_office(office):
    if office.get('phone'):
        phone = re.sub(r'[^\d]+', '', office['phone'])
        office['phone'] = None
        try:
            if len(phone) == 11:
                office['phone'] = "%s-%s-%s" % (phone[1:4], phone[4:7], phone[7:11])
            elif len(phone) == 10:
                office['phone'] = "%s-%s-%s" % (phone[0:3], phone[3:6], phone[6:10])
        except:
            pass

    return office


def subscribe_to_bill_updates(**kwargs):
    from flask import request
    headers = {
        'X-Twilio-Signature': request.headers.get('X-Twilio-Signature', ''),
        'X-Twilio-Request-URI': request.url,
        'X-Twilio-Post-Body': urllib.urlencode(request.form),
    }
    params = kwargs
    r = requests.post('https://scout.sunlightfoundation.com/remote/subscribe/sms', data=params, headers=headers)
    if r.status_code == 200:
        return True
    else:
        return False
