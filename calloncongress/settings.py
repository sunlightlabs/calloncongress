import os
# Define any global settings here
DEBUG = True
LANGUAGES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('eo', 'Esperanto'),
)
DEFAULT_LANGUAGE = 'en'
DEFAULT_VOICE = 'female'
UPCOMING_BILL_DAYS = 14
INPUT_TIMEOUT = 10
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))

import sunlight.services.congress
sunlight.services.congress.API_ROOT = 'http://congress.api.sunlightfoundation.com'

# Import local settings or from os.environ
try:
    from calloncongress.local_settings import *
except ImportError:
    import imp
    import sys
    try:
        with open(os.path.join(os.path.dirname(__file__), 'local_settings.example.py'), 'rb') as fp:
            for key in imp.load_module(
                    'example_settings', fp, 'local_settings.example.py',
                    ('.py', 'rb', imp.PY_SOURCE)
                ).__dict__.keys():
                if os.environ.get(key) is not None:
                    setting = os.environ.get(key)
                    if setting.lower() == 'false':
                        setting = False
                    else:
                        try:
                            float(setting)
                            setting = int(setting)
                        except ValueError:
                            pass
                    setattr(sys.modules[__name__], key, setting)
    except Exception, e:
        raise ImportError('Got %s trying to initialize settings.' % e)
    finally:
        del sys.modules[__name__].imp
        del sys.modules[__name__].os
        del sys.modules[__name__].key
        del sys.modules[__name__].fp
        del sys.modules[__name__].sys  # make sure I'm the last del from sys.modules!
