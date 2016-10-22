from lxml import etree
from multiprocessing import Process
from multiprocessing import Queue
import os
import time
from pyelasticsearch import ElasticSearch, utils


class Worker(Process):
    def __init__(self, in_q, out_q):
        super(Worker, self).__init__()
        self.in_q = in_q
        self.out_q = out_q

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
                break

            tag = '{http://www.policticalmashup.nl}root'
            t = time.time()
            tree = etree.iterparse(xml, events=('end',), tag=tag)
            parsed = []
            for event, elem in tree:
                parsed.append(self.get_fields(list(elem.itertext())))
                elem.clear()
            print('doing', xml)
            self.out_q.put(parsed)
            print('did', xml, 'took', time.time() - t)


class StoreWorker(Process):
    def __init__(self, out_q):
        super(StoreWorker, self).__init__()
        self.out_q = out_q

    def run(self):
        while True:
            articles = self.out_q.get()
            if articles is None:
                break
            for chunk in utils.bulk_chunks(articles, docs_per_chunk=200):
                es.bulk(chunk, index='telegraaf', doc_type='artikel')
            del articles

es = ElasticSearch('http://localhost:9200')
try:
    es.delete_index('telegraaf')
except:
    print('index did not exist')

folder = input('Geef de naam van de data folder')
# folder = '/home/jim/data/'
t = time.time()
files = [os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
         if f[-3:] == 'xml']

in_q = Queue()
out_q = Queue()
workers = [Worker(in_q, out_q) for _ in range(2)]
storer = StoreWorker(out_q)

for f in sorted(files):
    in_q.put(f)

for i in range(2):
    workers[i].start()

storer.start()
print('Going for it!')

storer.join()
print(time.time() - t)
