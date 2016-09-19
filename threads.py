import random
import time
import threading
from threading import Thread
from threading import active_count as threading_active_count
import Queue
from stem.control import Controller
from stem import Signal
from helpers import *
import socks
import traceback
import sys
import requests
from scrapers import ServiceUnavailable, NotProductPage
import datetime

class NoMoreRetry(Exception):
    pass

class TorConnection(object):
    def __init__(self, proxy_port, timeout=HTTP_TIMEOUT_SEC):
        self.set_port(proxy_port)
        self.identity_counter = 0
        self.timeout = timeout
        self.success_counter = 0
        self.error_counter = 0
        self.suc_time = datetime.timedelta()
        self.err_time = datetime.timedelta()

    def get_avgs(self):
        s = None
        e = None
        if self.success_counter > 0:
            s = self.suc_time/self.success_counter
        if self.error_counter > 0:
            e = self.err_time/self.error_counter
        return "%s/%s" % (s,e)

    def set_port(self, port):
        if port is None:
            self.proxy_port = random.randint(0, NUM_TORS)
        else:
            self.proxy_port = port
        self.ctl_port = self.proxy_port - 934
        # print "Set Tor ports %s/%s" % (self.proxy_port, self.ctl_port)
        self.tor_control = Controller.from_port(port=self.ctl_port)

    def set_timeout(self, timeout):
        self.timeout = timeout

    def get_proxy(self):
        return 'localhost:%s' % self.proxy_port

    def get(self, *args, **kwargs):
        kwargs['proxies'] = dict(http='socks5://%s' % self.get_proxy(), https='socks5://%s' % self.get_proxy()) 
        kwargs['timeout'] = self.timeout
        starttime = datetime.datetime.now()
        try:
            resp = requests.get(*args, **kwargs)
            self.success_counter += 1
            endtime = datetime.datetime.now()
            self.suc_time += (endtime-starttime)
            return resp.text
        except:
            self.error_counter += 1
            endtime = datetime.datetime.now()
            self.err_time += (endtime-starttime)
            raise

    def get_with_retry(self, *args, **kwargs):
        r = kwargs.pop('retry_count', 1)
        for i in range(r):
            try:
                return self.get(*args, **kwargs)
            except Exception, e:
                self.change_identity()
        raise NoMoreRetry

    def change_identity(self):
        self.tor_control.authenticate('r2d2tor')
        self.tor_control.signal(Signal.NEWNYM)
        self.identity_counter += 1

    def change_identity_wait(self): 
        old_ip = self.ip()
        self.change_identity()
        if self.ip() == old_ip:
            time.sleep(0.5)

    def ip(self):
        try:
            return self.get_with_retry('http://bradheath.org/ip/', retry_count=3)
        except:
            return "n/a"

    def __str__(self):
        return "TorConnection port=[%s/%s] OK=%s FAILURE=%s IDENTITY=%s AVG=%s" % (self.proxy_port, self.ctl_port, self.success_counter, self.error_counter, self.identity_counter, self.get_avgs())
       

def get_variants_proxified(url, tor):
    for i in range(5):
        try:
            scraper = AliProductScraper(url, proxy=tor)
            return scraper.get_variants()
        except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable, requests.ConnectionError) as e:
            tor.change_identity_wait()
    raise ServiceUnavailable

def get_variants_fast(url, tor):
    tor.set_timeout(1)
    for i in range(5):
        try:
            scraper = AliProductScraper(url, proxy=tor)
            return scraper.get_variants()
        except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable, requests.ConnectionError) as e:
            tor.change_identity()
            tor.set_port(TOR_BASE_PORT + random.randint(0,NUM_TORS))
    raise ServiceUnavailable

class Worker(Thread):
    def __init__(self, queue, proxy_port, writer=write_to_db):
        Thread.__init__(self)
        self.queue = queue
        self.proxy = TorConnection(proxy_port)
        self.writer = writer
        self.result = None

    def run(self):
        while not self.queue.empty():
            url = self.queue.get()
            try:
                #save_variants(url, self.writer)
                #scraper = AliProductScraper(url, proxy=self.proxy.get_proxy())
                self.result = get_variants_proxified(url, self.proxy)
                self.writer(self.result)
                logger.info("URL %s OK" % url)
                time.sleep(1)
            #except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable, requests.ConnectionError) as e:
            #    self.proxy.change_identity()
            except ServiceUnavailable, e:
                self.queue.put(url)
                self.proxy.change_identity()
                time.sleep(5)
            except NotProductPage, e:
                logger.error("URL %s is not a Product page" % url)
            except Exception, e:
                logger.error("URL %s error" % url)
                traceback.print_exc(file=sys.stdout)
            self.queue.task_done()
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
            print "Elements in Queue:", self.queue.qsize(), "Active Threads:", len(self.workers)
            for w in self.workers:
                print "[%s] Worker with %s" % (" " if w.is_alive() else "X", w.proxy)


def run_all(iterator):
    q = Queue.LifoQueue()
    for url in iterator:
        q.put(url)

    workers = []
    for i in range(NUM_TORS):
        w = Worker(q, TOR_BASE_PORT + i)
        workers.append(w)

    for w in workers:
        w.start()

    mon = Monitor(q, workers)
    mon.start()

    q.join()
    mon.finish()


def run_one(url, writer):
    q = Queue.LifoQueue()
    q.put(url)
    w = Worker(q, TOR_BASE_PORT + random.randint(0,NUM_TORS), writer)
    w.run()
    q.join()
    return w.result


if __name__ == "__main__":
    run_all(get_urls())
