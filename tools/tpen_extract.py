import json
import sys

msdata = None
with open(sys.argv[1], encoding='utf-8') as jfile:
    msdata = json.load(jfile)

pages = msdata['sequences'][0]['canvases']
for page in pages:
    print("--- Image %s" % page['label'])
    for line in page['otherContent'][0]['resources']:
        print(line['resource']['cnt:chars'])