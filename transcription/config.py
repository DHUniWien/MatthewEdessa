# coding=utf-8
"""Configuration routines for tpen2tei and friends"""

import os
import re
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


def tokenise(textnode):
    """Returns a list of tokens from a given text string. In this case,
    punctuation becomes its own token."""
    tokens = []
    words = re.split('\s', textnode)
    punct = re.compile(r"([.,։]+)?(\w+)([.,։]+)?")
    for w in words:
        match = punct.fullmatch(w)
        if match is not None:
            for bit in match.groups():
                if bit is not None:
                    tokens.append(bit)
        else:
            tokens.append(w)
    return tokens


def punctuation():
    return [".", "։", "՜", "՝", "՞"]


def normalise(token):
    # Remove all the punctuation that is irrelevant for collation
    token['t'] = _strip_noise(token['t'])
    token['n'] = _strip_noise(token['n'])
    token['lit'] = _strip_noise(token['lit'])

    # Do some orthographic simplification for Armenian string matching
    if token.get('n') == token.get('t'):
        st = token.get('n').lower().replace(
            'եւ', 'և').replace(
            'աւ', 'օ').replace(
            'է', 'ե').replace(
            'վ', 'ւ')
        if re.search(r'\w', st) is not None:
            st = re.sub(r'[\W]', '', st)
        token['n'] = st

    # Parse the word's XML literal form
    word = fromstring('<word>%s</word>' % token['lit'])
    token_is_number = 'num' in token.get('context')

    # Make a regex for matching any abbreviated words
    if token.get('lit').find('abbr') > -1:
        # Get the first part of the word
        token['re'] = _strip_nonalpha(word.text)
        # Wildcard the abbreviation bit of the word
        for ch in word:
            if ch.tag == 'abbr':  # Join all letters with wildcards
                token['re'] += '.*%s.*' % '.*'.join(_strip_nonalpha(ch.text))
            token['re'] += _strip_nonalpha(ch.tail)
        # Recognise that 'վ' and 'ւ' are used a bit interchangeably e.g. in թվականութիւն
        token['re'] = re.sub(r'\Bվ', '[վւ]', token.get('re'))

    # Make a Graphviz HTML display field for abbreviations, gaps, hilights, etc.
    display = word.text or ''
    if token_is_number:
        display = _number_orth(display)
    for ch in word:
        if ch.tag == 'abbr':  # Put a line over it
            display += '<O>%s</O>' % ch.text
        elif ch.tag == 'hi':  # Make it red
            display += '<FONT COLOR="red">%s</FONT>' % ch.text
        elif ch.tag == 'gap':  # Replace it with stars
            glen = 1
            try:
                glen = int(ch.get('extent'))
            except (ValueError, TypeError):
                pass
            display += '*' * glen
        elif ch.tag == 'damage':
            display += '[%s]' % ch.text
        elif ch.tag == 'supplied':
            display += '&lt;%s&gt;' % ch.text
        elif ch.tag == 'num':
            token_is_number = True
            display += _number_orth(ch.text)
        # elif ch.tag == 'lb':
        #     display += ' | '
        else:
            display += ch.text or ''
        display += ch.tail or ''
    # Clean up orthographic noise of numbers by replacing the 't' value
    if token_is_number:
        token['t'] = display
    if display != token['t']:
        token['display'] = display
    return token


def _strip_noise(st):
    return st.replace(
        '֊', '').replace(
        '՛', '')


def _strip_nonalpha(token):
    if token is not None:
        return re.sub(r"\W", "", token)
    return ""


def _number_orth(st):
    return re.sub(r'[^\w\s]', '', st).upper().replace('ԵՒ', 'և')

def postprocess(root):
    """Find all pb/lb/cb milestone elements that occur last in a
    paragraph, and move them outside that paragraph."""
    ns = {'t': 'http://www.tei-c.org/ns/1.0'}
    for block in root.xpath('//t:body/t:p', namespaces=ns):
        parent = block.getparent()
        idx = parent.index(block)
        try:
            last_el = block.xpath('./child::*[last()]', namespaces=ns)[0]
        except IndexError:
            continue
        tag = last_el.tag.replace('{http://www.tei-c.org/ns/1.0}', '')
        if last_el.tail is None and re.match(r'[lcp]b', tag):
            parent.insert(idx+1, last_el)

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
