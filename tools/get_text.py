import json
import sys
sys.path.append('transcription')
import config
from lxml import etree
from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import from_etree

with open(sys.argv[1], encoding='utf-8') as jfile:
	msdata = json.load(jfile)
xmltree = from_sc(msdata, metadata=config.metadata, special_chars=config.special_chars,
    numeric_parser=config.numeric_parser, text_filter=config.transcription_filter)

sys.stdout.buffer.write(etree.tostring(xmltree, encoding='utf-8', pretty_print=True, xml_declaration=True))