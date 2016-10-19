from lxml import etree
from multiprocessing import Pool
import os
import time


def parsexml(xml):
    parser = etree.XMLParser(huge_tree=True)

    def get_fields(parsed):
        if len(parsed) > 3:
            date = parsed[0]
            typ = parsed[1]
            i = parsed[2]
            title = ''

            if len(parsed) == 4:
                text= parsed[3]
            else:
                title = parsed[3]
                text = ' '.join(parsed[4:])

            c_dict = {
                'date': date,
                'type': typ,
                'id': i,
                'title': title,
                'text': text,
            }
            return c_dict
        return {}

    try:
        tree = etree.parse(xml, parser=parser)
    except:
        print(Exception)
        print(xml, 'failed')
        return []
    print('opened', xml)
    t = time.time()
    parsed = (get_fields(text) for child in tree.getroot().iterchildren()
              for text in child.itertext())
    print('parsing took', time.time() -t )
    print('writing to disk')
    # RENS HIER KOMT JE CODE JONGE!

p = Pool(4)
folder = '/home/jim/data/'
t = time.time()
files = [os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
             if f[-3:] == 'xml']
p.map(parsexml, files)
print(time.time() - t)
