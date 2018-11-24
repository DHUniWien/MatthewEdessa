import argparse
import json
from lxml import etree
from lxml.etree import XMLSyntaxError
import os
import requests
from requests.auth import HTTPBasicAuth
from requests.exceptions import HTTPError
import sys


GRAPMLNS = 'http://graphml.graphdrawing.org/xmlns'


def fetch_graphml(options):
    """Download the GraphML for all the requested sections, and return
    a parsed etree object for each."""
    authobj = None
    if options.username is not None:
        authobj = HTTPBasicAuth(options.username, options.password)
    url = "%s/tradition/%s/sections" % (options.repository, options.tradition)
    r = requests.get(url, auth=authobj)
    r.raise_for_status()
    sectxml = []
    for sect in r.json():
        if sect.get('name') in options.section:
            if options.verbose:
                print("Retrieving section %s / %s" %
                    (sect.get('id'), sect.get('name')), end='', file=sys.stderr)
            url = "%s/tradition/%s/section/%s/graphml" % (
                options.repository, options.tradition, sect.get('id')
            )
            x = requests.get(url, auth=authobj)
            try:
                x.raise_for_status()
            except HTTPError as e:
                print("Got error %s on section %s"
                    % (e.response.text), sect.get('name'), file=sys.stderr)
                continue
            x.encoding = 'utf-8'
            try:
                xmlobj = etree.fromstring(x.content)
                sectxml.append(xmlobj)
                if options.verbose:
                    print("...retrieved.", file=sys.stderr)
            except XMLSyntaxError as e:
                print("Got XML parsing error %s" % (e.msg), file=sys.stderr)
    return sectxml


def make_matrix(sectionlist, mergelist, outputtype, outfile, verbose=False):
    """Iterate through the list of sections building a matrix of
    variants, and return the matrix in the specified form."""
    witlines = {}
    total = 0
    for sect in sectionlist:
        matrix = _process(sect, mergelist, verbose=verbose)
        sectwits = matrix.pop(0)
        if verbose:
            print("Section %s has witnesses %s"
                % (_retrieve_name(sect), sectwits))
        sectlen = len(matrix)
        seen = set()
        for i, w in enumerate(sectwits):
            seen.add(w)
            if w not in witlines:
                if total > 0 and verbose:
                    print("Adding missing elements to new witness %s" % w)
                witlines[w] = ['#MISSING#'] * total
            witlines[w].extend([r[i] for r in matrix])
        for w in witlines.keys():
            if w not in seen:
                if verbose:
                    print("Adding missing elements to skipped witness %s" % w)
                witlines[w].extend(['#MISSING#'] * sectlen)
        total += sectlen

    witnesslist = sorted(witlines.keys())
    mlen = len(witlines.get(witnesslist[0]))
    fullmatrix = [witnesslist]
    for i in range(mlen):
        fullmatrix.append([witlines.get(x)[i] for x in witnesslist])

    if outputtype == 'nexus':
        return(_make_nexus(fullmatrix, outfile))
    elif outputtype == 'pars':
        return(_make_pars(fullmatrix, outfile))
    elif outputtype == 'rhm':
        return(_make_rhm(fullmatrix, outfile))


def _retrieve_name(section):
    namekey = None
    typekey = None
    for kel in section.xpath('g:key[@for="node"]', namespaces={'g':GRAPMLNS}):
        if kel.get('attr.name') == 'name':
            namekey = kel.get('id')
        elif kel.get('attr.name') == 'neolabel':
            typekey = kel.get('id')
    if typekey is not None:
        sectnodes = section.xpath(
            './/g:node/g:data[@key="%s" and text()="[SECTION]"]/..' % typekey,
            namespaces={'g': GRAPMLNS})
        if sectnodes is not None:
            names = sectnodes[0].xpath('./g:data[@key="%s"]/text()' % namekey,
                namespaces={'g': GRAPMLNS})
            if len(names) > 0:
                return names[0]
    return 'Unknown'



