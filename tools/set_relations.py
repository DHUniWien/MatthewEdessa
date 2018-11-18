import argparse
import json
import re
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError


def make_obvious_relations(options, auth=None):
    """Connects to a Stemmarest URL, goes section by section through
    the readings, and tries to make relationships based on normal form,
    case folding, and a few other custom parameters."""
    url = "%s/tradition/%s" % (options.repository, options.tradition_id)
    for section in get_sections(url, options.section, auth):
        print("Working on section %s" % section.get('name'))
        apply_relations(url, section.get('id'), auth=auth, verbose=options.verbose)


def get_sections(url, requested, auth=None):
    if auth is not None:
        r = requests.get("%s/sections" % url, auth=auth)
    else:
        r = requests.get("%s/sections" % url)
    r.raise_for_status()
    if requested is not None:
        return [s for s in r.json() if s.get('name') == requested]
    return r.json()


def apply_relations(url, sectid, auth=None, verbose=False):
    rdgurl = "%s/section/%s/readings" % (url, sectid)
    if auth is not None:
        r = requests.get(rdgurl, auth=auth)
    else:
        r = requests.get(rdgurl)
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
                elif test_equiv(thisrdg, otherrdg):
                    relation_stack.append((thisrdg, otherrdg, 'spelling'))

    make_relations("%s/relation" % url, relation_stack, auth=auth, verbose=verbose)


def sort_by_rank(rdglist):
    rankdict = {}
    for rdg in rdglist:
        rk = rdg.get('rank')
        if rk in rankdict:
            rankdict.get(rk).append(rdg)
        else:
            rankdict[rk] = [rdg]
    return rankdict


def test_equiv(rdg1, rdg2):
    equiv = rdg1.get('normal_form') == rdg2.get('normal_form') or \
            rdg1.get('normal_form') == rdg2.get('text') or \
            rdg1.get('text') == rdg2.get('normal_form')
    t1 = _make_cmp_string(rdg1.get('text').lower())
    t2 = _make_cmp_string(rdg2.get('text').lower())
    n1 = _make_cmp_string(rdg1.get('normal_form').lower())
    n2 = _make_cmp_string(rdg2.get('normal_form').lower())
    return t1 != '' and t2 != '' and (t1 == t2 or t1 == n2 or t2 == n1)


def _make_cmp_string(s):
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
    s = re.sub('ցձ', 'ծ', s)   # same except for alveolar affricates
    s = re.sub('փ', 'ֆ', s)   # same exceot for 'f' forms
    s = re.sub('[ւվ]', 'ու', s)   # same except for v/w forms
    s = re.sub('ո', 'օ', s)   # same except for long/short o
    s = re.sub('ր', 'ռ', s)   # same except for r forms
    return s


def make_relations(url, stack, auth=None, verbose=False):
    for rtuple in stack:
        relmodel = {
            'source': rtuple[0].get('id'),
            'target': rtuple[1].get('id'),
            'type': rtuple[2],
            'annotation': 'automatically created',
            'scope': 'local'
        }
        headers={'Content-Type': 'application/json'}
        if auth is not None:
            r = requests.post(url, data=json.dumps(relmodel), headers=headers, auth=auth)
        else:
            r = requests.post(url, data=json.dumps(relmodel), headers=headers)

        prettyprint = "%s/%s and %s/%s (%s)" % \
                      (rtuple[0].get('rank'), rtuple[0].get('text'), rtuple[1].get('rank'), rtuple[1].get('text'), rtuple[2])
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


def merge_identical_across_ranks(options, auth=None):
    url = "%s/tradition/%s" % (options.repository, options.tradition_id)
    for section in get_sections(url, options.section, auth):
        print("Checking mergeable readings in section %s" % section.get('name'))
        murl = "%s/section/%s/mergeablereadings/1/%s" % \
            (url, section.get('id'), section.get('endRank'))
        r = requests.get(murl, auth=auth)
        r.raise_for_status()

        # We have a list of mergeable readings. Do two passes; first for
        # function words and then for punctuation.
        mergetargets = {}
        punct = []
        for pair in r.json():
            (r1, r2) = pair
            if _mergeable(*pair):
                if re.search(r'\w', r1.get('text')):
                    r1 = mergetargets.get(r1.get('id'), r1)
                    r2 = mergetargets.get(r2.get('id'), r2)
                    mgurl = "%s/reading/%s/merge/%s" % \
                        (options.repository, r1.get('id'), r2.get('id'))
                    if _attempt_merge(mgurl, r1, r2, auth=auth, verbose=options.verbose):
                        mergetargets[r2.get('id')] = r1
                else:
                    punct.append(pair)

        # Now for the punctuation.
        for pair in punct:
            (r1, r2) = pair
            if _mergeable(*pair):
                r1 = mergetargets.get(r1.get('id'), r1)
                r2 = mergetargets.get(r2.get('id'), r2)
                mgurl = "%s/reading/%s/merge/%s" % \
                    (options.repository, r1.get('id'), r2.get('id'))
                if _attempt_merge(mgurl, r1, r2, auth=auth, verbose=options.verbose):
                    mergetargets[r2.get('id')] = r1



def _mergeable(r1, r2):
    a = "%s|%s|%s" % (r1.get('text'), r1.get('normal_form'), r1.get('display'))
    b = "%s|%s|%s" % (r2.get('text'), r2.get('normal_form'), r2.get('display'))
    return a == b



def _attempt_merge(url, r1, r2, auth=None, verbose=False):
    if verbose:
        print("Attempting merge of %s/%s and %s/%s" % \
              (r1.get('id'), r1.get('text'),
               r2.get('id'), r2.get('text')), end='', flush=True)
    r = requests.post(url, auth=auth)
    try:
        r.raise_for_status()
    except HTTPError as e:
        if verbose:
            print("failed: %s" % e.response.text)
        return False
    if verbose:
        print("...succeeded")
    return True


# Do the work
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    server = parser.add_argument_group('Stemmarest server connection')
    server.add_argument(
        "-r",
        "--repository",
        required=True,
        help="URL to tradition repository"
    )
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

    # Make an authentication object if we need to
    if args.username is not None:
        authobj = HTTPBasicAuth(args.username, args.password)

    # Go do the work.
    if args.do_merge:
        merge_identical_across_ranks(args, auth=authobj)
    make_obvious_relations(args, auth=authobj)
    print("Done!")
