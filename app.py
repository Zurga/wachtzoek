import requests
import json
import string
import re
import math

from flask import Flask, render_template, request, jsonify
from gensim.summarization import summarize as summ
from gensim.summarization import keywords as kw
from collections import Counter, defaultdict
from nltk.corpus import stopwords
from nltk import word_tokenize
from nltk.stem import SnowballStemmer
from elasticsearch import Elasticsearch, client

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


es = Elasticsearch()
indices_client = client.IndicesClient(es)
if not indices_client.exists('score'):
    # creating index for scores
    indices_client.create('score')

app = Flask(__name__, static_path='/static/')

def toInt(i):
    return int(i) if i else i


@app.route('/api/score', methods=['POST'])
def insert_score():
    scoredict = request.form
    query = {
        'query': {
            "bool": {
                'must': [
                    {'match': {
                        'query': scoredict['query']
                    }},
                    {'match': {
                        'docid': scoredict['docid']
                    }},
                    {'match': {
                        'judge': scoredict['judge']
                    }}
                ]
            }
        }
    }
    exists = es.search(index='score', body=query)
    if not exists['hits']['hits']:
        es.index(index='score', body=scoredict, doc_type='score')
        return json.dumps({'success':True}), 200, {'ContentType':'application/json'}
    return json.dumps({'success': False}), 404, {'ContentType':'application/json'}


def tokenizer(s):
    """
    Tokenizes a string.
    """
    s = re.sub(r"[^.,!;:A-z]+|Pagina|Advertentie", ' ', s.rstrip())
    tokens = [i.lower() for i in word_tokenize(s)
              if i.lower() not in stopwords.words('dutch')
              and len(i) > 2 and re.match(r'^[a-zA-Z]+$', i)]
    return tokens

def describe(query, text):
    """
    Returns a fraction of a text based on
    a query. Makes query terms bold.
    """
    # No proper tokenization here to keep structure
    tokens = text.split()
    query = '|'.join(query.lower().split())
    s1 = "<strong>"
    s2 = "</strong>"

    strongified = [s1+t+s2 if re.match(query, t.lower()) else t for t in tokens]
    enum = enumerate(strongified)

    indices = []
    for i, token in enum:
        if token.startswith('<'):
            if len(indices) == 0:
                indices.append(i)
            else:
                if abs(indices[-1] - i) > 10:
                    indices.append(i)

    snippits = [' '.join((['...'] if i-12>0 else ['']) + strongified[(i-12 if i-12 >0 else 0):i+12] + ['...']) for i in indices]

    description = ' '.join(snippits[:2])
    if len(description) > 15:
        return description
    else:
        return "No description available."


