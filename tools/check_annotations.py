import json
import re
import requests
import sys
import time
from requests.auth import HTTPBasicAuth

ENDPOINT = "https://api.editions.byzantini.st/ChronicleME/stemmarest"
TRADID = "4aaf8973-7ac9-402a-8df9-19a2a050e364"
# TRADID = "7c650e59-4a6c-4075-b245-a395e27b474e"
authobj = HTTPBasicAuth('tla', 'pi-fi-ghor')

## What to do if we find a duplicate
def print_duplicate_info(first, second, section):
    atype = existing['label']
    baseurl = "%s/tradition/%s/section/%s/annotation/" % (ENDPOINT, TRADID, section['id'])
    # Find the respective referent of the two entities
    r = requests.get(baseurl + first['id'] + '/referents')
    r.raise_for_status()
    fref = [x for x in r.json() if x['label'] != 'TRADITION']
    r = requests.get(baseurl + second['id'] + '/referents')
    r.raise_for_status()
    sref = [x for x in r.json() if x['label'] != 'TRADITION']


## Go through section by section
if __name__ == '__main__':
    r = requests.get("%s/tradition/%s/sections" % (ENDPOINT, TRADID))
    r.raise_for_status()
    sectionlist = r.json()
    for section in sectionlist:
        print("Checking section " + section['name'])
        requrl = "%s/tradition/%s/section/%s/annotations" % (ENDPOINT, TRADID, section['id'])
        r = requests.get(requrl)
        r.raise_for_status()
        seen = dict()
        for anno in r.json():
            atype = anno['label']
            if 'REF' in atype:
                rb = None
                re = None
                for l in anno['links']:
                    if l['type'] == 'BEGIN':
                        rb = l['target']
                    elif l['type'] == 'END':
                        re = l['target']
                if rb is not None and re is not None:
                    hkey = "%s/%d/%d" % (atype, rb, re)
                    if hkey in seen:
                        existing = seen[hkey]
                        print("Duplicate found: %s vs. %s" % (existing['id'], anno['id']))
                    else:
                        seen[hkey] = anno

    print("Done")
