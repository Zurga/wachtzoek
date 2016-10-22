from lxml import etree
from multiprocessing import Pool
import os
import time
from elasticsearch import Elasticsearch
import pyelasticsearch

es = Elasticsearch(hosts=['http://localhost:9200/'])

def parsexml(xml):

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
        tree = etree.iterparse(xml, events=('end',), tag='root')
    except:
        print(Exception)
        print(xml, 'failed')
        return []
    t = time.time()
    parsed = []

    for event, elem in tree:
        parsed.append(get_fields(list(elem.itertext())))
        elem.clear()

    del tree
    return parsed
    print('parsing took', time.time() -t )
    print('writing to disk')
    # RENS HIER KOMT JE CODE JONGE!
    es.bulk(parsed)
'''
p = Pool(4)
folder = '../Telegraaf/telegraaf/'
t = time.time()
files = [os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
             if f[-3:] == 'xml']
p.map(parsexml, files)
print(time.time() - t)'''
