"""Configuration routines for tpen2tei and friends"""

import os
import re
import yaml
from lxml.etree import fromstring

metadata = {
    'title': 'Ժամանակագրութիւն',
    'author': 'Մատթէոս Ուռհայեցի',
    'short_error': True
}

special_chars = {
    'աշխարհ': ('asxarh', 'ARMENIAN ASHXARH SYMBOL'),
    'ամենայն': ('amenayn', 'ARMENIAN AMENAYN SYMBOL'),
    'արեգակն': ('aregakn', 'ARMENIAN AREGAKN SYMBOL'),
    'լուսին': ('lusin', 'ARMENIAN LUSIN SYMBOL'),
    'աստղ': ('astgh', 'ARMENIAN ASTGH SYMBOL'),
    'աւետարան': ('awetaran', 'ARMENIAN AWETARAN SYMBOL'),
    'որպէս': ('orpes', 'ARMENIAN ORPES SYMBOL'),
    'երկիր': ('erkir', 'ARMENIAN ERKIR SYMBOL'),
    'երկին': ('erkin', 'ARMENIAN ERKIN SYMBOL'),
    'ընդ': ('und', 'ARMENIAN END SYMBOL'),
    'ըստ': ('ust', 'ARMENIAN EST SYMBOL'),
    'ըստ այնմ': ('ustaynm', 'ARMENIAN EST-AYNM LIGATURE'),
    'պտ': ('ptlig', 'ARMENIAN PEH-TIWN LIGATURE'),
    'րպ': ('rplig', 'ARMENIAN REH-PEH LIGATURE'),
    'թբ': ('tblig', 'ARMENIAN TO-BEN LIGATURE'),
    'թե': ('techlig', 'ARMENIAN TO-ECH LIGATURE'),
    'թև': ('tewlig', 'ARMENIAN TO-EW LIGATURE'),  # with the Unicode ligature
    'թեւ': ('tewlig', 'ARMENIAN TO-EW LIGATURE'),  # with ե ւ separated
    'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
    'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
    'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
    'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
    'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
    'րզ': ('rzlig', 'ARMENIAN REH-ZA LIGATURE'),
    'սպ': ('splig', 'ARMENIAN SEH-PEH LIGATURE'),
    'զմ': ('zmlig', 'ARMENIAN ZA-MEN LIGATURE'),
    'թգ': ('tglig', 'ARMENIAN TO-GIM LIGATURE'),
    'ին': ('inlig', 'ARMENIAN INI-NU LIGATURE'),
    'իվ': ('ivlig', 'ARMENIAN INI-VEV LIGATURE'),
    'ռո': ('rolig', 'ARMENIAN RA-VO LIGATURE'),
    'ըս': ('uslig', 'ARMENIAN ET-SEH LIGATURE'),
    'ա': ('avar', 'ARMENIAN AYB VARIANT'),
    'հ': ('hvar', 'ARMENIAN HO VARIANT'),
    'յ': ('yabove', 'ARMENIAN YI SUPERSCRIPT VARIANT'),
    'ր': ('rabove', 'ARMENIAN REH SUPERSCRIPT VARIANT')
}

def numeric_parser(val):
    """Given the text content of a <num> element, try to turn it into a number."""
    # Create the stack of characters
    sigfigs = [ord(c) for c in val.replace('և', '').upper() if 1328 < ord(c) < 1365]
    total = 0
    last = None
    for ch in sigfigs:
        # What is this one's numeric value?
        if ch < 1338:  # Ա-Թ
            chval = ch - 1328
        elif ch < 1347:  # Ժ-Ղ
            chval = (ch - 1337) * 10
        elif ch < 1356:  # Ճ-Ջ
            chval = (ch - 1346) * 100
        else:  # Ռ-Ք
            chval = (ch - 1355) * 1000

        # Put it in the total
        if last is None or chval < last:
            total += chval
        else:
            total *= chval
        last = chval
    return total


def transcription_filter(line):
    """A list of custom corrections to easily-fixed transcription errors"""
    line = re.sub(r'(?<=[^</"])un(clear|known)', '<gap/>', line)
    line = re.sub(r'<del\s+type', '<del rend', line)
    return line.replace(
        '_', '֊').replace(  # fix erroneous underscore use by Razmik
        '“', '"').replace(  # fix curly quote pasting by Anahit
        '”', '"').replace(
        '<subst><del rend="overwrite"', '<subst rend="overwrite"><del').replace(
        ',', '.')  # MSS have no difference between comma & dot


def normalise(token):
    # Normalise for Armenian orthography and case
    if token['n'] == token['t']:
        st = token['n'].lower().replace('եւ', 'և').replace('աւ', 'օ')
        if re.search(r'\w', st) is not None:
            st = re.sub(r'[\W]', '', st)
        token['n'] = st
    # Make a regex for matching any abbreviated words
    if token['lit'].find('abbr') > -1:
        token['re'] = '%s.*' % '.*'.join(token['t'])
        token['re'] = token['re'].replace('վ', '[վւ]')
    # Make an Graphviz HTML display field for abbreviations, gaps, hilights, etc.
    word = fromstring('<word>%s</word>' % token['lit'])
    display = word.text or ''
    for ch in word:
        if ch.tag == 'abbr':  # Put a line over it
            display += '<O>%s</O>' % ch.text
            use_html = True
        elif ch.tag == 'hi':  # Make it red
            display += '<FONT COLOR="red">%s</FONT>' % ch.text
        elif ch.tag == 'gap':  # Replace it with stars
            glen = 1
            try:
                glen = int(ch.get('extent'))
            except:
                pass
            display += '*' * glen
        elif ch.tag == 'damage':
            display += '[%s]' % ch.text
        else:
            display += ch.text or ''
        display += ch.tail or ''
    if display != token['t']:
        token['display'] = display
    return token


def milestones():
    # Where are we?
    milestonelist = []
    ourpath = os.path.abspath(os.path.dirname(__file__))
    ocrpath = ourpath.replace('transcription', 'ocr')
    ocrfiles = [f for f in os.listdir(ocrpath)
                if f.startswith('vagharshapat') and f.endswith('.txt')]
    for f in sorted(ocrfiles):
        with open("%s/%s" % (ocrpath, f), encoding='utf-8') as fh:
            for line in fh:
                for m in re.finditer(r'milestone unit="section" n="([\w.]+)"', line):
                    milestonelist.append(m.group(1))
    return milestonelist
