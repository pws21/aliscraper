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
        conn = None
        cur = None
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
                if conn:
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

@db_wrap
def create_variants_table(cur):
    cur.execute(DDL)
    cur.execute("create index ak1_%(variants_table)s on %(variants_table)s (product_id)" % DB)
    cur.execute("create index ak2_%(variants_table)s on %(variants_table)s (insert_dt)" % DB)
	cur.execute("alter table %(variants_table)s add constraint uk_%(variants_table)s unique (product_id, variant_id)" % DB)

@db_wrap
def table_exists(cur, schema_name, table_name):
	cur.execute("SELECT count(*) FROM information_schema.tables "+
	            "WHERE table_schema = %(schema_name)s AND table_name = %(table_name)s LIMIT 1", {"schema_name": schema_name, "table_name": table_name})
	ret = cur.fetchone()
	return ret != 0

class DBWriter(object):
    def __init__(self, ext_id=None):
        self.ext_id = ext_id
		if not table_exists(DB["db_name"], DB["variants_table"]):
			create_variants_table()
        
    def write(self, rows):
        ff = fieldnames + ['ext_id']
        for r in rows:
            r['ext_id'] = self.ext_id
        cols = ",".join(ff)
        vals = ",".join(map(lambda x: "%("+x+")s", ff))
		upd = ",".join(["%s=values(%s)" % (f,f) for f in ff])
        insert_all("insert into %s(%s) values(%s) "+
		           "on duplicate key update %s, update_dt=now()" % (DB['variants_table'], cols, vals, upd), rows)


@db_wrap
def get_urls(cur):
    cur.execute("Select DISTINCT product_url from %s" % DB['variants_table'])
    for url in cur:
		yield url
