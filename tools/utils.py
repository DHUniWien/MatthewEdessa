
import argparse

STEMMAWEB_URL="https://stemmaweb.net/stemmaweb"

def stemmaweb_login(uname, pword, session, apibase=STEMMAWEB_URL):
    """Try to log into Stemmaweb with the given credentials, and
    store the results in the given session. If we are successful,
    return the base URL for API calls."""
    CREDENTIALS = {
        'username': uname, 
        'password': pword 
    }
    r = session.post(apibase + "/login", data=CREDENTIALS)
    r.raise_for_status()
    return apibase + "/api"


def arg_parser():
    "Return an argument parser object with the usual options we need"
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
    server.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="turn on verbose output"
    )
    return parser
