import json
import os
import requests
import sys
import time
from io import BytesIO

if __name__ == '__main__':
    scfile = sys.argv[1]
    # Get the JSON
    with open(scfile, encoding='utf-8') as f:
        scjson = json.load(f)
    # Get the project name and make the corresponding subdir
    dname = '.'
    for md in scjson['metadata']:
        if md['label'] == 'title':
            dname = md['value']
            try:
                os.mkdir(dname)
            except FileExistsError:
                pass
    # Loop through the canvases and download the images
    canvases = scjson['sequences'][0]['canvases']
    total = len(canvases)
    curr = 0
    for canvas in canvases:
        curr += 1
        imgfn = canvas['label']
        url = canvas['images'][0]['resource']['@id']
        print("Downloading from %s (%d/%d)" % (url, curr, total))
        r = requests.get(url)
        r.raise_for_status()
        with open("%s/%s" % (dname, imgfn), 'w+b') as imgf:
            imgf.write(r.content)
        time.sleep(15)
    print("Done!")
