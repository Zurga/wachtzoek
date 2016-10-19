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

    with open(xml) as file:
        raw = file.read().replace('<?xml version="1.0" encoding="UTF-8"?>', '')
        try:
            tree = etree.parse(parser=parser)
        except:
            print(xml, 'failed')
            return []
    print('opened', xml)
    return [get_fields(text) for child in tree.iterchildren()
            for text in child.itertext()]

p = Pool(4)
folder = '/mnt/Telegraaf/'
files = [os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
             if f[-3:] == 'xml']
dicts = p.map(parsexml, files)
