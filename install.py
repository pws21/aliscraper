from settings import *
import MySQLdb as MySQL

try:
    conn = MySQL.connect(host=DB['host'],
                         user=DB['username'],
                         passwd=DB['password'],
                         db=DB['dbname'],
                         charset=DB['charset'])
    cur = conn.cursor()
    #cur.execute('drop table %s'%DB['variants_table'])
    cur.execute(DDL)
    cur.close()
    conn.close()
except:
    pass