def wordcloud_gen(texts, query):

    def n(i, maxi, mini):
        """
        Normalizes.
        """
        return (i - mini) / (maxi - mini)

    def idf(df, texts, term):
        """
        Given a single query term score the term using idf.
        """
        try:
            return math.log(len(texts), df[term])
        except ZeroDivisionError:
            return 0.0

    texts_tokenized = [tokenizer(text) for text in texts]
    all_tokens = [token for text in texts_tokenized for token in text
                    if token not in query.split() + ['pagina']]

    # Build inverse document frequency
    df = defaultdict(dict)
    for t in set(all_tokens):
        df[t] = sum(1 for text in texts_tokenized if t in text)

    counted = Counter(all_tokens).items()
    scores = [(term, count + (idf(df, texts, term)*2)) for term, count in counted]
    maxi = max(y for x,y in scores)
    mini = min(y for x,y in scores)

    wc = [[x, n(y, maxi, mini)]  for x, y in scores]

    if max(wc, key=lambda x: x[1])[1] < 10:
        wc = list(map(lambda x: [x[0], x[1]*7.75], wc))

    elif max(wc, key=lambda x: x[1])[1] < 6:
        wc = list(map(lambda x: [x[0], x[1]*12.25], wc))

    elif max(wc, key=lambda x: x[1])[1] < 4:
        wc = list(map(lambda x: [x[0], x[1]*15], wc))

    wordcloud = sorted(wc, key=lambda x: x[1], reverse=True)[:WORDCLOUD_SIZE]

    return wordcloud


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
    request.form
    if request.method == 'POST':
        data = request.form
    elif request.method == 'GET':
        data = request.args

    searchterm = ' '.join(tokenizer(data.get('query', '')))
    startdate = data.get('from', '')
    enddate = data.get('to', '')
    title = data.get('title', '')
    current_page = int(data.get('current_page', 1)) - 1
    doc_type = data.getlist('type')

    if not searchterm:
        wordcloud = [['oeps', 10], ['oh jee', 5], ['sorry', 3], ['vervelend', 2],
                     ['opnieuw', 1]]
        data = {
            'amount': 0,
            'wordcloud': wordcloud,
            'query_string': searchterm,
            'from_string': startdate,
            'to_string': enddate,
            'title_string': title,
        }
        return render_template('no-result.html', data=data)

    query = {"query": {
                "filtered": {
                    "query": {
                        # match the following input in the fiels
                        "multi_match": {
                            "query": searchterm,
                            #type': 'cross_fields',
                            "fields": ["text", "title"]
                            }
                    },
                    "filter" :[
                        # filter on date range gte >=, lte <=
                        {"range": {
                            #!!! not sure if name is correct
                            "date": {
                                "gte": '{}-01-01'.format(startdate if
                                                         startdate else 1900),
                                "lte": '{}-12-31'.format(enddate
                                                         if enddate else 1994)
                                }
                            }
                        },
                        ]
                    }
                },
            "from": RESULT_SIZE * page,
            "size": RESULT_SIZE,
            "sort": {
                "_score": {
                    "order": "desc"
                    }
                },
            "aggs" : {
                "dates": {
                    "date_histogram" : {
                        "field" : "date",
                        "interval": "year",
                        }
                    },
                'types': {
                    'terms': {'field': 'type'}
                    }
                }
            }

    title_filter = {"term": { "title": title}}
    if title:
        query['query']['filtered']['filter'].append(title_filter)

    if doc_type:
        filters = {'bool': {'should': []}}
        # Get the aggregation data for the facets that have not been enabled.
        facet_res = es.search(index='telegraaf', body=query).get('aggregations')
        facets = {t.get('key'): {'count': t.get('doc_count'),
                                                   'checked': ''} for t in
                      facet_res.get('types', {}).get('buckets', [])}
        for t in doc_type:
            facets[t]['checked'] = 'checked="true"'
            filters['bool']['should'].append({'term': {'type': t}})
        query['query']['filtered']['filter'].append(filters)


    res = es.search(index="telegraaf", body=query)
    docs = res['hits']['hits']
    aggregations = res.get('aggregations')

    if docs:
        num_docs = res['hits']['total']
        # for the pagination
        num_pages = round(num_docs / RESULT_SIZE)
        pagination_end = PAGINATION_SIZE + page
        overshoot = num_pages - pagination_end
        if overshoot < 0:
            pagination_end = num_pages

        for d in docs:
            d['description'] = describe(searchterm, d['_source'].get('text', ''))

        # For RESULT_SIZE.
        # Wordcloud only, 'summaries' aren't used on resultpage anymore.
        # We now use descriptions, with hightlighted words.
        wtexts = [i.get('_source', {}).get('text', '') for i in docs]
        wordcloud = wordcloud_gen(wtexts, searchterm)

        # create the timeline data for the graph
        startdate, enddate = toInt(startdate), toInt(enddate)
        timeline_years = list(range(startdate if startdate else 1918, enddate if enddate else 1995))
        if len(timeline_years) == 0:
            timeline_years = [startdate]
        timeline_data = dict([(int(a.get('key_as_string')[:4]), a.get('doc_count'))
                                for a in aggregations.get('dates', {}).get('buckets', [])])

        # fill the data with zero's for the missing years
        timeline_data = [timeline_data.get(y, 0) for y in timeline_years]


        # Facets data gathering
        if not doc_type:
            facets = {t.get('key'): {'count': t.get('doc_count'),
                                                    'checked': ''} for t in
                        aggregations.get('types', {}).get('buckets', [])}

        # facets = {}
        data = {
            'timeline_years': timeline_years,
            'timeline_data': ', '.join(map(str,timeline_data)),
            'items': docs,
            'amount': num_docs,
            'wordcloud': wordcloud,
            'query_string': searchterm,
            'from_string': startdate,
            'to_string': enddate,
            'title_string': title,
            'pagination_length': list(range(page - 1 if page - 1 != 0 else 1,
                                            pagination_end)),
            'pagination_current': page,
            'facets': facets,
        }

        return render_template('result.html', data=data)

    wordcloud = [['oeps', 10], ['oh jee', 5], ['sorry', 3], ['vervelend', 2],
                 ['opnieuw', 1]]
    data = {
        'amount': 0,
        'wordcloud': wordcloud,
        'query_string': searchterm,
        'from_string': startdate,
        'to_string': enddate,
        'title_string': title,
    }

    return render_template('no-result.html', data=data)


