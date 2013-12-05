# -*- coding: utf-8 -*-
from scrapy.selector import Selector
from scrapy.http import Request
from scrapy.contrib.spiders import CrawlSpider, Rule
from scrapy.contrib.linkextractors.sgml import SgmlLinkExtractor
from scrapy_redis.spiders import RedisMixin

from monitor.items import ProductItem

import json
import re
from datetime import date, datetime

from urllib import unquote

import sys
reload(sys)
sys.setdefaultencoding('utf8')


class TMSpider(RedisMixin, CrawlSpider):

    name = "tm"
    redis_key = 'tm:start_urls'
    allowed_domains = ["tmall.com", "taobao.com"]
    start_urls = []

    cat_map = {}

    rules = (

        Rule(   SgmlLinkExtractor(  allow=(r'detail.tmall.com'),
                                    restrict_xpaths=("//div[@id='J_ItemList']//p[@class='productTitle']"),
                                    unique=True),
                callback='parse_item', ),
        
        # Rule(   SgmlLinkExtractor(  allow=(r'list.tmall.com'),
        #                             restrict_xpaths=("//a[@class='ui-page-s-next']"),
        #                             unique=True), 
        #         follow=True ),
    
    )


    def __init__(self, *args, **kwargs):

        super(TMSpider, self).__init__(*args, **kwargs)

        self.action_type = kwargs.get('action_type', 'DEF_CALL')

        if self.action_type == 'BUSINESS_CALL':
            self.export_file_name = kwargs.get('export_file_name')

        if kwargs.get('start_urls'):
            self.start_urls = self.explain_urls( kwargs.get('start_urls') )
            # self.start_urls = [ kwargs.get('start_urls') ]


    def explain_urls(self, text):
        # remove header '####'
        text = text[4:]
        rto = []
        for group in text.split('####'):
            t = group.split('____')
            self.cat_map[t[1]] = unquote( t[0] ).decode('utf8')
            rto.append( t[1] )
        return rto


    def set_crawler(self, crawler):
        CrawlSpider.set_crawler(self, crawler)
        RedisMixin.setup_redis(self)


    def parse_item(self, response):
        """ Main parse function
        """
        sel = Selector(response)
        item = ProductItem()  

        item['source']  = 'tmall'       
        item['name']    = self.get_product_name( sel )        
        item['img']     = sel.xpath("//ul[@id='J_UlThumb']/li")[0].xpath(".//a/img/@src").extract()[0]

        item['category'] = self.get_category(response)
        
        try:
            # 获取TShop字符串，并对TShop字符串进行JSON标准化处理
            TShop_str = sel.re('TShop\.Setup\(((.|\n)+?)\);')[0]
            # 移除注释，目前只有天猫超市有注释，以逗号开头
            regex = re.compile(',\s*\/\/[^\n]*')
            TShop_str = re.sub(regex, ',', TShop_str)
            TShop = eval( TShop_str, type('Dummy', (dict,), dict(__getitem__=lambda s,n:n))() )      
        except SyntaxError:
            return  
        
        item['itemId']  = TShop.get('itemDO').get('itemId', '')
        item['url']     = 'http://detail.tmall.com/item.htm?id=' + item['itemId']
        item['date']    = date.today().strftime('%Y-%m-%d')
        item['attr'], item['brand'] = self.get_attr_and_brand( sel )
        
        skuMap = self.get_sku_chinese_map( sel, TShop )
        initApi_url = TShop.get('initApi')

        yield Request(  initApi_url, 
                        headers={'Referer': 'http://www.google.com.hk/'}, 
                        meta={'item': item, 'skuMap': skuMap}, 
                        callback=self.parse_initapi )


    def get_category(self, response):
        referer = response.request.headers.get('Referer', 'None')
        BASE_TM_LIST_URL = "http://list.tmall.com/search_product.htm?cat="
        # check referer contains list.tmall.com
        if referer:
            regex = re.compile('list.tmall.com')
            if regex.search( referer ):
                # get cat id
                regex2 = re.compile('cat=(\d+)')
                result = regex2.search( referer )
                if result:
                    url = BASE_TM_LIST_URL + result.group(1)
                    return self.cat_map.get(url, '')
        return ''


    def parse_initapi(self, response):
        """ 处理initApi的链接
        """
        item = response.meta['item']
        skuMap = response.meta['skuMap']
        item['relateSKU'] = {}
        try:
            initObj = eval( response.body.strip().decode('gbk'), type('Dummy', (dict,), dict(__getitem__=lambda s,n:n))() )
            priceInfo = initObj.get('defaultModel').get('itemPriceResultDO').get('priceInfo')
            for sku in skuMap.keys():
                item['relateSKU'][skuMap[sku]] = priceInfo[sku]
            item['price'] = self.get_default_price(priceInfo)
            item['tm_moonSellCount'] = initObj.get('defaultModel').get('sellCountDO').get('sellCount', 0)
        except:
            yield item
        else:
            yield Request( 'http://dsr.rate.tmall.com/list_dsr_info.htm?itemId=' + item['itemId'],
                            meta={'item': item},
                            callback=self.parse_comment )


    def parse_comment(self, response):
        """ 处理获取评论数的链接
        """
        item = response.meta['item']
        comment = re.findall('rateTotal\":(\d+)', response.body)[0]
        item['comment'] = int(comment) if comment.isdigit() else 0
        yield item


    def get_product_name(self, sel):
        """ 获取商品名
        """
        name_node = sel.xpath('//div[@id="J_DetailMeta"]//h3')

        if len(name_node.xpath('./a')) > 0:
            return name_node.xpath('./a/text()').extract()[0]
        elif len(name_node.xpath('./a')) == 0:
            return name_node.xpath('./text()').extract()[0]
        else:
            return ''


    def get_attr_and_brand(self, sel):
        """ 获取商品属性和品牌
        """
        attrs = sel.xpath('//ul[@id="J_AttrUL"]/li/text()').extract()

        attr_set = {}
        brand = ''

        for attr in attrs:
            if attr.count(':') > 0:
                # 中文冒号
                tmp = attr.split(':', 1)
                attr_set[tmp[0]] = tmp[1]
            elif attr.count('：') > 0:
                # 英文冒号
                tmp = attr.split('：', 1)
                attr_set[tmp[0]] = tmp[1]

            if tmp[0].find(u'品牌') >= 0:
                # 从属性里找品牌
                brand = tmp[1]

        return attr_set, brand


    def get_sku_chinese_map(self, sel, TShop):
        """ 获取SKU的中文名称
        """
        # SKU的中文title
        sku_key_set = {}
        specs = sel.xpath('//dl[@class="tb-prop tm-clear"]//ul')
        for spec in specs:
            # 获取规格值塞进对应的规格集合当中
            sku_key = spec.xpath('.//li/@data-value').extract()
            for key in sku_key:
                sku_title = spec.xpath('.//li[@data-value="' + key + '"]//span/text()').extract()[0]
                sku_key_set[key] = sku_title

        sku_map = TShop.get('valItemInfo').get('skuMap')
        # 拿到title跟sku的对应
        skuMap = {}
        if type(sku_map) == dict:
            for sku_key_str in sku_map.keys():
                sku_key = re.findall('\d+:\d+', sku_key_str)
                sku_title = ''
                for key in sku_key:
                    sku_title += sku_key_set[key] + '|'
                skuId = sku_map.get(sku_key_str).get('skuId', '')
                skuMap[skuId] = sku_title

        return skuMap


    def get_default_price(self, priceInfo):
        """ 计算商品的默认价格
        """
        def_obj = priceInfo.get('def', None)

        if def_obj:
            # 有Def属性
            promotionList = def_obj.get('promotionList', None)
            if type(promotionList) == list and len(promotionList) > 0:
                # 有促销信息
                min_price = sys.maxint
                for i in range( len(promotionList) ):
                    if promotionList[i].get('price') and float(promotionList[i].get('price')) < min_price:
                        min_price = float(promotionList[i].get('price'))
                return min_price
            else:
                # 没促销信息
                return float(def_obj.get('price'))
        else:
            # 没有def属性
            for sku in priceInfo:
                promotionList = priceInfo[sku].get('promotionList', None)
                if type(promotionList) == list and len(promotionList) > 0:
                    # 有促销信息
                    min_price = sys.maxint
                    for i in range( len(promotionList) ):
                        if promotionList[i].get('price') and float(promotionList[i].get('price')) < min_price:
                            min_price = float(promotionList[i].get('price'))
                    return min_price
                else:
                    # 没促销信息
                    return float(priceInfo[sku].get('price'))


    def parse_url(self, response):
        """ just for testing
        """
        sel = Selector(response)
        title = sel.xpath('/html/head/title/text()').extract()[0]
        open('file.txt', 'ab').write( '[Referer]: ' + response.request.headers.get('Referer', 'None') + '\n' + response.url + '\n')