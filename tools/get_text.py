import json
import sys
from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import from_etree

with open(sys.argv[1], encoding='utf-8') as jfile:
	msdata = json.load(jfile)
xmltree = from_sc(msdata)
tokens = from_etree(xmltree) # add 421letter as second arg if necessary
words = [ t['t'] for t in tokens ]
string = ' '.join(words)
sys.stdout.buffer.write(string.encode('utf-8'))