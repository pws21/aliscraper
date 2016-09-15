from variant_scraper import *
from flask import Flask, request, abort

app = Flask(__name__)

@app.route("/update_db")
def update_db():
    url = request.args.get('url')
    try:
        scraper = AliProductScraper(url)
        rows = scraper.get_variants()
        write_to_db(rows)
        return json.dumps({"result":"OK"})
    except NotProductPage:
        abort(422)

@app.route("/sample")
def sample():
    url = request.args.get('url')
    try:
        scraper = AliProductScraper(url)
        rows = scraper.get_variants()
        return json.dumps(rows, ensure_ascii=False)
    except NotProductPage:
        abort(422)

if __name__ == "__main__":
    app.run()

