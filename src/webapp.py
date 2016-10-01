from scrapers import ServiceUnavailable, NotProductPage, AliProductScraper
from helpers import DBWriter
from flask import Flask, request, abort
import json
from threads import  get_variants_fast
from tor import TorConnection

app = Flask(__name__)


def get_data():
    url = request.args.get('url')
    try:
        if not url:
            raise NotProductPage
        return get_variants_fast(url, TorConnection(proxy_port=None))
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)


@app.route("/update_db")
def update_db():
    data = get_data()
    ext_id = request.args.get('ext_id')
    w = DBWriter(ext_id=ext_id)
    w.write(data)
    return json.dumps({"result": "OK"})


@app.route("/sample")
def sample():
    return json.dumps(get_data(), ensure_ascii=False)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)

