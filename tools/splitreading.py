import argparse
import json
import requests

STEMMAWEB_URL="https://stemmaweb.net/stemmaweb"
#STEMMAWEB_URL="http://localhost:3000"

def stemmaweb_login(uname, pword):
    """Try to log into Stemmaweb, and return the cookie we get"""
    CREDENTIALS = {
        'username': uname, 
        'password': pword 
    }
    r = requests.post(STEMMAWEB_URL + "/login", data=CREDENTIALS)
    r.raise_for_status()
    return r.cookies


# Make the request to split the reading
def split_reading(cookiejar, options):
    """Make the request to split the reading"""
    BASEURL = STEMMAWEB_URL + "/api/" + options.tradition_id
    headers = {'Content-Type': 'application/json'}
    spec = {'character': options.character, 
            'separate': options.separate, 
            'isRegex': options.isRegex}
    r = requests.post(BASEURL + "/reading/%d/split/%d" 
                        % (options.reading, options.index), 
                      headers=headers, 
                      data=json.dumps(spec),
                      cookies=cookiejar)
    if r.status_code > 399:
        print(r.text)
    else:
        print(r.json())


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
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

    ops = parser.add_argument_group('Reading split operation')
    ops.add_argument(
        "-r",
        "--reading",
        type=int,
        help="ID of reading to split"
    )
    ops.add_argument(
        "-i",
        "--index",
        type=int,
        default=0,
        help="Index of the character where the reading should be split"
    )
    ops.add_argument(
        "-c",
        "--character",
        default=" ",
        help="Character to split on (default: space)"
    )
    ops.add_argument(
        "-s",
        "--separate",
        action="store_true",
        help="Specify this if the readings should be space separated"
    )
    parser.add_argument(
        "-rx",
        "--isRegex",
        action="store_true",
        help="Specify this if "
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="turn on verbose output"
    )

    args = parser.parse_args()

    # Log in to Stemmaweb
    cookies = stemmaweb_login(args.username, args.password)
    split_reading(cookies, args)

