from flask import Flask, jsonify

app = Flask(__name__)


@app.route('/')
def index():
    return 'Flask is running!'


@app.route('/data')
def names():
    data = {
        "first_names": ["Jonny", "Jacob", "Juuli", "Jenny", "Joan", "Jim"]
    }
    return jsonify(data)


if __name__ == '__main__':
    app.run(ssl_context='adhoc')
