import json
import re
import requests
import sys
import utils

# Parse some arguments
parser = utils.arg_parser()
args = parser.parse_args()

# Log in to Stemmaweb
s = requests.Session()
ENDPOINT = utils.stemmaweb_login(args.username, args.password, s)


def get_chapter(sectname):
    exc_chapters = {
        '500prologue': 2,
        '550prologue': 3,
        '550bk3': 3
    }
    key = re.match('^milestone-(.*)$', sectname)
    if key is None:
        raise ValueError("Bad milestone label: %s" % sectname)
    ms = key.group(1)
    chapter = exc_chapters.get(ms)
    if chapter is None:
        # Figure it out based on numbers
        yd = re.match('^(\d+).*', ms)
        if yd is None:
            raise ValueError("Bad milestone label without date: %s" % ms)
        year = int(yd.group(1))
        if year > 577:
            chapter = 4
        elif year > 550:
            chapter = 3
        elif year > 500:
            chapter = 2
        else:
            chapter = 1
    return chapter


def post_annotation(anno):
    url = "%s/%s/annotation" % (ENDPOINT, args.tradition_id)
    # print(anno)
    q = s.post(url, data=json.dumps(anno), headers={'Content-Type': 'application/json'})
    q.raise_for_status()


if __name__ == '__main__':
    # Wipe out all the chapters if asked
    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        url = "%s/tradition/%s/annotations?label=CHAPTER" % (ENDPOINT, args.tradition_id)
        r = s.get(url, headers={'Content-Type': 'application/json'})
        r.raise_for_status()
        for oldanno in r.json():
            url = "%s/tradition/%s/annotation/%s" % (ENDPOINT, args.tradition_id, oldanno.get("id"))
            d = s.delete(url)
            d.raise_for_status
            print("Deleted %s" % d.json())

    # Create the chapters
    allchapters = [
        {'label': 'CHAPTER', 'properties': {'title': 'Book One',
         'language': 'en_US.UTF-8',
         'description': 'The first book, covering the years 401–500 (952–1051)'
        }, 'links': []},
        {'label': 'CHAPTER', 'properties': {'title': 'Book Two',
         'language': 'en_US.UTF-8',
         'description': 'The second book, covering the years 500–550 (1051–1101)'
        }, 'links': []},
        {'label': 'CHAPTER', 'properties': {'title': 'Book Three',
         'language': 'en_US.UTF-8',
         'description': 'The third book, covering the years 550–577 (1101–1129)'
        }, 'links': []},
        {'label': 'CHAPTER', 'properties': {'title': 'Continuation',
         'language': 'en_US.UTF-8',
         'description': 'The continuation by Grigor Erecʿ, covering the years 585–611 (1136–1163)'
        }, 'links': []}
    ]

    # Loop through the sections, adding them as links to the annotation JSON
    url = "%s/%s/sections" % (ENDPOINT, args.tradition_id)
    r = s.get(url, headers={'Content-Type': 'application/json'})
    r.raise_for_status()
    for section in r.json():
        # Find the right chapter
        ident = section.get('name')
        print("Assigning section %s" % ident)
        chapter = allchapters[get_chapter(ident) - 1]
        # Add this section as a link
        chapter.get('links').append({'type': 'CONTAINS', 'target': section.get('id')})

    # Now create the annotations on the server
    for c in allchapters:
        print ("Creating %s with %d sections" % (c.get('properties').get('title'), len(c.get('links'))))
        post_annotation(c)

    print("Done!")
