import json
import sys

msdata = None
with open(sys.argv[1], encoding='utf-8') as jfile:
    msdata = json.load(jfile)

pages = msdata['sequences'][0]['canvases']
lines = []
for page in pages:
    pglines = [x['resource']['cnt:chars'] for x in page['otherContent'][0]['resources']]
    lines.append(''.join(pglines))

print(''.join(lines))
