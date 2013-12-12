# -*- conding: utf8 -*-
import redis
from pymongo import Connection
from datetime import datetime
from twisted.internet.threads import deferToThread


class TestMongoPipeline(object):

	def open_spider(self, spider):

		mongo_host = '127.0.0.1'
		mongo_port = 27017
		mongo_db = 'test'
		result_collection = 'result'

		self.c 			= Connection(mongo_host, mongo_port)
		self.db 		= self.c[mongo_db]
		self.collection = self.db[result_collection]

	def close_spider(self, spider):

		del self.c, self.db, self.collection

	def process_item(self, item, spider):
	    
		self.collection.save( dict(item) )
		return item


class MongoPipeline(object):
	"""Pushes item into mongo
	"""

	def __init__(self):

		mongo_host = '127.0.0.1'
		mongo_port = 27017
		mongo_db = 'monitor'
		result_collection = 'result'

		self.c 			= Connection(mongo_host, mongo_port)
		self.db 		= self.c[mongo_db]
		self.collection = self.db[result_collection]

		redis_host = '127.0.0.1'
		redis_port = 6379

		self.redis_map  = 'monitorspider:url'
		self.extra_map	= 'monitorspider:extra'
		self.r 			= redis.Redis(host=redis_host, port=redis_port)

	
	def __del__(self):

		del self.c, self.db, self.collection


	def process_item(self, item, spider):

		return deferToThread(self._process_item, item, spider)


	def _process_item(self, item, spider):

		url = item.get('url')
		name = item.get('name')
		price = item.get('price')
		source = item.get('source')
		tm_store = item.get('tm_store')
		tm_moonSellCount = item.get('tm_moonSellCount')
		category = item.get('category')
		itemId = item.get('itemId')
		extra = False # check item from urls or extra
		sku = self.r.hget(self.redis_map, url) 
		if not sku:
			extra = True
			start_url = item.get('start_url')
			sku = self.r.hget(self.extra_map, start_url)

		result_item = self.collection.find_one({'sku': sku})

		if not result_item:
			# no record
			rto = {
				'sku' : sku,
				'date' : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
			}

			if source == 'feifei':
				rto['category'] = category

			if not extra:
				# item not from extras
				if source == 'tmall':
					rto['priceList'] = { source : { 'url' : url, 'name' : name, 'price' : price, 'tm_store' : tm_store, 'tm_moonSellCount' : tm_moonSellCount } }
				else:
					rto['priceList'] = { source : { 'url' : url, 'name' : name, 'price' : price } }
			else:
				# item from extras
				if source == 'tmall':
					rto['extraList'] = {
						itemId : { 'url' : url, 'name': name, 'price': price, 'tm_store' : tm_store, 'tm_moonSellCount' : tm_moonSellCount }
					}
				else:
					rto['extraList'] = {
						name : { 'url' : url, 'name': name, 'price': price }
					}

			self.collection.save( rto )
			
		else:
			# has record
			date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

			if not extra:
				# item not from extras
				priceList = result_item.get('priceList', {})
				if price:
					# sometimes tmall item with no price
					priceList[ source ] = {
						'url' : url,
						'name' : name,
						'price' : price
					}
					if source == 'tmall':
						priceList[ source ]['tm_moonSellCount'] = tm_moonSellCount
						priceList[ source ]['tm_store'] = tm_store
					if source == 'feifei':
						self.collection.update( {'sku':sku}, {'$set': {'date': date, 'category': category, 'priceList': priceList}} )
					else:
						self.collection.update( {'sku':sku}, {'$set': {'date': date, 'priceList': priceList}} )

			else:
				# item from extras
				extraList = result_item.get('extraList', {})
				if price:
					extraList[ itemId ] = {
						'url' : url,
						'name' : name,
						'price' : price,
						'tm_moonSellCount' : tm_moonSellCount,
						'tm_store' : tm_store
					}
					if source == 'feifei':
						self.collection.update( {'sku':sku}, {'$set': {'date': date, 'category': category, 'extraList': extraList}} )
					else:
						self.collection.update( {'sku':sku}, {'$set': {'date': date, 'extraList': extraList}} )

		return item
