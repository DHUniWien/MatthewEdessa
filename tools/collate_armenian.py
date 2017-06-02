__author__ = 'tla'

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from io import BytesIO
from lxml import etree
from os.path import basename
from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import from_file, from_etree

# Our list of special characters that might occur as glyph (<g/>) elements.
# The key is the normalized form; the tuple is (xml:id, description).
_armenian_glyphs = {
    'աշխարհ': ('asxarh', 'ARMENIAN ASHXARH SYMBOL'),
    'ամենայն': ('amenayn', 'ARMENIAN AMENAYN SYMBOL'),
    'արեգակն': ('aregakn', 'ARMENIAN AREGAKN SYMBOL'),
    'լուսին': ('lusin', 'ARMENIAN LUSIN SYMBOL'),
    'որպէս': ('orpes', 'ARMENIAN ORPES SYMBOL'),
    'երկիր': ('erkir', 'ARMENIAN ERKIR SYMBOL'),
    'երկին': ('erkin', 'ARMENIAN ERKIN SYMBOL'),
    'ընդ': ('und', 'ARMENIAN END SYMBOL'),
    'ըստ': ('ust', 'ARMENIAN EST SYMBOL'),
    'պտ': ('ptlig', 'ARMENIAN PEH-TIWN LIGATURE'),
    'թբ': ('tblig', 'ARMENIAN TO-BEN LIGATURE'),
    'թե': ('techlig', 'ARMENIAN TO-ECH LIGATURE'),
    'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
    'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
    'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
    'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
    'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
    'րզ': ('rzlig', 'ARMENIAN REH-ZA LIGATURE'),
    'զմ': ('zmlig', 'ARMENIAN ZA-MEN LIGATURE'),
    'թգ': ('tglig', 'ARMENIAN TO-GIM LIGATURE'),
    'ա': ('avar', 'ARMENIAN AYB VARIANT'),
    'հ': ('hvar', 'ARMENIAN HO VARIANT'),
    'յ': ('yabove', 'ARMENIAN YI SUPERSCRIPT VARIANT')
}

def numberparse(val):
    """Given the text content of a <num> element, try to turn it into a number."""
    # Create the stack of characters
    sigfigs = [ord(c) for c in val.replace('և', '').upper() 
                if ord(c) > 1328 and ord(c) < 1365]
    total = 0
    last = None
    for ch in sigfigs:
        # What is this one's numeric value?
        if ch < 1338:    # Ա-Թ
            chval = ch - 1328
        elif ch < 1347:  # Ժ-Ղ
            chval = (ch - 1337) * 10
        elif ch < 1356:  # Ճ-Ջ
            chval = (ch - 1346) * 100
        else:            # Ռ-Ք
            chval = (ch - 1355) * 1000

        # Put it in the total
        if last is None or chval < last:
            total += chval
        else:
            total *= chval
        last = chval
    return total


def normalize_witness(wit, base, milestone, input, first_layer=False):
    """Collate each manuscript in turn with the base text, in order to find a
    normalised expansion for all of the manuscript abbreviations. Return a list
    of tokens that contain these normalised forms, for the 'main' collation."""
    witnesses = []
    # Convert the selected transcriptions, first to XML and then to tokenized JSON.
    if input == 'json':
        with open(wit, encoding='utf-8') as fh:
            msdata = json.load(fh)
        xmlobj = from_sc(msdata, special_chars=_armenian_glyphs, numeric_parser=numberparse)
    else:
        with open(xmlfile, encoding='utf-8') as fh:
            xmlobj = etree.parse(fh)
    tokens = from_etree(xmlobj, milestone=milestone, first_layer=first_layer)
    if not len(tokens):
        # The witness doesn't have anything for the given milestone. Skip it.
        return None
    sigil = re.sub('(\.(json|tei|xml))+$', '', basename(wit))
    # sigil = xmlobj.getroot().find(
    #         '{http://www.tei-c.org/ns/1.0}msDesc').get(
    #         '{http://www.w3.org/XML/1998/namespace}id')
    if first_layer:
        sigil += ' (a.c.)'
    witnesses.append({'id': sigil, 'tokens': normalize_spelling(tokens)})

    # Add in the base, which is a plain text file.
    tokens = plaintext_tokenize(base)
    witnesses.append({'id': 'BASE', 'tokens': normalize_spelling(tokens)})

    # Now do the collation. Use the Java version for this.
    print("Normalizing witness %s" % sigil, file=sys.stderr)
    result = json.loads(_collate(witnesses))

    # And now, figure out the likely expansion of any abbreviations in the original, based
    # on the collation.
    seen_expansions = {}
    base_idx = result['witnesses'].index('BASE')
    witness_tokens = []
    for corresp in result['table']:
        if len(corresp[1 - base_idx]) == 0:
            continue
        collated_token = corresp[1 - base_idx][0]
        if collated_token['lit'].find('abbr') > -1:
            if len(corresp[base_idx]):
                # Use what is in the base as a priority.
                base_token = corresp[base_idx][0]
                print("Normalizing %s to %s" % (collated_token['t'], base_token['n']), file=sys.stderr)
                seen_expansions[collated_token['n']] = base_token['n']
                collated_token['n'] = base_token['n']
            elif collated_token['n'] in seen_expansions:
                # Otherwise use any matching instance we have yet seen.
                collated_token['n'] = seen_expansions[collated_token['n']]
        witness_tokens.append(collated_token)

    return {'id': sigil, 'tokens': witness_tokens}
    