def _process(sectionxml, mergelist, verbose=False):
    """Return a list of witness-ordered rows containing some representation
    of the reading for the respective rank."""
    nodemap = {}
    edgemap = {}
    graph = None
    # First get the property key map
    for child in sectionxml:
        if child.tag == "{%s}key" % GRAPMLNS:
            if child.get("for") == "node":
                nodemap[child.get("attr.name")] = child.get("id")
            else:
                edgemap[child.get("attr.name")] = child.get("id")
        elif child.tag == "{%s}graph" % GRAPMLNS:
            graph = child
    # Then make our little graph node/edge lookup function
    def _nodeprop(el, key):
        return _get_property(el, key, nodemap)
    def _edgeprop(el, key):
        return _get_property(el, key, edgemap)

    # Now dig the information we need out of the graph
    ranks = {}
    witnesses = set()
    readingwits = {}
    equivalent = {}
    # Make the rank buckets
    for node in graph.xpath('g:node', namespaces={'g': GRAPMLNS}):
        if 'READING' in _nodeprop(node, 'neolabel'):
            # Put it in its rank bucket to process later.
            rank = int(_nodeprop(node, "rank"))
            if rank > 0 and _nodeprop(node, "is_end") is None:
                _dict_append(ranks, rank, node)

    # Get the witness information per reading and overall
    sequencexpath = 'g:edge/g:data[@key="%s" and text()="SEQUENCE"]/..' % \
        edgemap.get('neolabel')
    for seq in graph.xpath(sequencexpath, namespaces={'g': GRAPMLNS}):
        # Extract witness info from the sequences
        sourcerdg = seq.get('source')
        witstr = _edgeprop(seq, 'witnesses')
        if witstr is not None:
            for wit in _parse_wits(witstr):
                witnesses.add(wit)
                _dict_append(readingwits, sourcerdg, wit)
        # TODO deal with the layer readings in a separate step

    # Make the relation buckets
    if mergelist is not None:
        relationxpath = 'g:edge/g:data[@key="%s" and text()="RELATED"]/..' % \
            edgemap.get('neolabel')
        for rel in graph.xpath(relationxpath, namespaces={'g': GRAPMLNS}):
            type = _edgeprop(rel, 'type')
            if type in mergelist:
                # Make the target equivalent to the source
                source = rel.get('source')
                target = rel.get('target')
                equiv = equivalent.get(target, source)
                equivalent[target] = equiv

    # Now go rank by rank, producing a list of (equivalent) readings ordered
    # by witness.
    witnessrow = sorted(witnesses)
    ourmatrix = [witnessrow]
    for rank in sorted(ranks):
        seenwits = set()
        wit2rdg = {}
        rdg2txt = {}
        rankrdgs = []
        for rdg in ranks.get(rank):
            rid = rdg.get('id')
            rdg2txt[rid] = _nodeprop(rdg, 'text')
            for wit in readingwits.get(rid, []):
                seenwits.add(wit)
                wit2rdg[wit] = equivalent.get(rid, rid)
        for wit in witnessrow:
            rankrdgs.append(rdg2txt.get(wit2rdg.get(wit, None), None))
        ourmatrix.append(rankrdgs)
    return ourmatrix


def _get_property(el, key, keymap):
    propkey = keymap.get(key, None)
    if propkey is not None:
        # print(el.tag)
        for datum in el: # these should all be 'data' elements
            if datum.get('key', None) == propkey:
                return datum.text
    return None


def _dict_append(d, k, v):
    l = d.get(k, [])
    l.append(v)
    d[k] = l

def _parse_wits(wstr):
    return wstr.replace('[', '').replace(']', '').split(', ')


def _make_nexus(matrix, target):
    pass

def _make_rhm(matrix, target):
    try:
        os.mkdir(target)
    except FileExistsError:
        pass
    witnessrow = matrix.pop(0)
    for idx, sigil in enumerate(witnessrow):
        fn = "%s/%s" % (target, sigil)
        with open(fn, 'w+', encoding="utf-8") as fh:
            words = [x[idx] for x in matrix]
            for w in words:
                if w == '#MISSING#' or w is None:
                    w = ''
                fh.write("%s\n" % w)
    print("RHM input available in %s directory." % target)


def _make_pars(matrix, target):
    witnessrow = matrix.pop(0)
    print(witnessrow)
    witchars = {}
    final_length = 0
    for rdgrow in matrix:
        rowrdgs = set(rdgrow)
        repr = {}
        base = 0
        for rdg in rowrdgs:
            if rdg is None:
                repr[rdg] = 'X'
            elif rdg == '#MISSING#':
                repr[rdg] = '?'
            else:
                repr[rdg] = chr(65 + base)
                base += 1
        if base < 8:
            final_length += 1
            for idx, wit in enumerate(witnessrow):
                _dict_append(witchars, wit, repr[rdgrow[idx]])
    with open(target, 'w+') as fh:
        # Print the header counts
        fh.write("\t%d\t%d\n" % (len(witnessrow), final_length))
        for wit in witnessrow:
            fh.write("%-10s%s\n" % (wit, ' '.join(witchars.get(wit))))
    print("Pars input available in file %s." % target)



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
        "--tradition",
        required=True,
        help="ID of tradition to process"
    )
    parser.add_argument(
        "-s",
        "--section",
        action="append",
        help="Specify section(s) to use for analysis"
    )
    parser.add_argument(
        "-m",
        "--merge",
        action="append",
        help="Specify relation type(s) to treat as the same reading"
    )
    parser.add_argument(
        "-o",
        "--outfile",
        default="infile",
        help="Name of file (or, for RHM, directory) to write the output to"
    )

    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument(
        "--nexus",
        dest="output",
        action="store_const",
        const="nexus",
        help="Return Nexus-compatible character matrix"
    )
    output.add_argument(
        "--pars",
        dest="output",
        action="store_const",
        const="pars",
        help="Return Pars-compatible reading matrix"
    )
    output.add_argument(
        "--rhm",
        dest="output",
        action="store_const",
        const="rhm",
        help="Return RHM-compatible reading matrix"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="turn on verbose output"
    )

    args = parser.parse_args()
    sectiondata = fetch_graphml(args)
    make_matrix(sectiondata,
        args.merge, args.output, args.outfile, verbose=args.verbose)
