import json
import sys
from lxml import etree
from tpen2tei.parse import from_sc
from tpen2tei.wordtokenize import from_etree

armenian_glyphs = {
    'աշխարհ': ('asxarh', 'ARMENIAN ASHXARH SYMBOL'),
    'ամենայն': ('amenayn', 'ARMENIAN AMENAYN SYMBOL'),
    'արեգակն': ('aregakn', 'ARMENIAN AREGAKN SYMBOL'),
    'լուսին': ('lusin', 'ARMENIAN LUSIN SYMBOL'),
    'որպէս': ('orpes', 'ARMENIAN ORPES SYMBOL'),
    'երկիր': ('erkir', 'ARMENIAN ERKIR SYMBOL'),
    'երկին': ('erkin', 'ARMENIAN ERKIN SYMBOL'),
    'ընդ': ('und', 'ARMENIAN END SYMBOL'),
    'ըստ': ('ust', 'ARMENIAN EST SYMBOL'),
    'պտ': ('ptlig', 'ARMENIAN PEH-TIWN LIGATURE'),
    'թե': ('techlig', 'ARMENIAN TO-ECH LIGATURE'),
    'թի': ('tinilig', 'ARMENIAN TO-INI LIGATURE'),
    'թէ': ('tehlig', 'ARMENIAN TO-EH LIGATURE'),
    'թբ': ('tblig', 'ARMENIAN TO-BEN LIGATURE'),
    'էս': ('eslig', 'ARMENIAN EH-SEH LIGATURE'),
    'ես': ('echslig', 'ARMENIAN ECH-SEH LIGATURE'),
    'յր': ('yrlig', 'ARMENIAN YI-REH LIGATURE'),
    'զմ': ('zmlig', 'ARMENIAN ZA-MEN LIGATURE'),
    'թգ': ('tglig', 'ARMENIAN TO-GIM LIGATURE'),
    'րզ': ('rzlig', 'ARMENIAN REH-ZA LIGATURE'),
    'ա': ('avar', 'ARMENIAN AYB VARIANT'),
    'հ': ('hvar', 'ARMENIAN HO VARIANT'),
    'յ': ('yabove', 'ARMENIAN YI SUPERSCRIPT VARIANT')
}

txninfo = {
    'title': 'Ժամանակագրութիւն',
    'author': 'Մատթէոս Ուռհայեցի'
}

with open(sys.argv[1], encoding='utf-8') as jfile:
	msdata = json.load(jfile)
xmltree = from_sc(msdata, metadata=txninfo, special_chars=armenian_glyphs)
# tokens = from_etree(xmltree) # add 421letter as second arg if necessary
# words = [ t['t'] for t in tokens ]
# string = ' '.join(words)
sys.stdout.buffer.write(etree.tostring(xmltree, encoding='utf-8', pretty_print=True, xml_declaration=True))