def plaintext_tokenize(txtfile):
    tokens = []
    with open(txtfile, encoding='utf-8') as fh:
        words = fh.read()
        for word in words.split():
            tokens.append({'t': word, 'n': word, 'lit': word})
    return tokens


def _collate(witnesses, output='json'):
    """Call out to the Java version of CollateX. Requires that you have it installed
     and are running on a Mac."""
    jinput = tempfile.NamedTemporaryFile(delete=False)
    jinput.write(bytes(json.dumps({'witnesses': witnesses}), encoding='utf-8'))
    jinput.close()
    try:
        jhome = subprocess.check_output(['/usr/libexec/java_home']).decode(encoding='utf-8').rstrip()
        os.environ['JAVA_HOME'] = jhome
        cxret = subprocess.check_output(["collatex", "-f", output, "-t", jinput.name])
    finally:
        os.unlink(jinput.name)
    return str(cxret, encoding='utf-8')


def normalize_spelling(tokens):
    ntokens = []
    for t in tokens:
        if t['t'] == t['n']:
            # Do some extra normalization.
            token = t['t'].lower()
            token = re.sub('\W', '', token)
            token = re.sub('աւ', 'օ', token)
            token = re.sub('և', 'եւ', token)
            t['n'] = token
        if t['lit'].find('<abbr') > -1:
            # Add the Armenian abbreviation marks.
            abbrtoken = ''
            tfrag = BytesIO(bytes('<word>%s</word>' % t['lit'], encoding='utf-8'))
            abbreviate = False
            for event, element in etree.iterparse(tfrag, events=("start", "end")):
                if element.tag == '{http://www.tei-c.org/ns/1.0}abbr':
                    abbreviate = event == 'start'
                wfrag = ''
                if event == 'start':
                    wfrag = element.text or ''
                else:
                    wfrag = element.tail or ''
                if abbreviate:
                    wfrag = '՟'.join(wfrag)
                    if len(wfrag) == 1:
                        wfrag += '՟'
                abbrtoken += wfrag
            t['t'] = abbrtoken
        if t['n'] != '':
            ntokens.append(t)
    return ntokens


if __name__ == '__main__':
    argp = argparse.ArgumentParser(description="Collate the chosen transcriptions.")
    argp.add_argument('file', nargs='+')
    argp.add_argument('--base', required=True)
    argp.add_argument('--milestone')
    argp.add_argument('--input', choices=['json', 'xml'], default='json')
    argp.add_argument('--output', choices=['json', 'graphml', 'csv', 'dot'], default='json')
    options = argp.parse_args()

    normal_witnesses = []
    for fn in options.file:
        main_layer = normalize_witness(fn, options.base, options.milestone, options.input)
        if main_layer is not None:
            normal_witnesses.append(main_layer)
        corr_layer = normalize_witness(fn, options.base, options.milestone, options.input, True)
        if corr_layer is not None:
            normal_witnesses.append(corr_layer)
    result = _collate(normal_witnesses, output=options.output)
    sys.stdout.buffer.write(result.encode('utf-8'))
