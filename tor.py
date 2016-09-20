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
        s = 0
        e = 0
        if self.success_counter > 0:
            s = self.suc_time / self.success_counter
            s = round(s.total_seconds(), 2)
        if self.error_counter > 0:
            e = self.err_time / self.error_counter
            e = round(e.total_seconds(), 2)
        return "%04.2f/%04.2f" % (s, e)

    def get_totals(self):
        return "%05.1f/%05.1f" % (round(self.suc_time.total_seconds(),1), round(self.err_time.total_seconds(),1))

    def set_port(self, port):
        if port is None:
            self.proxy_port = TOR_BASE_PORT + random.randint(0, NUM_TORS-1)
        else:
            self.proxy_port = port
        self.ctl_port = self.proxy_port - 934
        #print "Set Tor ports %s/%s" % (self.proxy_port, self.ctl_port)
        self.tor_control = Controller.from_port(port=self.ctl_port)

    def next_port(self): 
        if self.proxy_port + 1 > TOR_BASE_PORT + NUM_TORS - 1:
            self.set_port(TOR_BASE_PORT)
        else:
            self.set_port(self.proxy_port + 1)

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
        self.tor_control.authenticate(TOR_PASSWORD)
        self.tor_control.signal(Signal.NEWNYM)
        self.identity_counter += 1

    def change_identity_wait(self): 
        old_ip = self.ip()
        self.change_identity()
        counter = 1
        while self.ip() == old_ip:
            if counter > 6:
                raise NoMoreRetry
            self.change_identity()
            counter += 1
            time.sleep(0.5)

    def ip(self):
        try:
            return self.get_with_retry('http://bradheath.org/ip/', retry_count=3)
        except:
            return "n/a"

    def __str__(self):
        return "TorConn(%s,%s) Requests [%4s/%-4s] ChIP=[%04d] AvgTime [%s] TotalTime [%s]" % (self.proxy_port, self.ctl_port, self.success_counter, self.error_counter, self.identity_counter, self.get_avgs(), self.get_totals())
       

