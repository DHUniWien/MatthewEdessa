import argparse
import json
import re
import requests
from requests.exceptions import HTTPError


STEMMAWEB_URL = 'https://stemmaweb.net/stemmaweb'
# STEMMAWEB_URL = 'http://localhost:3000'


def stemmaweb_login(uname, pword, session):
    """Try to log into Stemmaweb, and return the cookie we get"""
    credentials = {
        'username': uname, 
        'password': pword 
    }
    r = session.post(STEMMAWEB_URL + "/login", data=credentials)
    r.raise_for_status()


def make_obvious_relations(options, session):
    """Connects to a Stemmarest URL, goes section by section through
    the readings, and tries to make relationships based on normal form,
    case folding, and a few other custom parameters."""
    url = "%s/api/%s" % (STEMMAWEB_URL, options.tradition_id)
    for section in get_sections(url, options.section, session):
        print("Working on section %s" % section.get('name'))
        apply_relations(url, section.get('id'), session, verbose=options.verbose)


def get_sections(url, requested, session):
    r = session.get("%s/sections" % url)
    r.raise_for_status()
    if requested is not None:
        return [s for s in r.json() if s.get('name') == requested]
    return r.json()


def apply_relations(url, sectid, session, verbose=False):
    rdgurl = "%s/section/%s/readings" % (url, sectid)
    r = session.get(rdgurl)
    r.raise_for_status()
    ranked_rdgs = sort_by_rank(r.json())
    relation_stack = []
    for rk in ranked_rdgs.keys():
        column = ranked_rdgs.get(rk)
        while len(column) > 0:
            thisrdg = column.pop(0)
            for otherrdg in column:
                if re.fullmatch(r'\W+', thisrdg.get('text')) \
                    and re.fullmatch(r'\W+', otherrdg.get('text')):
                    relation_stack.append((thisrdg, otherrdg, 'punctuation'))
                elif test_equiv(thisrdg, otherrdg, _spelling_cmp_string):
                    relation_stack.append((thisrdg, otherrdg, 'spelling'))
                elif test_equiv(thisrdg, otherrdg, _punct_cmp_string):
                    relation_stack.append((thisrdg, otherrdg, 'punctuation'))
                elif test_equiv(thisrdg, otherrdg, _grammar_cmp_string):
                    relation_stack.append((thisrdg, otherrdg, 'grammatical'))

    make_relations("%s/relation" % url, relation_stack, session, verbose=verbose)


def sort_by_rank(rdglist):
    rankdict = {}
    for rdg in rdglist:
        rk = rdg.get('rank')
        if rk in rankdict:
            rankdict.get(rk).append(rdg)
        else:
            rankdict[rk] = [rdg]
    return rankdict


def test_equiv(rdg1, rdg2, subr):
    equiv = rdg1.get('normal_form') == rdg2.get('normal_form') or \
            rdg1.get('normal_form') == rdg2.get('text') or \
            rdg1.get('text') == rdg2.get('normal_form')
    t1 = subr(rdg1.get('text').lower())
    t2 = subr(rdg2.get('text').lower())
    # Use the modified 'text' attribute if 'normal_form' doesn't exist

    n1 = subr((rdg1.get('normal_form') or t1).lower())
    n2 = subr((rdg2.get('normal_form') or t2).lower())
    return t1 != '' and t2 != '' and (t1 == t2 or t1 == n2 or t2 == n1)


def _spelling_cmp_string(s):
    """Some experimental spelling assumptions"""
    s = re.sub('ը', '', s)   # same except for ը
    s = re.sub('աւ', 'օ', s) # same except for spelling of long o
    s = re.sub('է', 'ե', s)  # same except for long/short e
    s = re.sub('եւ', 'և', s)  # same except for ew ligature-or-not
    s = re.sub(r'(?<=[աո])՛?$', 'յ', s)  # same except for ՛ instead of յ
    s = re.sub(r'(?<=[աո])$', 'յ', s)   # same except for omitted terminal յ
    s = re.sub('[բփ]', 'պ', s)   # same except for labial plosives
    s = re.sub('[գք]', 'կ', s)   # same except for velar plosives
    s = re.sub('[դթ]', 'տ', s)   # same except for dental plosives
    s = re.sub('[ցձ]', 'ծ', s)   # same except for alveolar affricates
    s = re.sub('փ', 'ֆ', s)   # same exceot for 'f' forms
    s = re.sub('[ւվ]', 'ու', s)   # same except for v/w forms
    s = re.sub('ո', 'օ', s)   # same except for long/short o
    s = re.sub('ր', 'ռ', s)   # same except for r forms
    return s

def _punct_cmp_string(s):
    """Remove any punctuation from the strings"""
    s = re.sub('\W+', '', s)
    return s

