import re
import json
import requests
from BeautifulSoup import BeautifulSoup
import csv
import random
from settings import *
import MySQLdb as MySQL
import Queue
from threading import Thread
import traceback
import sys
import logging
import os
from tor import Tor
import socks
import socket
import time
from stem.control import Controller
from stem import Signal
from threading import active_count as threading_active_count

_logger = logging.getLogger('ali')
_logger.setLevel(LOGLEVEL)
fmt = logging.Formatter(LOGFMT)
handler = logging.FileHandler(LOGFILE)
handler.setFormatter(fmt)
_logger.addHandler(handler)


#_tor = Tor()
#socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4, '127.0.0.1', 9100)
#socket.socket = socks.socksocket

class Property(object):
    def __init__(self, id, title, img=None):
        self.id = id
        self.title = title
        self.img = img


class PropertyCombination(object):
    def __init__(self, vector):
        self.vector = vector

    @property
    def img(self):
        for i in self.vector:
            if i.img:
                return i.img
        return None

    @property
    def title(self):
        return " & ".join([p.title for p in self.vector])

    @property
    def key(self):
        return ",".join(self.vector)


class PropertyManager(object):
    def __init__(self, props):
        self.props = props

    def get_combination(self, key):
        if not key:
            return None
        vector = []
        for n, k in enumerate(key.split(',')):
            vector.append(self.props[n][k])
        return PropertyCombination(vector)


class AliShippingScraper(object):
    def __init__(self, product_page, product_id, currency, proxy=None):
        self.country = product_page.find('input', {'name':'countryCode'}).get('value')
        self.province = product_page.find('input', {'name':'provinceCode'}).get('value')
        self.city = product_page.find('input', {'name':'cityCode'}).get('value')

        def xstr(s):
            return '' if s is None else str(s)

        url = 'https://freight.aliexpress.com/ajaxFreightCalculateService.htm?callback=jQuery&f=d&productid=%s&count=1&currencyCode=%s&sendGoodsCountry=&country=%s&province=%s&city=%s&abVersion=1&_=1473792174531' % (product_id, currency, xstr(self.country), xstr(self.province), xstr(self.city))
        response = get_with_retry(url, proxy=proxy)
        #response = requests.get(url, timeout=HTTP_TIMEOUT_SEC)
        #response = urllib2.urlopen(url, None, HTTP_TIMEOUT_SEC)
        self.content = response.text

    def get_price(self):
        m = re.search('\"price\":\"([0-9\.]+)\"', self.content)
        if m:
            return m.groups(0)[0]
        else:
            return None

class NotProductPage(Exception):
    pass

class ServiceUnavailable(Exception):
    pass

def get_with_retry(url, cookies=None, proxy='localhost:9050', headers={}):
#    try:
    response = requests.get(url, timeout=HTTP_TIMEOUT_SEC, cookies=cookies, 
                            proxies=dict(http='socks5://%s' % proxy, https='socks5://%s' % proxy), headers=headers)
#        if 'serviceUnavailable:' in response.text:
#            raise ServiceUnavailable
    return response
#    except (requests.ReadTimeout, socks.GeneralProxyError,ServiceUnavailable) as e:
#        if retry_cnt > 0:
#            return get_with_retry(url, cookies, retry_cnt-1)
#        raise


