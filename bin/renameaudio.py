import json
import os
import sys

PWD = os.path.abspath(os.path.dirname(__file__))
LANGUAGES = ('en', 'es', 'eo')


def pathify(p):
    p = os.path.expanduser(p)
    p = os.path.expandvars(p)
    p = os.path.abspath(p)
    return p

if len(sys.argv) < 2:
    print "Usage: renameaudio.py <path to originals>"
    sys.exit(1)

src_path = pathify(sys.argv[1])
dst_path = os.path.abspath(os.path.join(PWD, '..', 'static', 'audio'))
script_path = os.path.abspath(os.path.join(PWD, '..', 'data', 'script.json'))

script = json.loads(open(script_path).read())

for lang in LANGUAGES:

    lang_path = os.path.join(src_path, lang)

    if os.path.exists(lang_path):

        for filename in os.listdir(lang_path):

            file_path = os.path.join(lang_path, filename)
            (filename, ext) = filename.rsplit('.', 1)

            name_hash = script.get(filename)
            if name_hash:

                path = os.path.join(dst_path, lang, '%s.%s' % (name_hash, ext))

                print "Copying %s" % file_path
                print "  -> %s.%s" % (name_hash, ext)

                with open(file_path) as infile:
                    with open(path, 'w') as outfile:
                        outfile.write(infile.read())
