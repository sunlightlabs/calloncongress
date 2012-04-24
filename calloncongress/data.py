from flask import g
from influenceexplorer import InfluenceExplorer
from sunlightapi import sunlight
import json
import requests

from calloncongress import settings

TITLES = {
    'Rep': 'Representative',
    'Sen': 'Senator',
}

sunlight.apikey = settings.SUNLIGHT_KEY
ie = InfluenceExplorer(settings.SUNLIGHT_KEY)


def load_call(sid, params):
    """ Loads a call from the datastore or creates a new one if one
        does not exist. Appends the current call status to the list
        of requests involved in this call.

        sid: the unique call ID from Twilio
        params: the POSTed request parameters
    """

    # find existing call
    doc = g.db.calls.find_one({'call_sid': sid})

    if doc is None:
        # create new call if call does not exist
        doc = {
            'call_sid': sid,
            'from': params['From'],
            'to': params['To'],
            'caller_name': params.get('CallerName', None),
            'context': {
                'zipcode': None,
                'legislator': None,
            },
        }
        g.db.calls.insert(doc)

    # create array for requests list
    if 'requests' not in doc:
        doc['requests'] = []

    # append current request information and update current status
    doc['requests'].append({
        'timestamp': g.now,
        'call_status': params['CallStatus']
    })
    doc['current_status'] = params['CallStatus']

    return doc


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
        results = sunlight.legislators.allForZip(zipcode)

        # create a copy of the Legislator object dict
        legislators = [r.__dict__.copy() for r in results]

        # sort the legislators by reverse title so Senators are listed
        # before members of the House
        legislators.sort(lambda x, y: -cmp(x['title'], y['title']))

        # move current title to short_title and update title with
        # a more readable version, create full name
        for l in legislators:
            l['short_title'] = l['title']
            l['title'] = TITLES.get(l['title'], 'Representative')
            l['fullname'] = "%s %s %s" % (l['title'], l['firstname'], l['lastname'])

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
    comms = sunlight.committees.allForLegislator(g.legislator['bioguide_id'])
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
