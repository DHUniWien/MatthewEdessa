__author__ = 'tla'

import argparse
import importlib
import json
import os
import re
import subprocess
import sqlite3
import sys
import tempfile
from tpen2tei.wordtokenize import Tokenizer


def normalize_witness(conn, xmlfile, base, milestone, interactive=False, config=None, aclayer=False):
    """Collate the chosen witness with the base text, in order to find a
    normalised expansion for all of the manuscript abbreviations. Report on
    all the correspondences found, as well as correspondences not found;
    save the results to SQLite."""

    configmod = None
    if config is not None:
        configpath = os.path.expanduser(config)
        sys.path.append(os.path.dirname(configpath))
        configmod = importlib.import_module(os.path.basename(configpath))
    normalise = None
    if configmod is not None:
        normalise = getattr(configmod, "normalise", None)

    tk = Tokenizer(
        milestone=milestone,
        first_layer=aclayer,
        normalisation=normalise,
        id_xpath='//t:msDesc/@xml:id'
    )
    witness = tk.from_file(xmlfile)
    if len(witness['tokens']) == 0:
        return None

    cxinput = {'witnesses': [witness]}
    sigil = witness['id']

    # Add in the base, which is a simple TEI file with the canonical set of milestones.
    tk = Tokenizer(milestone=milestone)
    base_witness = tk.from_file(base)
    cxinput['witnesses'].append({'id': 'BASE', 'tokens': base_witness['tokens']})

    # Now collate the witness to the base.
    print("Comparing witness %s with base" % sigil, file=sys.stderr)
    result = json.loads(_collate(cxinput))

    # And now, figure out the likely expansion of any abbreviations in the
    # original, based on the collation.
    base_idx = result['witnesses'].index('BASE')
    witness_tokens = []
    for corresp in result['table']:
        # If either witness has an empty token, skip this spot
        if len(corresp[1 - base_idx]) == 0:
            continue
        if len(corresp[base_idx]) == 0:
            continue
        # Otherwise, get each token and try to do a normalisation
        # TODO Also look up DB normalisation for collated tokens if the base token doesn't exist
        collated_token = corresp[1 - base_idx][0]
        base_token = corresp[base_idx][0]
        if 're' in collated_token:
            normal_form = _find_normal_form(conn, collated_token, base_token, interactive)
            if normal_form is not None:
                collated_token['normal_form'] = normal_form
        witness_tokens.append(collated_token)

    return {'id': sigil, 'tokens': witness_tokens}


def _find_normal_form(conn, token, basetoken, interactive):

    # Some constants
    LOOKUP_SQL = 'SELECT expansion FROM abbreviations WHERE form=?'
    INSERT_SQL = 'INSERT INTO abbreviations VALUES (?, ?)'
    utiwn_re = re.compile('^(.*)ութ(իւն|եան|ենէ|եամբ)(.*)')
    utiwn_forms = ['իւն', 'եան', 'ենէ', 'եամբ']

    # First see if an entry exists in the database
    c = conn.cursor()
    c.execute(LOOKUP_SQL, (token['n'],))
    result = c.fetchall()
    if len(result) > 0:
        print("Using form %s for %s" % (result[0], token['lit']), file=sys.stderr)
        return result[0]

    # Then see if the token's regex matches the base
    regex = re.compile(token['re'])
    if regex.match(basetoken['n']):
        print("Regex matched form %s for %s" % (basetoken['n'], token['n']), file=sys.stderr)
        c.execute(INSERT_SQL, (token['n'], basetoken['n']))
        conn.commit()
        return basetoken['n']

    # Then do -ութիւն form parsing
    mo = utiwn_re.match(basetoken['n'])
    if mo is not None:
        root = mo.group(0)
        suffix = mo.group(1)
        for uf in utiwn_forms:
            form = root + uf + suffix
            if regex.match(form):
                print("Regex morph matched form %s for %s" % (form, token['n']), file=sys.stderr)
                c.execute(INSERT_SQL, (token['n'], form))
                conn.commit()
                return form
            elif regex.match(root + uf):
                print("Regex morph matched form %s for %s" % (root + uf, token['t']), file=sys.stderr)
                c.execute(INSERT_SQL, (token['n'], root + uf))
                conn.commit()
                return root + uf

    # If we are in interactive mode, ask
    if interactive:
        norm_form = input("Normal form for %s (ase token %s)? " % (token['lit'], basetoken['n']))
        if norm_form:
            c.execute(INSERT_SQL, (token['n'], norm_form))
            conn.commit()
        return norm_form

    print("Unable to find normalisation for %s" % token['lit'], file=sys.stderr)
    return None


def _collate(witnesses, output='json'):
    """Call out to the Java version of CollateX. Requires that you have it installed
     and are running on a Mac."""
    jinput = tempfile.NamedTemporaryFile(delete=False)
    jinput.write(bytes(json.dumps(witnesses), encoding='utf-8'))
    jinput.close()
    try:
        jhome = subprocess.check_output(['/usr/libexec/java_home']).decode(encoding='utf-8').rstrip()
        os.environ['JAVA_HOME'] = jhome
        cxret = subprocess.check_output(["collatex", "-f", output, "-t", jinput.name])
    finally:
        os.unlink(jinput.name)
    return str(cxret, encoding='utf-8')


# Initialize the database if necessary, and return a cursor to it
def _init_db(dbpath):
    conn = sqlite3.connect(dbpath)
    c = conn.cursor()
    # See if our table already exists
    c.execute("SELECT name FROM sqlite_master WHERE type='table';")
    result = c.fetchall()
    if not len(result):
        c.execute("CREATE TABLE abbreviations (form text, expansion text)")
        conn.commit()
    return conn


if __name__ == '__main__':
    argp = argparse.ArgumentParser(description="Collate the chosen transcriptions.")
    argp.add_argument('file', nargs='+')
    argp.add_argument('--base', required=True)
    argp.add_argument('--milestone')
    argp.add_argument('--config')
    argp.add_argument('--db')
    argp.add_argument('-i', '--interactive', action="store_true")
    options = argp.parse_args()

    # Get a DB cursor
    dbconn = _init_db(options.db)

    # Collate each witness in turn against the base, and evaluate for a
    # normal form
    for fn in options.file:
        print("Attempting normalisation on witness %s, milestone %s" % (fn, options.milestone), file=sys.stderr)
        normalize_witness(dbconn, fn, options.base, options.milestone, interactive=options.interactive,
                          config=options.config)
        print("Attempting normalisation on a.c. layer witness %s, milestone %s" % (fn, options.milestone),
              file=sys.stderr)
        normalize_witness(dbconn, fn, options.base, options.milestone, interactive=options.interactive,
                          config=options.config, aclayer=True)

    dbconn.close()
    print("Done. Results saved to %s" % options.db, file=sys.stderr)
