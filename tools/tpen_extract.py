import json
import sys

msdata = None
with open(sys.argv[1], encoding='utf-8') as jfile:
    msdata = json.load(jfile)

pgtag = None
if len(sys.argv) > 2:
    pgtag = sys.argv[2]

pages = msdata['sequences'][0]['canvases']
lines = []
for page in pages:
    if pgtag is not None and page['label'].find(pgtag) < 0:
        continue
    pglines = [x['resource']['cnt:chars'] for x in page['otherContent'][0]['resources']]
    lines.append('\n'.join(pglines))

print(''.join(lines))
