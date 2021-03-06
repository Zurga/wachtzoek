import http
from lxml import etree
from multiprocessing import Process
from multiprocessing import Queue
import os
import time
import gc
from elasticsearch import Elasticsearch, helpers, \
    client


class Worker(Process):
    def __init__(self, in_q, last, num_p):
        super(Worker, self).__init__()
        self.in_q = in_q
        self.last = last
        self.num_docs = 0
        self.num_p = num_p

    def tokenize(self, text):
        for token in text.split():
            if token.isalpha():
                yield token

    def get_fields(self, elem):
        namespaces = {'pm':'http://www.politicalmashup.nl',
                    'dc': 'http://purl.org/dc/elements/1.1/'}
        date = elem.xpath('pm:meta/dc:date', namespaces=namespaces)[0].text
        typ = elem.xpath('pm:meta/dc:subject', namespaces=namespaces)[0].text.replace(' ', '_')
        text = ' '.join(e.text for e in elem.xpath('pm:content/text/p',
                                                   namespaces=namespaces)
                        if e.text)
        title = elem.xpath('pm:content/title', namespaces=namespaces)[0].text

        c_dict = {
            'date': date,
            'type': typ,
            'id': i,
            'title': title,
            'text': text,
        }
        return {'_op_type': 'index',
                '_type': 'document',
                '_index': 'telegraaf',
                '_source': c_dict,
                }

    def run(self):
        print('started')

        while True:
            xml = self.in_q.get()
            if xml is None:
                print('Stopping Worker, blegh i am ded')
                print('parsed this many documents', self.num_docs)
                break

            tag = '{http://www.politicalmashup.nl}root'
            tree = etree.iterparse(xml, events=('end',), tag=tag)
            t = time.time()
            actions = []

            print('doing', xml)
            for event, elem in tree:
                actions.append(self.get_fields(elem))
                elem.clear()

            self.num_docs += len(actions)

            try:
                for ret in helpers.parallel_bulk(es, actions, thread_count=2,
                                                chunk_size=100):
                    del ret
            except Exception as e:
                print(e, xml)
                pass

            del tree
            del actions
            gc.collect()
            if self.last == xml:
                for i in range(self.num_p):
                    self.in_q.put(None)

            print('did', xml, 'in', time.time() - t, 'seconds')

es = Elasticsearch('http://localhost:9200')
indices_client = client.IndicesClient(es)
if indices_client.exists('telegraaf'):
    print('deleting index')
    indices_client.delete('telegraaf')
print('making index')
settings = {"index": {
            "refresh_interval": -1,
            'number_of_replicas': 0
            },
            'indices': {
                'memory': {
                    'index_buffer_size': 512
                }
            },
        }

mappings = {"document":{
    "properties":{
        "title":{"type":"string"},
        "text":{"type":"string"},
        "date":{"type":"date","format":"yyyy-MM-dd"},
        "type":{"type":"string"},
            }
        }
    }
indices_client.create('telegraaf', {'settings': settings,
                                    'mappings': mappings})

folder = input('Geef de naam van de data folder: ')
if not folder.endswith('/'):
    folder = folder + '/'

files = sorted([os.path.abspath(folder+f) for f in
                os.listdir(os.path.abspath(folder))
                if f[-3:] == 'xml'])

num_p = 2
in_q = Queue()
workers = [Worker(in_q, files[-1], num_p) for _ in range(num_p)]

for f in files:
    in_q.put(f)

print('Going for it!')
t = time.time()
for i in range(num_p):
    workers[i].start()

for worker in workers:
    worker.join()

num_docs = sum(w.num_docs for w in workers)
print('Nog even goed instellen :D')
indices_client.put_settings({"index": {"refresh_interval": "1s",
                                       'number_of_replicas': 0}}, 'telegraaf')
print('We zijn klaar, joeeeeeeeeeee')

print(time.time() - t)
