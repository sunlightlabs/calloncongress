MENU = {
    'main': {
        'name': 'Main menu',
        'route': '.index',
        'choices': [
            {'key': 1, 'action': '.members'},
            {'key': 2, 'action': '.bills'},
            {'key': 3, 'action': '.voting'},
            {'key': 4, 'action': '.about'},
        ],
    },
    'member': {
        'name': 'Member options for %s',
        'route': '.member',
        'parent': 'reps',
        'choices': [
            {'key': 1, 'action': '.member_bio'},
            {'key': 2, 'action': '.member_donors'},
            {'key': 3, 'action': '.member_votes'},
            {'key': 4, 'action': '.member_call'},
        ],
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
    'bill': {
        'name': 'Bill information for %s',
        'route': '.bill',
        'parent': 'bills',
        'choices': [
            {'key': 1, 'action': '.subscribe_to_bill_updates'},
            {'key': 2, 'action': '.search_bills'},
            {'key': 0, 'action': '.index'}
        ],
    },
    # 'upcoming_bills': {
    #     'name': 'Upcoming bills',
    #     'route': '.upcoming_bills',
    #     'parent': 'bills',
    #     'choices': [
    #         {'key': 1, 'action': '.call_reps'},
    #     ]
    # },
    # 'voting': {
    #     'name': 'Voting information',
    #     'route': '.voting',
    #     'parent': 'main',
    #     'choices': [
    #         {'key': 1, 'action': '.call_election_commission'},
    #     ],
    # },
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