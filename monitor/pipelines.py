# -*- conding: utf8 -*-
import redis
from pymongo import Connection
from datetime import datetime
from twisted.internet.threads import deferToThread


class ExamplePipeline(object):
    def process_item(self, item, spider):
        item["crawled"] = datetime.utcnow()
        item["spider"] = spider.name
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
		sku = self.r.hget(self.redis_map, url)

		result_item = self.collection.find_one({'sku': sku})

		if not result_item:
			# no record
			rto = {
				'sku' : sku,
				'date' : datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
				'priceList': {
					source : {
						'url' : url,
						'name' : name,
						'price' : price
					}
				}		
			}
			if source == 'feifei':
				rto['category'] = item.get('category')

			self.collection.save( rto )

		else:
			# has record
			date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
			priceList = result_item['priceList']

			if price:
				# sometimes tmall item with no price
				priceList[ source ] = {
					'url' : url,
					'name' : name,
					'price' : price
				}

				self.collection.update( {'sku':sku}, {'$set': {'date': date, 'priceList': priceList}} )

		return item
