import csv
from settings import *
import MySQLdb as MySQL
import os
import json

logger = logging.getLogger('ali')
logger.setLevel(LOGLEVEL)
_fmt = logging.Formatter(LOGFMT)
handler = logging.FileHandler(LOGFILE)
handler.setFormatter(_fmt)
logger.addHandler(handler)

def reset_log_file(fname):
    global logger
    global handler
    if handler:
        logger.removeHandler(handler)
    handler = logging.FileHandler(fname)
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


def get_file_writer(filename, fmt):
    def fn(rows):
        if filename:
            fname = filename
        elif len(rows) > 0:
            if not os.path.exists(FILES_DIR):
                os.makedirs(FILES_DIR)
            fname = "%s.%s" % (rows[0].get('product_id', 'None'), fmt)
            fname = os.path.join(FILES_DIR, fname)
        else:
            return
        f = open(fname, "wb")
        writer(f, rows)
        f.close()        
        
    writer = None
    if fmt == 'csv':
        writer = write_to_csv
    elif fmt == 'json':
        writer = write_to_json
    else:
        raise ValueError

    return fn


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



@db_wrap
def get_urls(cur):
    #TODO: write SELECT from table with urls
    return test_urls * 10
