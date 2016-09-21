#from optparse import OptionParser
import argparse
from threads import run_all, run_one
import sys
from helpers import *
import settings

class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def run_with_args(ns):
    writer = None
    filename = None
    if ns.log:
        reset_log_file(ns.log)
    if ns.url and ns.filename:
        filename = ns.filename
    if ns.save_to == 'db':
        writer = write_to_db
    else:
        writer = get_file_writer(filename, ns.save_to)

    if ns.url:
        run_one(ns.url, writer=writer)
    else:
        run_all(get_urls(), writer=writer, with_monitor=ns.verbose)

if __name__ == "__main__":
    parser = MyParser(description="""AliExpress scraping runner

WARNING!
Before RUN You need to start multiple Tor instances with run_tors.sh

""", formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--save-to", action="store", dest="save_to", help="Save results to Database or CSV file or Json file", default="db", choices=['db', 'csv', 'json'], required=True)
    parser.add_argument("--url", action="store", dest="url", help="URL to AliExpress Product Page (for one time usage)")
    parser.add_argument("--file", action="store", dest="filename", help="Filename for saving result. Can be used only with --url flag and --save-to=csv|json")
    parser.add_argument("--silent", action="store_false", dest="verbose", help="Silent mode. No output.")
    parser.add_argument("--log", action="store", dest="log", help="Log file. Default %s" % settings.LOGFILE)

    ns = parser.parse_args()

    run_with_args(ns)

