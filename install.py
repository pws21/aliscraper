from helpers import db_wrap
from settings import DDL


@db_wrap
def create_table(cur):
    cur.execute(DDL)
