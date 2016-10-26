import sys
from lxml import etree
import json
from multiprocessing import Process
from multiprocessing import Queue
from threading import Thread
import os
import time
import gc
from elasticsearch import Elasticsearch, helpers
import nltk
import re
import string


class Worker(Process):
    def __init__(self, in_q, out_q, last, num_p):
        super(Worker, self).__init__()
        self.in_q = in_q
        self.out_q = out_q
        self.last = last
        self.num_p = num_p
        self.tokenize = nltk.word_tokenize
        self.stopwords = nltk.corpus.stopwords.words('dutch')
        self.table = str.maketrans(string.punctuation,
                                   chr(0) * len(string.punctuation))

    def tokenize(self, text):
        for token in text.split():
            if token.isalpha():
                yield token

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
                '''
                text = ' '.join(token for text in parsed[4:]
                t1 = time.time()
                                for token in text.split())
                t2 = time.time()
                '''
                text = ' '.join(t for t in parsed[4:])
                #print('second', time.time() -t2)

            c_dict = {
                'date': date,
                'type': typ,
                'id': i,
                'title': title,
                'text': text,
            }
            return {'_op_type': 'index',
                    '_type': 'document',
                    'index': 'telegraaf',
                    'doc': c_dict
                    }
        return {}

    def run(self):
        print('started')

        while True:
            xml = self.in_q.get()
            if xml is None:
                print('Stopping Worker, blegh i am ded')
                gc.collect()
                self.terminate()

            tag = '{http://www.politicalmashup.nl}root'
            parsed = []
            tree = etree.iterparse(xml, events=('end',), tag=tag)

            # print('doing', xml)

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
            articles, xml = self.out_q.get()
            if articles is None:
                print('Stopping store')
                break
            print('articles inserting', len(articles), 'from', xml)

            helpers.parallel_bulk(es, articles, thread_count=10,
                                  chunk_size=250)
            '''
            for chunk in utils.bulk_chunks(articles, docs_per_chunk=200):
                es.bulk(chunk, index='telegraaf', doc_type='artikel')
            '''
            print('stored something', xml)



es = Elasticsearch('http://localhost:9200')
try:
    es.delete_index('telegraaf')
except:
    print('index did not exist')

folder = input('Geef de naam van de data folder')
if not folder.endswith('/'):
    folder = folder + '/'
folder = '/home/jim/data/'
t = time.time()
files = sorted([os.path.abspath(folder+f) for f in os.listdir(os.path.abspath(folder))
         if f[-3:] == 'xml'])

num_p = 2
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
