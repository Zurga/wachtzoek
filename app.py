import requests
import json
from flask import Flask, render_template, request, jsonify

ELASTICPORT = 9200
ELASTIC = 'http://localhost:' + str(ELASTICPORT) + '/_search'

# Check if Elasticsearch is running
r = requests.get(ELASTIC)
if not r:
    exit()

app = Flask(__name__, static_path='/static/')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/result', methods=['POST'])
def suggest():
    docs = ["Juliana eet een jodenkoeck"]*6
    summaries = ["""
    Lorem ipsum dolor sit amet, consectetur adipiscing elit.
    Nam venenatis sed urna quis viverra.
    Etiam ultrices dui dignissim ligula maximus fringilla.
    Suspendisse accumsan lorem ipsum, vel ullamcorper arcu interdum vitae.
    Pellentesque at tellus non neque finibus lacinia id quis ligula.
    Lorem ipsum dolor sit amet, consectetur adipiscing elit. Vestibulum ante.
    """]*10

    timeline_years = ["2010", "2011", "2012", "2013"]
    timeline_data = [103, 99, 66, 200]
    items = list(zip(docs, summaries))
    wordcloud = [
        ["Lorem", 1],
        ["ipsum", 6],
        ["dolor", 3],
        ["sid", 2],
        ["amet", 8],
    ]

    data = {
        'timeline_years': timeline_years,
        'timeline_data': ', '.join(map(str,timeline_data)),
        'items': items,
        'amount': len([i for i in items]),
        'wordcloud': wordcloud,
        'query_string': request.form.get('query')
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
