import argparse
import json
import requests

STEMMAWEB_URL="https://stemmaweb.net/stemmaweb"
#STEMMAWEB_URL="http://localhost:3000"

def stemmaweb_login(uname, pword, session):
    """Try to log into Stemmaweb, and return the cookie we get"""
    CREDENTIALS = {
        'username': uname, 
        'password': pword 
    }
    r = session.post(STEMMAWEB_URL + "/login", data=CREDENTIALS)
    r.raise_for_status()


# Make the request to split the reading
def split_section(session, options):
    """Make the request to split the section"""
    BASEURL = STEMMAWEB_URL + "/api/" + options.tradition_id

    # Were we called with a reading?
    if args.reading:
        r = session.get(BASEURL + "/reading/%d" % options.reading)
        r.raise_for_status
        rdg = r.json()
        splitRank = rdg.get('rank')
    else:
        splitRank = options.rank

    # headers = {'Content-Type': 'application/json'}
    r = session.post(BASEURL + "/section/%d/splitAtRank/%d" 
                        % (options.section_id, splitRank), 
                      )
    if r.status_code > 399:
        print(r.text)
    else:
        print(r.json())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split a section on a reading or a rank")
    server = parser.add_argument_group('Stemmaweb server connection')
    server.add_argument(
        "-u",
        "--username",
        help="Stemmaweb login username"
    )
    server.add_argument(
        "-p",
        "--password",
        help="Stemmaweb login password"
    )
    server.add_argument(
        "-t",
        "--tradition-id",
        required=True,
        help="ID of tradition to be modified"
    )
    server.add_argument(
        "-s",
        "--section-id",
        required=True,
        type=int,
        help="ID of section to be split"
    )

    ops = parser.add_mutually_exclusive_group(required=True)
    ops.add_argument(
        "-rdg",
        "--reading",
        type=int,
        help="ID of reading where the section should be split"
    )
    ops.add_argument(
        "-rk",
        "--rank",
        type=int,
        help="Rank where the section should be split"
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="turn on verbose output"
    )

    args = parser.parse_args()

    # Log in to Stemmaweb
    s = requests.Session()
    stemmaweb_login(args.username, args.password, s)
    split_section(s, args)

