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
from tor import TorConnection


def get_variants_proxified(url, tor):
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

    def run(self):
        while not self.queue.empty():
            url = self.queue.get()
            try:
                self.result = get_variants_proxified(url, self.proxy)
                self.writer(self.result)
                logger.info("URL %s OK" % url)
                time.sleep(2)
            except ServiceUnavailable, e:
                self.queue.put(url)
                self.proxy.change_identity()
                time.sleep(3)
            except NotProductPage, e:
                logger.error("URL %s is not a Product page" % url)
            except Exception, e:
                logger.error("URL %s error" % url)
                traceback.print_exc(file=sys.stdout)
            self.queue.task_done()
            #time.sleep(2)


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
