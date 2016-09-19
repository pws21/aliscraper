import re
import json
import requests
from BeautifulSoup import BeautifulSoup
from settings import *

class NotProductPage(Exception):
    pass


class ServiceUnavailable(Exception):
    pass


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
        if proxy:
            response = proxy.get(url)
        else:
            response = http_get(url)
        self.content = response

    def get_price(self):
        m = re.search('\"price\":\"([0-9\.]+)\"', self.content)
        if m:
            return m.groups(0)[0]
        else:
            return None

def http_get(url, cookies=None, proxy='localhost:9050', headers={}):
    response = requests.get(url, timeout=HTTP_TIMEOUT_SEC, cookies=cookies,
                            #proxies=dict(http='socks5://%s' % proxy, https='socks5://%s' % proxy), 
                            headers=headers)
    return response.text


class AliProductScraper(object):
    def __init__(self, url, proxy):
        self.url = url
        self.proxy = proxy
        #_tor.new_identity()
        headers = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip,deflate',
            'Accept-Language': 'en-US,en;q=0.8',
            'Cache-Control': 'max-age=0',
            'Connection': 'keep-alive','user-agent': 'Googlebot/2.1'}
        if proxy:
            response = proxy.get(self.url, cookies={'aep_usuc_f': 'region=US&site=glo&b_locale=en_US&c_tp=USD'}, headers=headers)
        else:
            response = http_get(self.url, cookies={'aep_usuc_f': 'region=US&site=glo&b_locale=en_US&c_tp=USD'}, headers=headers)
        #html = response.text
        #print html
        self.soup = BeautifulSoup(response)

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





