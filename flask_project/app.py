from flask import Flask, jsonify
from flask_sslify import SSLify


app = Flask(__name__)
#SSLify(app)


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
    app.run(debug=True, host='0.0.0.0')
