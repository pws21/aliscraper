import time
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
                logger.info("URL %s OK" % url)
            except (requests.ReadTimeout, socks.GeneralProxyError, ServiceUnavailable) as e:
                self.change_identity()
            except NotProductPage, e:
                logger.error("URL %s is not a Product page" % url)
            except Exception, e:
                logger.error("URL %s error" % url)
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

def run_threaded(iterator):
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

if __name__ == "__main__":
    run_threaded(get_urls())