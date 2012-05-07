from calloncongress.voice.helpers import *

MENU = {
    'main': {
        'name': 'Main menu',
        'route': '.index',
        'choices': [
            {'key': 1, 'action': '.reps'},
            {'key': 2, 'action': '.bills'},
            {'key': 3, 'action': '.voting'},
            {'key': 4, 'action': '.about'},
        ],
    },
    'reps': {
        'name': 'Your members of congress',
        'route': '.reps',
        'parent': 'main',
        'depends_on': ['zipcode_selected'],
        'choices': rep_choices,
    },
    'rep': {
        'name': selected_rep_name,
        'route': selected_rep_url,
        'parent': 'reps',
        'choices': [
            {'key': 1, 'action': selected_rep_biography_url},
            {'key': 2, 'action': selected_rep_donors_url},
            {'key': 3, 'action': selected_rep_votes_url},
            {'key': 4, 'action': selected_rep_call_office_url},
        ],
    },
    'call_reps': {
        'name': 'Call your representatives',
        'route': '.call_reps',
        'parent': referrer,
        'choices': rep_choices,
    },
    'bills': {
        'name': 'Find bills',
        'route': '.bills',
        'parent': 'main',
        'choices': [
            {'key': 1, 'action': '.upcoming_bills'},
            {'key': 2, 'action': '.search_bills'},
        ],

    },
    'upcoming_bills': {
        'name': 'Upcoming bills',
        'route': '.upcoming_bills',
        'parent': 'bills',
        'choices': [
            {'key': 1, 'action': '.call_reps'},
        ]
    },
    'bill_detail': {
        'name': selected_bill_name,
        'route': selected_bill_url,
        'parent': 'bills',
        'choices': selected_bill_choices,
    },
    'voting': {
        'name': 'Voting information',
        'route': '.voting',
        'parent': 'main',
        'choices': [
            {'key': 1, 'action': '.call_election_commission'},
        ],
    },
    'about': {
        'name': 'About Call on Congress',
        'route': '.about',
        'parent': 'main',
        'choices': [
            {'key': 1, 'action': '.about_sunlight'},
            {'key': 2, 'action': '.signup'},
            {'key': 3, 'action': '.feedback'}
        ],
    },
}