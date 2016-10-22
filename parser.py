import sys
from lxml import etree
import json
from multiprocessing import Process
from multiprocessing import Queue
import os
import time
import gc
from pyelasticsearch import ElasticSearch, utils


class Worker(Process):
    def __init__(self, in_q, out_q, last, num_p):
        super(Worker, self).__init__()
        self.in_q = in_q
        self.out_q = out_q
        self.last = last
        self.num_p = num_p

    def get_fields(self, parsed):
        if len(parsed) > 3:
            date = parsed[0]
            typ = parsed[1]
            i = parsed[2]
            title = ''

            if len(parsed) == 4:
                text = parsed[3]
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

    def run(self):
        print('started')

        while True:
            xml = self.in_q.get()
            if xml is None:
                print('Stopping Worker, blegh i am ded')
                gc.collect()
                self.terminate()
                sys.exit()

            tag = '{http://www.politicalmashup.nl}root'
            parsed = []
            t = time.time()
            tree = etree.iterparse(xml, events=('end',), tag=tag)

            #print('doing', xml)

            for event, elem in tree:
                parsed.append(self.get_fields(list(elem.itertext())))
                elem.clear()

            del tree
            gc.collect()
            self.out_q.put((parsed, xml))
            if self.last == xml:
                print(self.last, xml)
                print('sending none to store')
                self.out_q.put((None,None))
                for i in range(self.num_p):
                    self.in_q.put(None)
            # print('did', xml, 'in', time.time() - t, 'seconds')


class StoreWorker(Process):
    def __init__(self, out_q):
        super(StoreWorker, self).__init__()
        self.out_q = out_q

    def run(self):
        while True:
            articles = self.out_q.get()
            if articles is None:
                print('Stopping store')
                break
            print('articles inserting', len(articles))
            for chunk in utils.bulk_chunks([es.index_op(a) for a in articles], docs_per_chunk=200):
                es.bulk(chunk, index='telegraaf', doc_type='artikel')
                del chunk
            del articles
            gc.collect()
            print('stored something')

es = ElasticSearch('http://localhost:9200')
try:
    es.delete_index('telegraaf')
except:
    print('index did not exist')

folder = input('Geef de naam van de data folder')
if not folder.endswith('/'):
    folder = folder + '/'
# folder = '/home/jim/data/'
t = time.time()
files = sorted([os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
         if f[-3:] == 'xml'])

num_p = 3
in_q = Queue()
out_q = Queue()
workers = [Worker(in_q, out_q, files[-1], num_p) for _ in range(num_p)]
storer = StoreWorker(out_q)

for f in files:
    in_q.put(f)

for i in range(num_p):
    workers[i].start()

print('Going for it!')
storer.start()

for worker in workers:
    worker.join()

storer.join()
print('We zijn klaar, joeeeeeeeeeee')

out_q.put(None)
print(time.time() - t)
