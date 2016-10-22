from flask import Flask, render_template, request


app = Flask(__name__, static_path='/static')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/suggest', methods=['POST'])
def suggest():

@app.rout('/api/search', methods=['POST'])
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

if __name__ == '__main__':
    app.run()
