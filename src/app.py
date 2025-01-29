import json
from flask import Flask, request, Response

from recognition_core import worker
from data_processing import format_result


app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False


@app.route('/recognition', methods=['POST'])
def recognition():
    file = '../tmp.mp3'
    request.files['file'].save(file)

    recognition_result = worker(file)
    result = format_result(recognition_result)
    json_string = json.dumps(result, ensure_ascii=False, indent=4)
    response = Response(json_string, content_type="application/json; charset=utf-8")
    return response


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