class AliProductScraper(object):
    def __init__(self, url, proxy):
        self.url = url
        #_tor.new_identity()
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive','user-agent': 'Googlebot/2.1'}
        response = get_with_retry(self.url, cookies={'aep_usuc_f': 'region=US&site=glo&b_locale=en_US&c_tp=USD'}, proxy=proxy, headers=headers)
        #html = response.text
        #print html
        self.soup = BeautifulSoup(response.text)

        self.js = self.soup.findAll('script', {"type": "text/javascript"})
        if self.find_pattern("serviceUnavailable:'(.+)',", self.js):
            raise ServiceUnavailable
        self.details_block = self.soup.find('div', {"class":"detail-wrap"}) or self.soup.find('div', {"class":"store-detail-wrap"})
        if not self.details_block:
            raise NotProductPage

        self.product_id = self.find_pattern('window.runParams.productId=\"(.+)\"', self.js)
        self.product_title = self.details_block('h1', {"class": "product-name"})[0].text
        self.product_img = self.soup.find('div',{"itemprop":"image"}).find('img').get('src')
        self.currency_code = self.find_pattern('window.runParams.baseCurrencyCode=\"(.+)\"', self.js)
        self.pm = self.create_property_manager()

        self.shipping = AliShippingScraper(self.soup, self.product_id, self.currency_code, proxy=proxy)

    def create_property_manager(self):
        props = []
        for p in self.details_block.find('div', {"id": "j-product-info-sku"}).findAll('dl', {"class": "p-property-item"}):
            prop_dict = {}
            for el in p.findAll('a', {'data-role': 'sku'}):
                img = None
                if el.find('img'):
                    img = el.find('img').get('bigpic')
                prop = Property(el.get('data-sku-id'), el.get('title') or el.find('span').text, img)
                prop_dict[prop.id] = prop
            props.append(prop_dict)

        return PropertyManager(props)

    def get_variants(self):
        data = json.loads(self.find_pattern('var skuProducts=(\[.+\])', self.js))
        rows = []
        for sku in data:
            if sku['skuVal'].get("availQuantity") > 0:
                row = {}
                combination = self.pm.get_combination(sku["skuPropIds"])
                row["product_id"] = self.product_id
                row["product_title"] = self.product_title
                product_price_currency = self.find_pattern('window.runParams.baseCurrencySymbol=\"(.+)\"', self.js)

                # price calculation
                min_price = self.find_pattern('window.runParams.actMinPrice=\"([0-9\.]+)\"', self.js)
                max_price = self.find_pattern('window.runParams.actMaxPrice=\"(0-9\.+)\"', self.js)
                if min_price is None:
                    min_price = self.find_pattern('window.runParams.minPrice=\"([0-9\.]+)\"', self.js)
                    max_price = self.find_pattern('window.runParams.maxPrice=\"([0-9\.]+)\"', self.js)
                if min_price == max_price:
                    price = min_price
                else:
                    price = "%s-%s" % (min_price, max_price)
                row["product_price"] = "%s %s" % (product_price_currency, price)

                if combination:
                    row["product_image"] = combination.img or self.product_img
                    row["variant_title"] = combination.title
                else:
                    row["product_image"] = self.product_img
                    row["variant_title"] = u''
                row["product_url"] = self.url
                row["variant_id"] = sku["skuPropIds"]
                if sku['skuVal'].get("isActivity"):
                    row["variant_price"] = sku['skuVal'].get("actSkuPrice")
                else:
                    row["variant_price"] = sku['skuVal'].get("skuPrice")

                row["shipping_cost"] = self.shipping.get_price()
                rows.append(row)
        return rows

    def find_pattern(self, pattern, where):
        for txt in where:
            m = re.search(pattern, txt.text);
            if m:
                return m.groups(0)[0]
        return None


class Worker(Thread):
    def __init__(self, queue, proxy_port):
        Thread.__init__(self)
        self.queue = queue
        self.proxy_port = proxy_port
        self.identity_counter = 0
        self.tor_control = Controller.from_port(port=proxy_port-934)
        
    def run(self):
        while not self.queue.empty():
            url = self.queue.get()
            try:
                save_variants(url, write_to_db)
                _logger.info("URL %s OK" % url)
            except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable) as e:
                self.change_identity()
            except NotProductPage, e:
                _logger.error("URL %s is not a Product page" % url)
            except Exception, e:
                _logger.error("URL %s error" % url)
                traceback.print_exc(file=sys.stdout)
            self.queue.task_done()
            #time.sleep(1)

    def change_identity(self):
        self.tor_control.authenticate('r2d2tor')
        self.tor_control.signal(Signal.NEWNYM)
        self.identity_counter += 1
        #time.sleep(1)

class Monitor(Thread):
    def __init__(self, queue, workers):
        Thread.__init__(self)
        self.queue = queue
        self.finish_signal = False
        self.workers = workers

    def finish(self):
        self.finish_signal = True
 
    def run(self):
        while not self.finish_signal:
            time.sleep(2)
            print "Elements in Queue:", self.queue.qsize(), "Active Threads:", threading_active_count()
            for w in self.workers:
                print "Worker on port %s - %s" % (w.proxy_port, w.identity_counter)
            

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
    _logger.info("Start process URL %s" % url)
    scraper = AliProductScraper(url, proxy)
    rows = scraper.get_variants()
    writer(rows)


def run_threaded(iterator):
    def process_queue():
        while not q.empty():
            url = q.get()
            try:
                save_variants(url, write_to_db)
                _logger.info("URL %s OK" % url)
            except NotProductPage, e:
                _logger.error("URL %s is not a Product page" % url)
            except ServiceUnavailable, e:
                _logger.error("URL %s unavailable" % url)
            except Exception, e:
                _logger.error("URL %s error" % url)
                traceback.print_exc(file=sys.stdout)
            q.task_done()

    q = Queue.LifoQueue()
    for url in iterator:
        q.put(url)
    
    workers = []
    for i in range(10):
        w = Worker(q, 9052 + i)
        workers.append(w)

    for w in workers:
        w.start()

    mon = Monitor(q, workers)
    mon.start()

    q.join()
    mon.finish()


@db_wrap
def get_urls(cur):
    #TODO: write SELECT from table with urls
    return test_urls * 10

if __name__ == "__main__":
    run_threaded(get_urls())

