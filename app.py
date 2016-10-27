import requests
import json
import string
import re

from flask import Flask, render_template, request, jsonify
from gensim.summarization import summarize as summ
from gensim.summarization import keywords as kw
from collections import Counter
from nltk.corpus import stopwords
from nltk import word_tokenize
from nltk.stem import SnowballStemmer

stemmer = SnowballStemmer('dutch')

ELASTICPORT = 9200
ELASTIC = 'http://localhost:' + str(ELASTICPORT) + '/_search'
WORDCLOUD_SIZE = 15
SUMMARIES_SIZE = 15
PROCESS_SIZE = 100 # Prevents running algorithms on entire db

# Check if Elasticsearch is running
r = requests.get(ELASTIC)
if not r:
    exit()


from elasticsearch import Elasticsearch, client
es = Elasticsearch()
indices_client = client.IndicesClient(es)

app = Flask(__name__, static_path='/static/')

# creating index for scores
indices_client.create('score')

def insert_score():
    # dict = {query: [(id, 1)]}
    scoredict = request.form
    es.index(index='score', body=scoredict)

def tokenizer(s):
    """
    Tokenizes a string.
    """
    tokens = [i.lower() for i in word_tokenize(s)
                if i.lower() not in stopwords.words('dutch')
                and len(i) > 1
                and re.match(r'^[a-zA-Z]+$', i)]
    return tokens




def doc_getter(res):
    hits = res['hits']['hits']
    items = [es.get('telegraaf', i.get('_id'))
                    for i in sorted(hits,
                                    key=lambda x: x['_score'],
                                    reverse=True)]

    docs = [j.get('_source').get('doc') for j in items]
    return docs

def summary_fixer(s):
    """
    Makes the summaries look nicer.
    """
    if not s:
        return '<No summary available.>'
    if not s.endswith('.'):
        s += '.'
    return s.capitalize() if len(s.split()) > 2 else '<No summary available.>'

def summarize(text, word_count):
    text = re.sub(r"[^.,!;:A-z]+|Pagina", ' ', text.rstrip())

    try:
        s = summ(text, word_count=word_count)
    except:
        try:
            s = kw(text, words=word_count)
        except:
            s = ' '.join([i for i in text.split()][:word_count])

    return summary_fixer(s)

def wordcloud_gen(summaries, query):
    def n(i, maxi, mini):
        if i == 1:
            return 1.75
        n = (i - mini) / (maxi - mini)
        return int(n * 15)

    summaries = [i for i in summaries if ">" not in i]
    tokens = [token for summary in summaries
                for token in tokenizer(summary)
                    if token not in query.split()]
    counted = Counter(tokens).items()
    maxi = max(y for x,y in counted)
    mini = min(y for x,y in counted)
    wc = [[x, n(y, maxi, mini)] for x,y in counted]

    return sorted(wc, key=lambda x: x[1], reverse=True)[:WORDCLOUD_SIZE]

def paginate(docs, per_page=10):
    """
    On input on a list of doc-items,
    paginate into seperate lists and return them.
    """
    return [docs[i: i + per_page] for i in range(0, len(docs), per_page)]


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def suggest():
    query = ' '.join(tokenizer(request.form.get('query', '')))
    startdate = request.form.get('startdate', '1918')
    enddate = request.form.get('enddate', '1994')
    title = request.form.get('title', '')
    current_page = request.form.get('current_page', 1) - 1

    if not query or len(query) == 1:
        pass

    res = es.search(index = "telegraaf", body = {
        "query": {
            "filtered": {
                "query": {
                    "query_string": {
                        "query": "{}".format(query)
                    }
                }
            }
        },
        "fields": [

        ],
        "from": 0,
        "size": 50,
        "sort": {
            "_score": {
                "order": "desc"
            }
        },
        "explain": True
    })

    # Retrieve documents
    docs = doc_getter(res)
    amount = len(docs)

    # Pagination
    p = paginate(docs[:PROCESS_SIZE])
    pagination_length = len(p)


    titles = [i.get('title') for i in docs]
    titles = [t if len(t) else '<No title available.>' for t in titles]
    texts = [i.get('text') for i in docs]
    summaries = [summarize(t, word_count=SUMMARIES_SIZE) for t in texts]

    timeline_years = ["2010", "2011", "2012", "2013"]
    timeline_data = [103, 99, 66, 200]

    wordcloud = wordcloud_gen(summaries, query)
    items = list(zip(titles, summaries))

    data = {
        'timeline_years': timeline_years,
        'timeline_data': ', '.join(map(str,timeline_data)),
        'items': items,
        'amount': amount,
        'wordcloud': wordcloud,
        'query_string': request.form.get('query'),
        'pagination_length': pagination,
        'pagination_current': current_page,
    }

    return render_template('result.html',
                           data=data)



"""
@app.route('/api/search', methods=['POST'])
def search():
    searchterm = request.form.get('query', '')
    startdate = request.form.get('startdate', '1918')
    enddate = request.form.get('enddate', '1994')
    title = request.form.get('title', '')

    query = {"query": {
                "filtered": {
                    "query": {
                        # match the following input in the fiels
                        "multi_match": {
                            "query": , searchterm
                            "fields": ["text", "title"]
                            }
                    },
                    "filter" :{
                        # filter on date range gte >=, lte <=
                        "range": {
                            #!!! not sure if name is correct
                            "date": {
                                "gte": startdate,
                                "lte": enddate
                                }
                            },
                        #!!! not sure, filter on the title of term
                        'term' : {'title': title}
                        }
                    }
                }
            }
    pass
"""

if __name__ == '__main__':
    app.run(debug=True)
