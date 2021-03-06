# coding=utf-8
"""Configuration routines for tpen2tei and friends"""

import os
import random
import re
import requests
import string
from lxml.etree import fromstring, tostring

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
    'թեւ': ('teylig', 'ARMENIAN TO-ECH-YIWN LIGATURE'),  # with ե ւ separated
    'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
    'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
    'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
    'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
    'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
    'մի': ('milig', 'ARMENIAN MEN-INI LIGATURE'),
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

# This is a big ugly hack to prevent thousands of repetitive database API calls.
# Assuming that memory is cheaper than network access.
abbreviation_lookup = {}


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
    # fix hyphen misinterpretation of Tatevik V.
    line = re.sub(r'\s*<add place="below">֊</add>', '֊', line)
    return line.replace(
        '_', '֊').replace(  # fix erroneous underscore use by Razmik
        '“', '"').replace(  # fix curly quote pasting by Anahit
        '”', '"').replace(
        ':', '։').replace(  # use Armenian full stop, not ASCII colon
        'xml։id', 'xml:id').replace( # ...except in xml:id attribute
        '․', '.').replace(  # use ASCII period, not Unicode one-dot leader
        '<p/>', '</p><p>').replace( # fix paragraph milestones
        '<subst><del rend="overwrite"', '<subst rend="overwrite"><del').replace(
        ',', '.')  # MSS have no difference between comma & dot


def punctuation():
    return [".", "։", "՜", "՝", "՞"]


def comparator(tokenstr):
    st = tokenstr.lower().replace(
        'եւ', 'և').replace(
        'աւ', 'օ').replace(
        'է', 'ե').replace(
        'վ', 'ւ')
    if re.search(r'\w', st) is not None:
        st = re.sub(r'[\W]', '', st)
    return st


def normalise(token):
    # Remove all the punctuation that is irrelevant for collation
    token['t'] = _fix_encoding(_strip_noise(token.get('t')))
    token['n'] = _fix_encoding(_strip_noise(token.get('n')))
    token['lit'] = _strip_noise(token.get('lit'))

    # Do some orthographic simplification for Armenian string matching
    if token.get('n') == token.get('t'):
        token['n'] = comparator(token.get('t'))

    # If the token is punctuation, or the words 'և' or 'ի', put a random
    # string in the 'n' field to prevent spurious alignment
    if re.match(r'^(\W+|և|ի)$', token.get('t')):
        token['n'] = ''.join(random.choices(string.ascii_uppercase, k=8))

    # Parse the word's XML literal form
    word = fromstring('<word>%s</word>' % token['lit'])
    token_is_number = 'num' in token.get('context', '') or \
        '<num value=' in token.get('lit')
    token_is_abbreviated = 'abbr' in token.get('context', '')

    # Make a regex for matching any abbreviated words
    token_re = None
    if token_is_abbreviated:
        token_re = '.*%s.*' % '.*'.join(_strip_nonalpha(word.text))
    elif '<abbr>' in token.get('lit'):
        # Get the first part of the word
        token_is_abbreviated = True
        token_re = _strip_nonalpha(word.text)
        # Wildcard the abbreviation bit of the word
        for ch in word:
            if ch.tag == 'abbr':  # Join all letters with wildcards
                token_re += '.*%s.*' % '.*'.join(_strip_nonalpha(ch.text))
            elif ch.text is not None:
                token_re += ch.text
            token_re += _strip_nonalpha(ch.tail)
        # Recognise that 'վ' and 'ւ' are used a bit interchangeably e.g. in թվականութիւն
        token_re = re.sub(r'\Bվ', '[վւ]', token_re)

    # Set the normal form where we can
    if token_re is not None:
        nf = abbreviation_lookup.get(token_re, None)
        if nf is None:
            abbrurl = 'http://test.stemmaweb.net:3000/lookup/%s' % token_re
            try:
                r = requests.get(abbrurl)
                if r.status_code == requests.codes.ok:
                    expansion = r.json()
                    if len(expansion) > 0:
                        # Add normal form, remove regex
                        nf = expansion[0].get('a_expansion')
                    else:
                        nf = 'UNDEF'
                else:
                    nf = 'ERROR %d' % r.status_code
            except requests.exceptions.ConnectionError:
                nf = 'ERROR connection'
        if not nf.startswith('ERROR') and nf is not 'UNDEF':
            token['normal_form'] = nf
            token['n'] = comparator(nf)
            abbreviation_lookup[token_re] = nf
    if token_is_number:
        # Get the numeric value out of the normal form
        nmatch = re.search(r'\d+', token.get('n'))
        if nmatch is not None:
            north = _number_norm(int(nmatch.group(0)))
            token['normal_form'] = token.get('n').replace(
                nmatch.group(0), north)

    # Make a Graphviz HTML display field for numbers, gaps, hilights, etc.
    display = _make_display(word, is_number=token_is_number)
    # Add abbreviation marks over the whole if applicable
    if token_is_abbreviated:
        display = '<O>%s</O>' % display
    # If we are dealing with a number, run the base reading text separately
    # through number_orth, to get the less noisy form without HTML tags
    if token_is_number:
        token['t'] = _number_orth(token.get('t'))
    # Add the display form to the token, if it is different from the t form
    if display != token['t']:
        token['display'] = display
    return token


