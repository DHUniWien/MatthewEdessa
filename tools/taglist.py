#!/usr/bin/env python

import sys
from lxml import etree

tags = set()

for file in sys.argv[1:]:
    xmldoc = etree.parse(file).getroot()
    track = False
    for el in xmldoc.iter():
        if track:
            tags.add(el.tag)
        if el.tag == '{http://www.tei-c.org/ns/1.0}ab':
            track = True
        
print("\n".join(sorted(tags)))