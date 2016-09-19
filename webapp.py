from scrapers import ServiceUnavailable, NotProductPage, AliProductScraper
from helpers import save_variants, write_to_db
from flask import Flask, request, abort
import json
from threads import run_one, TorConnection, get_variants_fast

app = Flask(__name__)


@app.route("/update_db")
def update_db():
    url = request.args.get('url')
    try:
        data = get_variants_fast(url, TorConnection(proxy_port=None))
        write_to_db(data)
        return json.dumps({"result": "OK"})
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)


@app.route("/sample")
def sample():
    url = request.args.get('url')
    try:
        data = get_variants_fast(url, TorConnection(proxy_port=None))
        return json.dumps(data, ensure_ascii=False)
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)

if __name__ == "__main__":
    app.run()

