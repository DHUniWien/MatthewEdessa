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

spec = []
label = {}

with open(sys.argv[1], encoding='utf-8') as f:
    for l in f:
        ## If we start with a label name, start a new hash
        line = l.rstrip()
        if (line.startswith('*')):
            if (line.find(':') > -1):
                # It is a property for the existing label
                m = re.match(r'\*\s+(\S+)\s?:\s+(\S+)', line)
                if m is not None:
                    pname = m.group(1)
                    ptype = m.group(2)
                    props = label.get('properties', dict())
                    label['properties'] = props
                    props[pname] = ptype
                else:
                    raise Exception('Could not parse line ' + line)
            elif (line.find('<-') > -1):
                # It is a link for the existing label
                m = re.match(r'\*\s+(\S+)\s?<-\s+(\S+)', line)
                if m is not None:
                    lnode = m.group(1)
                    ltype = m.group(2)
                    links = label.get('links', dict())
                    label['links'] = links
                    links[lnode] = ltype
                else:
                    raise Exception('Could not parse line ' + line)
        elif len(line) > 0 and line[0].isalpha():
            # It is a new label name, so start a new hash
            if 'name' in label: spec.append(label)
            label = {'name': line}

# Get the last label
if 'name' in label: spec.append(label)

for item in spec:
    url = ENDPOINT + '/tradition/' + TRADID + '/annotationlabel/' + item.get('name')
    print("Input: " + json.dumps(item))
    r = requests.put(url,
                     data=json.dumps(item),
                     headers={'Content-Type': 'application/json'},
                     auth=authobj)
    print("Output: " + json.dumps(r.json()))
    r.raise_for_status()
