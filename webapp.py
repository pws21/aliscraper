from scrapers import ServiceUnavailable, NotProductPage, AliProductScraper
from helpers import DBWriter
from flask import Flask, request, abort
import json
from threads import  get_variants_fast
from tor import TorConnection

app = Flask(__name__)


@app.route("/update_db")
def update_db():
    url = request.args.get('url')
    try:
        data = get_variants_fast(url, TorConnection(proxy_port=None))
        w = DBWriter()
        w.write(data)
        return json.dumps({"result": "OK"})
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)


@app.route("/sample")
def sample():
    url = request.args.get('url')
    try:
        tor = TorConnection(proxy_port=None)
        data = get_variants_fast(url, tor)
        print tor
        return json.dumps(data, ensure_ascii=False)
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)

if __name__ == "__main__":
    app.run()