@app.route('/modal', methods=["GET"])
def modal():
    # haal doc o.b.v id
    # prop tekst en metadata in template (jinja)
    # geef template terug met render_template
    doc_id = request.args.get('id')
    query = {'query': {'match': {'_id': doc_id}}}

    doc = es.search(index="telegraaf",
                    body=query).get('hits', {}).get('hits', [''])[0].get('_source')

    data = {
        'doc_id': doc_id,
        'title': doc.get('title', '<No title available.>'),
        'date': doc.get('date', '<No date available.>'),
        'text': doc.get('text', '<No text available.>')
    }

    return render_template('modal.html', data=data)

@app.route('/scores', methods=['GET'])
def get_scores():
    searchterms = request.args.getlist('queries')
    Evaluation = {'terms': {},'avg':0}

    if not searchterms:
        return render_template('no-result.html')

    for searchterm in searchterms:
        query = {'query': {'match': {'query': searchterm}},"size":50}
        # get results based on the query
        result = es.search(index='score', body=query)
        print(result['hits']['hits'])

        Evaluation['terms'][searchterm] = {}
        # return empty dict if no results
        if len(result['hits']['hits']) < 20:
            continue

        # get judg[e id's for serach query
        judges = list({doc['_source']['judge'] for doc in result['hits']['hits']})
        judge1 = judges[0]
        judge2 = judges[1]

        # get a dict with judge keys with
        # their relevant  and nonrelevant labeled docs
        # {j1:{relevant:[d1,d4,d5],nonrelevant:[d2,d3]},j2:..}
        relevantdoc = {
            judge1: {'relevant': [],
                    'nonrelevant': []},
            judge2: {'relevant': [],
                    'nonrelevant': []}
        }

        print(len(result['hits']['hits']))
        for hit in result['hits']['hits']:
            hit = hit['_source']
            if int(hit['relevant']) == 1:
                relevantdoc[hit['judge']]['relevant'].append(hit['docid'])
            if int(hit['relevant']) == 0:
                relevantdoc[hit['judge']]['nonrelevant'].append(hit['docid'])

        docIDs = set(hit['_source']['docid']
                          for hit in result['hits']['hits'])

        N11, N10, N01, N00 = 0, 0, 0, 0

        for docID in docIDs:
            if docID in relevantdoc[judge1]['relevant'] and \
                    docID in relevantdoc[judge2]['relevant']:
                N11 += 1
            if docID in relevantdoc[judge1]['relevant'] and \
                    docID in relevantdoc[judge2]['nonrelevant']:
                N10 += 1
            if docID in relevantdoc[judge1]['nonrelevant'] and \
                    docID in relevantdoc[judge2]['relevant']:
                N01 += 1
            if docID in relevantdoc[judge1]['nonrelevant'] and \
                    docID in relevantdoc[judge2]['nonrelevant']:
                N00 += 1

        N = N11 + N10 + N01 + N00

        # Calculate the P@10 for both judges
        Evaluation['terms'][searchterm]['P10judge1'] = len(relevantdoc[judge1]['relevant'])/N
        Evaluation['terms'][searchterm]['P10judge2'] = len(relevantdoc[judge2]['relevant'])/N

        # Calculate the Cohen's kappa
        PA = (N11 + N00)/N
        Pnonrel = (N01 + N10 + 2*N00)/(2*N)
        Prel = (N10 + N01 + 2*N11)/(2*N)
        PE = Pnonrel**2 + Prel**2
        Evaluation['terms'][searchterm]['CohensKappa'] = (PA - PE)/(1 - PE)
        Evaluation['avg'] += Evaluation['terms'][searchterm]['P10judge1'] + Evaluation['terms'][searchterm]['P10judge2']

    Evaluation['avg'] = Evaluation['avg'] / len(searchterms)
    return render_template('evaluation.html', data=Evaluation)


if __name__ == '__main__':
    app.run(debug=True)
