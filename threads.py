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
from scrapers import ServiceUnavailable, NotProductPage, AliProductScraper
import datetime
from tor import TorConnection, NoMoreRetry


def get_variants_hard(url, tor):
    for i in range(5):
        try:
            scraper = AliProductScraper(url, proxy=tor)
            return scraper.get_variants()
        except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable, requests.ConnectionError) as e:
            tor.change_identity_wait()
                
    raise ServiceUnavailable

def get_variants_fast(url, tor):
    tor.set_timeout(2)
    for i in range(NUM_TORS):
        try:
            scraper = AliProductScraper(url, proxy=tor)
            return scraper.get_variants()
        except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable, requests.ConnectionError) as e:
            tor.change_identity()
            tor.next_port()
    raise ServiceUnavailable

class Worker(Thread):
    def __init__(self, queue, proxy_port, writer=write_to_db):
        Thread.__init__(self)
        self.queue = queue
        self.proxy = TorConnection(proxy_port)
        self.writer = writer
        self.result = None
        self.stat = {}
        self.state = 'FREE'
        self.running = True

    def finish(self):
        self.running = False
        self.state='STOP'

    def run(self):
        while self.running:
            try:
                url = self.queue.get(False)
                try:
                    self.state = 'WORK'
                    self.result = get_variants_hard(url, self.proxy)
                    self.writer(self.result)
                    logger.info("URL %s OK" % url)
                    self.stat['ok'] = self.stat.get('ok', 0) + 1
                    time.sleep(1)
                except (ServiceUnavailable, NoMoreRetry), e:
                    self.queue.put(url)
                    self.proxy.change_identity()
                    self.stat['err'] = self.stat.get('err', 0) + 1
                    self.state = 'WAIT'
                    time.sleep(2)
                except NotProductPage, e:
                    self.stat['err'] = self.stat.get('err', 0) + 1
                    logger.error("URL %s is not a Product page" % url)
                except Exception, e:
                    self.stat['err'] = self.stat.get('err', 0) + 1
                    logger.error("URL %s error" % url)
                    traceback.print_exc(file=sys.stdout)
                self.queue.task_done()
                #time.sleep(2)
            except Queue.Empty, e:
                self.state = 'FREE'
                time.sleep(0.5)

    def __str__(self):
        return "[%s] W-%-3s [%4s/%-4s] %s" % (self.state, xstr(self.ident), self.stat.get('ok',0), self.stat.get('err', 0), self.proxy)


class Monitor(Thread):
    def __init__(self, queue, workers):
        Thread.__init__(self)
        self.queue = queue
        self.finish_signal = False
        self.workers = workers

    def finish(self):
        self.finish_signal = True


    def run(self):
        started = datetime.datetime.now()
        while not self.finish_signal:
            time.sleep(2)
            live = filter(lambda w: w.is_alive(), self.workers)
            now = datetime.datetime.now()
            print "Elements in Queue:", self.queue.qsize(), "Active Threads:", len(live), "Time:", (now-started)
            for w in self.workers:
                print w


def run_all(iterator, writer=write_to_db, num_threads=NUM_TORS, with_monitor=True):
    q = Queue.LifoQueue()
    for url in iterator:
        q.put(url)

    workers = []
    for i in range(min([NUM_TORS, num_threads])):
        w = Worker(q, TOR_BASE_PORT + i, writer=writer)
        workers.append(w)

    for w in workers:
        w.start()

    if with_monitor:
        mon = Monitor(q, workers)
        mon.start()

    q.join()
    for w in workers:
         w.finish()
         w.join()

    if with_monitor:
        mon.finish()
        mon.join()


def run_one(url, writer):
    tor = TorConnection(proxy_port=None)
    rows = get_variants_fast(url, tor)
    writer(rows)
    #run_all([url, ], writer, 2)


#if __name__ == "__main__":
#    run_all(get_urls())
