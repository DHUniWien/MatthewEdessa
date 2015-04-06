# -*- encoding: utf-8 -*-
__author__ = 'tla'

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from lxml import etree
from os.path import basename
from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import from_etree


def normalize_witness(wit, base, milestone=None):
    witnesses = []
    # Convert the selected transcriptions, first to XML and then to tokenized JSON.
    sigil = re.sub('\.json$', '', basename(wit))
    with open(wit, encoding='utf-8') as fh:
        msdata = json.load(fh)
    xmlobj = from_sc(msdata)
    tokens = from_etree(xmlobj, milestone=milestone)
    normalize_spelling(tokens)
    witnesses.append({'id': sigil, 'tokens': tokens})

    # Add in the base XML file.
    xmlobj = etree.parse(base)
    tokens = from_etree(xmlobj, milestone=milestone)
    normalize_spelling(tokens)
    witnesses.append({'id': 'BASE', 'tokens': tokens})

    # Now do the collation. Use the Java version for this.
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

    return {'id': result['witnesses'][1-base_idx], 'tokens': witness_tokens}


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
    for t in tokens:
        if t['t'] == t['n']:
            # Do some extra normalization.
            token = t['t'].lower()
            token = re.sub('\W', '', token)
            token = re.sub('աւ', 'օ', token)
            t['n'] = token
        if t['n'] == '':
            tokens.remove(t)


if __name__ == '__main__':
    argp = argparse.ArgumentParser(description="Collate the chosen transcriptions.")
    argp.add_argument('file', nargs='+')
    argp.add_argument('--base', required=True)
    argp.add_argument('--milestone')
    argp.add_argument('--format', choices=['json', 'graphml', 'csv', 'dot'], default='json')
    options = argp.parse_args()

    normal_witnesses = []
    for fn in options.file:
        normal_witnesses.append(normalize_witness(fn, options.base, options.milestone))

    print(_collate(normal_witnesses, output=options.format))