import csv
from settings import *
import MySQLdb as MySQL
import os
import json

logger = logging.getLogger('ali')
logger.setLevel(LOGLEVEL)
handler = None

def set_log_file(fname):
    global logger
    global handler
    if handler:
        logger.removeHandler(handler)
    handler = logging.FileHandler(fname)
    _fmt = logging.Formatter(LOGFMT)
    handler.setFormatter(_fmt)
    logger.addHandler(handler)

fieldnames = ["product_id",
              "product_title",
              "product_price",
              "product_image",
              "product_url",
              "variant_id",
              "variant_price",
              "variant_title",
              "shipping_cost"]

def xstr(s):
    return '' if s is None else str(s)

def safe_encode(val, charset):
     if val is  None:   
         return None
     return val.encode(charset)


class FileWriter(object):
    def __init__(self, filename=None, ext='dat', write_method=None):
        self.filename = filename
        self.ext = ext
        self.write_method = write_method

    def set_filename_for_rows(self, rows):
        if not self.filename:
            if not os.path.exists(FILES_DIR):
                os.makedirs(FILES_DIR)
            self.filename = "%s.%s" % (rows[0].get('product_id', 'None'), self.ext)
            self.filename = os.path.join(FILES_DIR, self.filename)
        
    def write(self, rows):
        self.set_filename_for_rows(rows)
        f = open(self.filename, "wb")
        self.write_method(f, rows)
        f.close()
        

class UnicodeDictWriter(csv.DictWriter):
    def writerow(self, rowdict):
        self.writer.writerow([safe_encode(s, "utf-8") for s in self._dict_to_list(rowdict)])


def write_to_csv(f, rows):
    writer = UnicodeDictWriter(f, fieldnames=fieldnames)
    #writer.writeheader()
    for r in rows:
        writer.writerow(r)


def write_to_json(f, rows):
    f.write(json.dumps(rows))


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
def insert_all(cur, sql, rows):
    for r in rows:
        cur.execute(sql, r)


class DBWriter(object):
    def __init__(self, ext_id=None):
        self.ext_id = ext_id
        
    def write(self, rows):
        ff = fieldnames + ['ext_id']
        for r in rows:
            r['ext_id'] = self.ext_id
        cols = ",".join(ff)
        vals = ",".join(map(lambda x: "%("+x+")s", ff))
        insert_all("insert into %s(%s) values(%s)" % (DB['variants_table'], cols, vals), rows)


@db_wrap
def get_urls(cur):
    #TODO: write SELECT from table with urls
    return test_urls * 10
