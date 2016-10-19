from flask import Flask, render_template, request


app = Flask(__name__, static_path='/static')

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/suggest', methods=['POST'])
def suggest():
    # hier komt code die zoekt met behulp van elasticsearch
    # en de json die er uit angular komt.
    pass

if __name__ == '__main__':
    app.run()
