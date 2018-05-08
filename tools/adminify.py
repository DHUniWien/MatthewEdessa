#!/usr/bin/env python

import argparse
import json
import requests
from prettytable import PrettyTable

def listusers(url):
    r = requests.get("%s/users" % url)
    r.raise_for_status()
    t = PrettyTable(['ID', 'email', 'role'])
    for record in r.json():
        t.add_row([record['id'], record['email'], record['role']])
    print(t)


def upgradeuser(url, userid):
    r = requests.get("%s/user/%s" % (url, userid))
    r.raise_for_status()
    record = r.json()
    if record['role'] == "admin":
        print("User %s is already an admin" % userid)
        return

    record['role'] = "admin"
    headers = {"content-type": "application/json"}
    r = requests.put("%s/user/%s" % (url, userid), headers=headers, data=json.dumps(record))
    r.raise_for_status()
    listusers(url)

if __name__ == '__main__':
    argp = argparse.ArgumentParser(description="Promote stemmarest users to admins")
    argp.add_argument('-l', '--list', action="store_true", help="List the existing users and exit")
    argp.add_argument('-u', '--user', help="The ID of the user to upgrade")
    argp.add_argument('--url', default="https://api.editions.byzantini.st/ChronicleMETest/stemmarest",
        help="The base URL of the stemmarest API to query")
    options = argp.parse_args()

    if options.list is False and options.user is None:
        print("Please specify either -l or -u")
        exit()

    if options.list:
        listusers(options.url)
        exit()

    if options.user is not None:
        upgradeuser(options.url, options.user)
        exit()
