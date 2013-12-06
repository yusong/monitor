# Scrapy settings for monitor project
#
# For simplicity, this file contains only the most important settings by
# default. All the other settings are documented here:
#
#     http://doc.scrapy.org/en/latest/topics/settings.html
#

BOT_NAME = 'monitor'

SPIDER_MODULES = ['monitor.spiders']
NEWSPIDER_MODULE = 'monitor.spiders'

# Crawl responsibly by identifying yourself (and your website) on the user-agent
#USER_AGENT = 'monitor (+http://www.yourdomain.com)'

SCHEDULER = "scrapy_redis.scheduler.Scheduler"
SCHEDULER_PERSIST = True
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderPriorityQueue"
SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderQueue"
#SCHEDULER_QUEUE_CLASS = "scrapy_redis.queue.SpiderStack"

ITEM_PIPELINES = [
	# 'monitor.pipelines.TestMongoPipeline',
	'monitor.pipelines.MongoPipeline',
]


REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379

MONGO_HOST = '127.0.0.1'
MONGO_PORT = 27017
MONGO_DB = 'monitor'
MONGO_RESULT_COLLECTION = 'result'
