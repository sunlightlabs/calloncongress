# Define any global settings here
DEBUG = True
LANGUAGES = (
    ('en', 'English'),
    ('es', 'Spanish'),
    ('eo', 'Esperanto')
)

DEFAULT_LANGUAGE = 'en'

# Import local settings or from os.environ
try:
    from calloncongress.local_settings import *
except ImportError:
    import imp
    import os
    import sys
    try:
        with open(os.path.join(os.path.dirname(__file__), 'local_settings.example.py'), 'rb') as fp:
            for key in imp.load_module(
                    'example_settings', fp, 'local_settings.example.py',
                    ('.py', 'rb', imp.PY_SOURCE)
                ).__dict__.keys():
                if os.environ.get(key) is not None:
                    setattr(sys.modules[__name__], key, os.environ.get(key))
    except Exception, e:
        raise ImportError('Got %s trying to initialize settings.' % e)
    finally:
        del sys.modules[__name__].imp
        del sys.modules[__name__].os
        del sys.modules[__name__].key
        del sys.modules[__name__].fp
        del sys.modules[__name__].sys  # make sure I'm the last del from sys.modules!
