# -*- conding: utf8 -*-
import redis
from pymongo import Connection

# default values
MONGO_HOST = '127.0.0.1'
MONGO_PORT = 27017
TASK_DB	= 'monitor'
TASK_COLLECTION = 'tasks'
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_MAP = 'monitorspider:url'
EXTRA_MAP = 'monitorspider:extra'
SPIDER = 'monitorspider'


class MonitorCronJob(object):


	def __init__(self):
		self.mongo_host = MONGO_HOST
		self.mongo_port = MONGO_PORT
		self.redis_host = REDIS_HOST
		self.redis_port = REDIS_PORT
		self.rmap = REDIS_MAP
		self.emap = EXTRA_MAP
		self.ulist = '%s:start_urls' % SPIDER
		self.dupefilter_key = '%s:dupefilter' % SPIDER

		self._connectDB()
		self._connectRedis()
		self._cleanRedis()

	def __del__(self):
		self._disconnectDB()


	def _connectDB(self):
		self.c 			= Connection(self.mongo_host, self.mongo_port)
		self.db 		= self.c[TASK_DB]
		self.collection = self.db[TASK_COLLECTION]
		print "[log] Connect to MongoDB %s:%s" % (self.mongo_host, self.mongo_port)

	def _disconnectDB(self):
		self.c.disconnect()
		del self.c, self.db, self.collection
		print "[log] Disconnect from MongoDB %s:%s" % (self.mongo_host, self.mongo_port)

	def _alive(self):
		return True if self.c and self.c.alive() else False

	def _connectRedis(self):
		self.r = redis.Redis(host=self.redis_host, port=self.redis_port)
		print "[log] Connect to Redis %s:%s" % (self.redis_host, self.redis_port)

	def _cleanRedis(self):
		self.r.delete( self.rmap )
		print "[log] Clean url hash map of %s" % self.rmap
		self.r.delete( self.emap )
		print "[log] Clean extra url hash map of %s" % self.emap
		self.r.delete( self.dupefilter_key )
		print "[log] Clean dupefilter_key of %s" % self.dupefilter_key


	def read_task(self, rto_type='cursor'):
		""" Get tasks from MongoDB, then return a list
		"""
		if self._alive():

			cursor = self.collection.find({'state': 1})

			if rto_type == 'cursor':
				print "[log] Read %d tasks from DB" % cursor.count()
				return cursor

			elif rto_type == 'list':
				tasks = []
				for i in cursor:
					tasks.append( i )
				print "[log] Read %d tasks from DB" % len(tasks)
				return tasks
		
		else:
			pass
			

	def map_tasks(self):
		""" 
		Map tasks' url and SKU
		----------------------

		Task's structure
		{
			'sku' : string, product sku of feifei,
			'urls' : list, list of this task's urls
		}
		"""
		def to_redis(url):
			self.r.lpush( self.ulist, url )

		tasks = self.read_task( 'cursor' )

		for i in tasks:
			sku = i.get('sku', None)
			urls = i.get('urls', None)
			extras = i.get('extras', None)
			if sku:
				for url in urls:
					self.r.hset( self.rmap, url, sku ) # hset(hash, key, value)
					to_redis( url )
					print "[log] List %s to %s" % (url, self.ulist)
				for extra in extras:
					self.r.hset( self.rmap, extra, sku )
					to_redis( extra )
					print "[log] List %s to %s" % (extra, self.ulist)


	def test(self):

		with open('test.txt', 'ab') as f:
			f.write('1\n')


	def __getattribute__(self, name): 
		try:
		    rt = object.__getattribute__(self, name)
		except:
		    rt = None 
		return rt


if __name__ == "__main__":
	m = MonitorCronJob()
	m.map_tasks()