def _make_display(el, is_number=False):
    display = el.text or ''

    # Handle tags that modify the text itself
    if el.tag == 'num':
        is_number = True
    if is_number:
        display = _number_orth(display)
    elif el.tag == 'gap':  # Replace it with stars
        glen = 1
        try:
            glen = int(el.get('extent'))
        except (ValueError, TypeError):
            pass
        display += '*' * glen

    # Recurse to handle the children
    for ch in el:
        display += _make_display(ch, is_number=is_number)

    # Now handle tags that wrap the text
    if el.tag == 'hi':
        display = '<FONT COLOR="red">%s</FONT>' % display
    elif el.tag == 'damage':
        display = '[%s]' % display
    elif el.tag == 'supplied':
        display = '&lt;%s&gt;' % display

    # Finally, add on the tail
    if el.tail is not None:
        if is_number:
            display += _number_orth(el.tail)
        else:
            display += el.tail

    return display


def _strip_noise(st):
    return st.replace(
        '֊', '').replace(
        '՛', '').replace(
        "\n", "")

def _fix_encoding(st):
    return st.replace(
        'եւ', 'և').replace(
        'h', 'հ').replace(
        'o', 'օ')

def _strip_nonalpha(token):
    if token is not None:
        return re.sub(r"\W", "", token)
    return ""

def upper(matchobj):
    return matchobj.group(0).upper()

def _number_orth(st):
    """Return a more orthographically normalised form of the tagged number"""
    num = re.sub(r'(\w)՟', upper, st)
    # if num != st:
    #     num = num.replace('և', '').replace('ի', '')
    return re.sub(r'[^\w\s]', '', num)

def _number_norm(val):
    '''Return the standard Armenian orthography for a given number value'''
    num = ''
    groups = [ val % 1000, int(val / 1000) ]
    thou = 0
    for g in groups:
        if g > 0:
            single = g < 10
            gn = ''
            power = 0
            while g > 0:
                if g % 10 > 0:
                    gn = chr(g % 10 + 1328 + 9 * power) + gn
                power += 1
                g = int(g / 10)
            if single:
                num = chr(ord(gn) + 27 * thou) + num
            elif len(gn) > 0:
                num = gn + 'Ռ' * thou + num
        thou += 1
    return num

def postprocess(root):
    """Find all pb/lb/cb milestone elements that occur last in a
    paragraph, and move them outside that paragraph."""
    ns = {'t': 'http://www.tei-c.org/ns/1.0'}
    for block in root.xpath('//t:body/t:p', namespaces=ns):
        parent = block.getparent()
        idx = parent.index(block)
        children = list(block)
        if len(children) > 0:
            children.reverse()
            # Move a final line break
            if children[0].tag == '{http://www.tei-c.org/ns/1.0}lb' and children[0].tail is None:
                lb_el = children.pop(0)
                parent.insert(idx+1, lb_el)
                # Now check for page or column breaks
                while len(children) > 0 and re.search(r'\}[cp]b', children[0].tag):
                    br_el = children.pop(0)
                    parent.insert(idx+1, br_el)
                # Now move the remaining trailing newline where it belongs
                if len(children):
                    penultimate = children[0]
                    if penultimate.tail is not None:
                        penultimate.tail = penultimate.tail.rstrip()
                    else:
                        print("Penultimate was %s" % tostring(penultimate, encoding="utf-8").decode("utf-8"))
                else:
                    block.text = block.text.rstrip()
                block.tail = "\n"


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
    # return ['410', '407', '408']
