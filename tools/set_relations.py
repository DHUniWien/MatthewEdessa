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
    if auth is not None:
        r = requests.get("%s/sections" % url, auth=auth)
    else:
        r = requests.get("%s/sections" % url)
    r.raise_for_status()
    for section in r.json():
        if options.section is not None:
            if section.get('name') != options.section:
                continue
        print("Working on section %s" % section.get('name'))
        apply_relations(url, section.get('id'), auth=auth, verbose=options.verbose)


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
            rdg1.get('text') == rdg2.get('normal_form') or \
            rdg1.get('text').lower() == rdg2.get('text').lower()
    # Some experimental spelling assumptions
    t1 = rdg1.get('text')
    t2 = rdg2.get('text')
    if re.sub(r'\W+', '', t1) == re.sub(r'\W+', '', t2) \
        and re.search(r'\w+', t1) is not None:
        return True
    if re.sub('ը', '', t1) == re.sub('ը', '', t2):
        return True
    if re.sub('աւ', 'օ', t1) == re.sub('աւ', 'օ', t2):
        return True
    if re.sub(r'(?:[աո])՛$', 'յ', t1) == re.sub(r'(?:[աո])՛$', 'յ', t2):
        return True
    # If none of these matter, return the formal equivalence
    return equiv


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
    make_obvious_relations(args, auth=authobj)
    print("Done!")
