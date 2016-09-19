import csv
from settings import *
import MySQLdb as MySQL
from scrapers import AliProductScraper

logger = logging.getLogger('ali')
logger.setLevel(LOGLEVEL)
_fmt = logging.Formatter(LOGFMT)
_handler = logging.FileHandler(LOGFILE)
_handler.setFormatter(_fmt)
logger.addHandler(_handler)


class NotProductPage(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


fieldnames = ["product_id",
              "product_title",
              "product_price",
              "product_image",
              "product_url",
              "variant_id",
              "variant_price",
              "variant_title",
              "shipping_cost"]


class UnicodeDictWriter(csv.DictWriter):
    def writerow(self, rowdict):
        self.writer.writerow([s.encode("utf-8") for s in self._dict_to_list(rowdict)])


def write_to_csv(rows, filename):
    f = open(filename, "wb")
    writer = UnicodeDictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

def db_wrap(f):
    """Init/deinit Mysql connection and add cursor ass the first argument to function"""
    def func(*args, **kwargs):
        try:
            conn = MySQL.connect(host=DB['host'],
                                 user=DB['username'],
                                 passwd=DB['password'],
                                 db=DB['dbname'],
                                 charset=DB['charset'])
            cur = conn.cursor()
            new_args = list(args)
            new_args.insert(0, cur)
            res = f(*new_args, **kwargs)
            conn.commit()
            return res
        except:
            try:
                conn.rollback()
            except:
                pass
            raise
        finally:
            try:
                cur.close()
            except:
                pass
            try:
                conn.close()
            except:
                pass
    return func

@db_wrap
def write_to_db(cur, rows):
    cols = ",".join(fieldnames)
    vals = ",".join(map(lambda x: "%("+x+")s", fieldnames))
    for r in rows:
        cur.execute("insert into %s(%s) values(%s)" % (DB['variants_table'], cols, vals), r)

def save_variants(url, writer, proxy='localhost:9050'):
    logger.info("Start process URL %s" % url)
    scraper = AliProductScraper(url, proxy)
    rows = scraper.get_variants()
    writer(rows)



@db_wrap
def get_urls(cur):
    #TODO: write SELECT from table with urls
    return test_urls * 10