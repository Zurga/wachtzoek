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

# Prevents program from doing stuff for entire database.
# Also sets amount of pagination items to /10.
RESULT_SIZE = 10
PAGINATION_SIZE = 10

# Check if Elasticsearch is running
r = requests.get(ELASTIC)
if not r:
    exit()


from elasticsearch import Elasticsearch, client
es = Elasticsearch()
indices_client = client.IndicesClient(es)
if not indices_client.exists('telegraaf'):
    # creating index for scores
    indices_client.create('score')

app = Flask(__name__, static_path='/static/')



@app.route('/api/score', methods=['POST'])
def insert_score():
    #{query: query, judge: name, docID: doc, relevant: [1,0]}

    scoredict = request.form
    query = {
        'query': {
            "bool": {
                'should': [
                    {'match': {
                        'query': scoredict['query']
                    }},
                    {'match': {
                        'docid': scoredict['docid']
                    }}
                ]
            }
        }
    }
    print(query)
    exists = es.search(index='score', body=query)
    if not exists['hits']['hits']:
        es.index(index='score', body=scoredict, doc_type='score')
    return json.dumps({'success':True}), 200, {'ContentType':'application/json'}

def get_scores():
    searchterm = request.form.get(query)

    query = {
    'query:{
        'match': {
            'query': searchterm
            }
        }
    }
    # get results based on the query
    result = es.search(index=query)

    # get judge id's for serach query
    j1id = result['hits']['hits'][0][judge]
    j2id = result['hits']['hits'][1][judge]

    judge_query =
    {
        'query':{
            'bool': {
                'must': {
                    "match": {
                        "query": searchterm
                    }
                },
                "filter": {}
                    {"term": {"judge": [j1id,j2id]}}
                }
            }
        }
    }



def tokenizer(s):
    """
    Tokenizes a string.
    """
    tokens = [i.lower() for i in word_tokenize(s)
              if i.lower() not in stopwords.words('dutch')
              and len(i) > 1 and re.match(r'^[a-zA-Z]+$', i)]
    return tokens

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


@app.route('/result', defaults={'page': 1}, methods=['POST', 'GET'])
@app.route('/result/page/<int:page>')
def search(page):
    print(request.form)

    if request.method == 'POST':
        searchterm = ' '.join(tokenizer(request.form.get('query', '')))
        startdate = request.form.get('from')
        enddate= request.form.get('to', '1994')
        title = request.form.get('title', '')
        current_page = int(request.form.get('current_page', 1)) - 1

    if request.method == 'GET':
        searchterm = ' '.join(tokenizer(request.args.get('query', '')))
        startdate = request.args.get('from')
        enddate= request.args.get('to', '1994')
        title = request.args.get('title', '')
        current_page = int(request.args.get('current_page', 1)) - 1

    if not searchterm:
        # TODO give feedback that the search failed
        pass


    query = {"query": {
                "filtered": {
                    "query": {
                        # match the following input in the fiels
                        "multi_match": {
                            "query": searchterm,
                            "fields": ["text", "title"]
                            }
                    },
                    "filter" :{
                        # filter on date range gte >=, lte <=
                        "range": {
                            #!!! not sure if name is correct
                            "date": {
                                "gte": '{}-01-01'.format(startdate if
                                                         startdate else 1900),
                                "lte": '{}-12-31'.format(enddate
                                                         if enddate else 1994)
                                }
                            },
                        #!!! not sure, filter on the title of term
                        #'term' : {'title': title}
                        }
                    }
                },
            "from": RESULT_SIZE * page,
            "size": RESULT_SIZE,
            "sort": {
                "_score": {
                    "order": "desc"
            }
        }
    }

    res = es.search(index="telegraaf", body=query)
    docs = res['hits']['hits']
    num_docs = res['hits']['total']
    # for the pagination
    num_pages = round(num_docs / RESULT_SIZE)
    pagination_end = PAGINATION_SIZE + page
    print('pag_end', pagination_end)
    overshoot = num_pages - pagination_end
    print('overshoot', overshoot)
    if overshoot < 0:
        pagination_end = num_pages

    # Only current page!
    results = docs
    ids = [i.get('_id') for i in results]
    titles = [i.get('_source', {}).get('title', '') for i in results]
    titles = [t if len(t) else '<No title available.>' for t in titles]
    texts = [i.get('_source', {}).get('text', '') for i in results]
    summaries = [summarize(t, word_count=SUMMARIES_SIZE) for t in texts]
    items = list(zip(ids, titles, summaries))

    timeline_years = ["2010", "2011", "2012", "2013"]
    timeline_data = [103, 99, 66, 200]

    # For RESULT_SIZE.
    wtexts = [i.get('_source', {}).get('text', '') for i in docs]
    wsummaries = [summarize(t, word_count=SUMMARIES_SIZE) for t in wtexts]
    # wordcloud = wordcloud_gen(wsummaries, searchterm)
    wordcloud = None


    data = {
        'timeline_years': timeline_years,
        'timeline_data': ', '.join(map(str,timeline_data)),
        'items': items,
        'amount': num_docs,
        'wordcloud': wordcloud,
        'query_string': searchterm,
        'from_strng': startdate,
        'to_string': enddate,
        'title_string': title,
        'pagination_length': list(range(page - 1 if page - 1 != 0 else 1, pagination_end)),
        'pagination_current': page
    }

    return render_template('result.html',
                           data=data)


@app.route('/modal', methods=["GET"])
def modal():
    # haal doc o.b.v id
    # prop tekst en metadata in template (jinja)
    # geef template terug met render_template
    doc_id = request.args.get('id')
    query = {
        'query': {
            'match': {
                '_id': doc_id
            }
        }
    }

    doc = es.search(index="telegraaf", body=query).get('hits', {}).get('hits', [''])[0].get('_source')

    data = {
        'doc_id': doc_id,
        'title': doc.get('title', '<No title available.>'),
        'date': doc.get('date', '<No date available.>'),
        'text': doc.get('text', '<No text available.>')
    }

    return render_template('modal.html', data=data)

@app.route('/api/search', methods=['POST'])
def old_search():
    if not request.form:
        data = request.values
    else:
        data = request.values
    searchterm = data.get('query', 'Duits')
    startdate = data.get('startdate', '1990-01-10')
    enddate = data.get('enddate', '1990-12-01')
    title = data.get('title', '')

    query = {"query": {
                "filtered": {
                    "query": {
                        # match the following input in the fiels
                        "multi_match": {
                            "query": searchterm,
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
                        #'term' : {'title': title}
                        }
                    }
                }
            }
    print('query',query)
    result = es.search(index='telegraaf', body=query)
    print('result',result)
    return result

if __name__ == '__main__':
    app.run(debug=True)

'''
query = {"query": {
            "filtered": {
                "query": {
                    # match the following input in the fiels
                    "multi_match": {
                        "query": searchterm,
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
                    #'term' : {'title': title}
                    }
                }
            }
        }
'''
