from helpers import db_wrap
from settings import DDL, DB


@db_wrap
def create_table(cur):
    cur.execute(DDL)
    cur.execute("create index ak1_%(variants_table)s on %(variants_table)s (product_id)" % DB)
    cur.execute("create index ak2_%(variants_table)s on %(variants_table)s (insert_dt)" % DB)
	cur.execute("alter table %(variants_table)s add constraint uk_%(variants_table)s unique (product_id, variant_id)" % DB)


@db_wrap
def drop_table(cur):
    cur.execute("drop table %s" % DB['variants_table'])

if __name__ == "__main__":
    drop_table()
    create_table()
