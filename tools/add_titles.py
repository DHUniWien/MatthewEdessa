import locale
import re
import requests
import sys
import utils
from datetime import date, timedelta

# Parse some arguments
parser = utils.arg_parser()
args = parser.parse_args()

# Log in to Stemmaweb
s = requests.Session()
ENDPOINT = utils.stemmaweb_login(args.username, args.password, s)
languages = ['hy_AM.UTF-8', 'en_US.UTF-8']


def get_datestring(year, localestr):
    beginning = date(552, 7, 11)
    dyear = int(year)
    offset = (dyear - 1) * 365
    # Account for Julian leap year rules in range 952–1163
    if dyear > 549:
        offset -= 5
    elif dyear > 448:
        offset -= 4
    else:
        offset -= 3
    nawasard1 = beginning + timedelta(days=offset)
    awaleats5 = nawasard1 + timedelta(days=364)
    locale.setlocale(locale.LC_ALL, localestr)
    return "%s–%s" % ((nawasard1.strftime("%-d %B %-Y").replace(" 0", " ")),
                        (awaleats5.strftime("%-d %B %-Y").replace(" 0", " ")))


def get_title(sectname, lang):
    exc_titles = {
        '421letter': {'hy': '421 թ., Յովհաննու Չմշկիկի թուղթն', 'en': 'The year 421, letter of Iōannēs Tzimiskes'},
        '421letter-A': {'hy': '421 թ., Յովհաննու Չմշկիկի թուղթն (մասն Ա)', 'en': 'The year 421, letter of Iōannēs Tzimiskes (part 1)'},
        '421letter-B': {'hy': '421 թ., Յովհաննու Չմշկիկի թուղթն (մասն Բ)', 'en': 'The year 421, letter of Iōannēs Tzimiskes (part 2)'},
        '421letter-C': {'hy': '421 թ., Յովհաննու Չմշկիկի թուղթն (մասն Գ)', 'en': 'The year 421, letter of Iōannēs Tzimiskes (part 3)'},
        '421letter-D': {'hy': '421 թ., Յովհաննու Չմշկիկի թուղթն (մասն Դ)', 'en': 'The year 421, letter of Iōannēs Tzimiskes (part 4)'},
        '471prophecy': {'hy': '471 թ., Կոզեռնի առաջին մարգարէութիւնն', 'en': 'The year 471, first prophecy of Kozeṙn'},
        '471aftermath': {'hy': '471 թ., շարունակութիւնն', 'en': 'The year 471, continued'},
        '485prophecy': {'hy': '485 թ., Կոզեռնի երկրորդ մարգարէութիւնն', 'en': 'The year 485, second prophecy of Kozeṙn'},
        '500prologue': {'hy':'500 թ., Ուռհայեցու առաջին յիշատակարանն', 'en': 'The year 500, first prologue of Uṙhayecʿi'},
        '514confession': {'hy': 'Գագիկի Բագրատունւոյ խոստովանութունն հաւատոյ', 'en': 'The year 514, confession of faith of Gagik Bagratuni'},
        '514aftermath': {'hy': '514 թ., շարունակութիւնն', 'en': 'The year 514, continued'},
        '534.2': {'hy': '534 թ., մասն երկրորդ', 'en': 'The year 534, second entry'},
        '546cutoff': {'hy': '546 թ., շարունակութիւնն', 'en': 'The year 546, continued'},
        '550prologue': {'hy':'550 թ., Ուռհայեցու երկրորդ յիշատակարանն', 'en': 'The year 550, second prologue of Uṙhayecʿi'},
        '550bk3': {'hy': '550 թ., մասն երկրորդ', 'en': 'The year 550, second entry'},
        '592thoros': {'hy': 'Երեւութիւնն Թորոսի, շուրջ 592 թ.', 'en': 'The appearance of Tʿoros, c. 592'},
        '595barsegh': {'hy': '595 թ., Բարսեղի վարդապետի դամբանականն', 'en': 'The year 595, funereal oration of Barseł vardapet'},
        '595barsegh-A': {'hy': '595 թ., Բարսեղի վարդապետի դամբանականն (մասն Ա)', 'en': 'The year 595, funereal oration of Barseł vardapet (part 1)'},
        '595barsegh-B': {'hy': '595 թ., Բարսեղի վարդապետի դամբանականն (մասն Բ)', 'en': 'The year 595, funereal oration of Barseł vardapet (part 2)'},
        '595barsegh-C': {'hy': '595 թ., Բարսեղի վարդապետի դամբանականն (մասն Գ)', 'en': 'The year 595, funereal oration of Barseł vardapet (part 3)'},
        '595barsegh-D': {'hy': '595 թ., Բարսեղի վարդապետի դամբանականն (մասն Դ)', 'en': 'The year 595, funereal oration of Barseł vardapet (part 4)'},
        '602b': {'hy': '602 թ., մասն երկրորդ', 'en': 'The year 602, second entry'},
        '604b': {'hy': '604 թ., մասն երկրորդ', 'en': 'The year 604, second entry'}
    }
    key = re.match('^milestone-(.*)$', sectname)
    if key is None:
        raise ValueError("Bad milestone label: %s" % sectname)
    year = key.group(1)
    title = exc_titles.get(year)
    if title is None:
        # Use a default title
        pattern = "%s թ. (%s)" if lang == 'hy_AM.UTF-8' else "The year %s (%s)"
        return pattern % (year, get_datestring(year, lang))
    else:
        return title.get(lang[0:2])


def post_annotation(anno):
    url = "%s/%s/annotation" % (ENDPOINT, args.tradition_id)
    print(anno)
    q = s.post(url, json=anno)
    q.raise_for_status()
    ## print("Annotation ID: " + q.json().get("id"))


if __name__ == '__main__':

    # Wipe out all the titles if asked
    if len(sys.argv) > 1 and sys.argv[1] == "-d":
        # Delete any previous title annotation(s)
        url = "%s/%s/annotations?label=TITLE" % (ENDPOINT, args.tradition_id)
        r = s.get(url)
        r.raise_for_status()
        for oldanno in r.json():
            url = "%s/%s/annotation/%s" % (ENDPOINT, args.tradition_id, oldanno.get("id"))
            d = s.delete(url)
            d.raise_for_status
            print("Deleted %s" % d.json())

    # Loop through the sections
    url = "%s/%s/sections" % (ENDPOINT, args.tradition_id)
    r = s.get(url)
    r.raise_for_status()
    for section in r.json():
        # Get its name
        ident = section.get('name')
        print("Titling section %s" % ident)
        # Set up the annotation structure
        annotation = {
            "links": [{"target": section.get("id"), "type": "TITLED"}],
            "label": "TITLE",
            "primary": True
        }
        for lang in languages:
            annotation["properties"] = {"language": lang[0:2], "text": get_title(ident, lang)}
            post_annotation(annotation)

    print("Done!")
