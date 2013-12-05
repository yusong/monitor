# -*- conding: utf8 -*-
from apscheduler.scheduler import Scheduler
from apscheduler.jobstores.mongodb_store import MongoDBJobStore
import pymongo
import os

from MonitorCronJob import MonitorCronJob


SETTING = {
	'host' : '127.0.0.1',
	'port' : 27017
}


def start( config={} ):

	# params init
	mongo_host = config.get('host', SETTING['host'])
	mongo_port = config.get('port', SETTING['port'])

	db = pymongo.Connection(mongo_host, mongo_port)  
	store = MongoDBJobStore(connection=db) 

	# create schedudler and run
	scheduler = Scheduler(daemonic=False)
	scheduler.start()
	scheduler.add_jobstore(store, 'mongo') 

	# add cron jobs
	scheduler.add_cron_job(monitor_cron_job, hour='0-23', minute="0,30", jobstore='mongo')
	# test cron job
	# scheduler.add_cron_job(test_cron_job, hour='0-23', minute="0-59", second='0', jobstore='mongo')


mcj = MonitorCronJob()


def monitor_cron_job():
	""" Monitor cron job
	"""
	mcj.map_tasks()


# def test_cron_job():
# 	""" Just a test function
# 	"""
# 	mcj.test()


if __name__ == "__main__":

	# start Cron Jobs
	start(config=SETTING)
	# test_cron_job()

	# start monitorspider
	os.system( "scrapy crawl monitorspider" )