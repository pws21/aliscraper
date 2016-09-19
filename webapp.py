from scrapers import ServiceUnavailable, NotProductPage, AliProductScraper
from helpers import save_variants, write_to_db
from flask import Flask, request, abort
import json
from threads import run_one, TorConnection, get_variants_fast
from settings import *
import random

app = Flask(__name__)

@app.route("/update_db")
def update_db():
    url = request.args.get('url')
    try:
        run_one(url, write_to_db)
        return json.dumps({"result": "OK"})
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)

@app.route("/sample")
def sample():
    url = request.args.get('url')
    data = []
    def fake_writer(rows):
        pass
    try:
        data = get_variants_fast(url, TorConnection(TOR_BASE_PORT + random.randint(0,NUM_TORS)))
        #scraper = AliProductScraper(url)
        #rows = scraper.get_variants()
        return json.dumps(data, ensure_ascii=False)
    except NotProductPage:
        abort(422)
    except ServiceUnavailable:
        abort(503)

if __name__ == "__main__":
    app.run()