def _grammar_cmp_string(s):
    """Some experimental grammatical form assumptions"""
    s = re.sub('եսցին', 'եսցեն', s)
    s = re.sub('^յ', '', s)
    s = re.sub('[նսք]$', '', s)
    return s

def make_relations(url, stack, session, verbose=False):
    for rtuple in stack:
        relmodel = {
            'source': rtuple[0].get('id'),
            'target': rtuple[1].get('id'),
            'type': rtuple[2],
            'annotation': 'automatically created',
            'scope': 'local'
        }
        prettyprint = "%s/%s and %s/%s (%s)" % \
                      (rtuple[0].get('rank'), rtuple[0].get('text'), rtuple[1].get('rank'), rtuple[1].get('text'), rtuple[2])
        
        headers={'Content-Type': 'application/json'}
        r = session.post(url, data=json.dumps(relmodel), headers=headers)
        try:
            r.raise_for_status()
        except HTTPError as he:
            print("Failed to link %s: HTTP error %s"
                % (prettyprint, he.response.text))
            continue

        if verbose and r.status_code == requests.codes.not_modified:
            print("Readings %s already linked" % prettyprint)
        else:
            print("Linked readings %s" % prettyprint)


def merge_identical_across_ranks(options, session):
    url = "%s/api/%s" % (STEMMAWEB_URL, options.tradition_id)
    for section in get_sections(url, options.section, session):
        print("Checking mergeable readings in section %s" % section.get('name'))
        ws = 100  # window size
        er = section.get('endRank')
        st = 1 # window start
        if options.verbose:
            print("Window size %d, end rank %d" % (ws, er))
        while st < er:
            # Set the window end, never exceeding the end rank
            e = st+ws if st+ws < er else er
            murl = "%s/section/%s/mergeablereadings/%d/%d" % \
                (url, section.get('id'), st, e)
            if options.verbose:
                print("Requesting %s" % murl)
            r = session.get(murl)
            r.raise_for_status()
            # Move the window start to 10 less than the window end, 
            # to allow for overlap
            st += ws - 10

            # We have a list of mergeable readings. Do a best-attempt merge
            # of what we can, and try to keep track when a reading has been
            # merged away already
            # TODO handle the case where A goes into B, B goes into C, but
            # A is still pointing to B as its merge target
            mergetargets = {}
            for pair in r.json():
                (or1, or2) = pair   # the original readings
                if _mergeable(*pair):
                    # This is pretty hackish, and relies on _attempt_merge only needing ID and text.
                    # Make pseudo-readings out of the previous merge targets.
                    rid1 = mergetargets.get(or1.get('id'), or1.get('id'))
                    r1 = {'id': rid1, 'text': or1.get('text')}
                    rid2 = mergetargets.get(or2.get('id'), or2.get('id'))
                    r2 = {'id': rid2, 'text': or2.get('text')}
                    if rid1 == rid2:
                        continue
                    # Attempt the merge and keep track of which readings no longer exist
                    mgurl = "%s/reading/%s/merge/%s" % \
                        (url, rid1, rid2)
                    if _attempt_merge(mgurl, r1, r2, session, verbose=options.verbose):
                        mergetargets[rid2] = rid1



def _mergeable(r1, r2):
    a = "%s|%s|%s" % (r1.get('text'), r1.get('normal_form'), r1.get('display'))
    b = "%s|%s|%s" % (r2.get('text'), r2.get('normal_form'), r2.get('display'))
    return a == b



def _attempt_merge(url, r1, r2, session, verbose=False):
    if verbose:
        print("Attempting merge of %s/%s and %s/%s" % \
              (r1.get('id'), r1.get('text'),
               r2.get('id'), r2.get('text')), end='', flush=True)
    r = session.post(url)
    try:
        r.raise_for_status()
    except HTTPError as e:
        if verbose:
            print("...failed: %s" % e.response.text)
        return False
    if verbose:
        print("...succeeded")
    return True


# Do the work
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    server = parser.add_argument_group('Stemmaweb server connection')
    server.add_argument(
        "-u",
        "--username",
        help="HTTP basic auth username for tradition repository"
    )
    server.add_argument(
        "-p",
        "--password",
        help="HTTP basic auth password for tradition repository"
    )

    parser.add_argument(
        "-t",
        "--tradition-id",
        required=True,
        help="ID of tradition to process"
    )
    parser.add_argument(
        "-s",
        "--section",
        help="Restrict processing to given section"
    )
    parser.add_argument(
        "-m",
        "--do-merge",
        action="store_true",
        help="Merge readings that look identical"
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="turn on verbose output"
    )

    args = parser.parse_args()

    # Create a session and use it to log into Stemmaweb
    s = requests.Session()
    stemmaweb_login(args.username, args.password, s)

    # Go do the work.
    if args.do_merge:
        merge_identical_across_ranks(args, s)
    make_obvious_relations(args, s)
    print("Done!")
