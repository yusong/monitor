# Define here the models for your scraped items
#
# See documentation in:
# http://doc.scrapy.org/en/latest/topics/items.html

from scrapy.item import Item, Field

class MonitorItem(Item):
    # define the fields for your item here like:
    # name = Field()
    pass


class ProductItem(Item):
    # fixed
    source		= Field()
    itemId 		= Field()
    name 		= Field()
    brand 		= Field()
    category	= Field()
    attr		= Field()
    # unfixed
    url			= Field()
    img 		= Field()
    relateSKU	= Field()
    tm_skuprice	= Field()
    # for sorting
    comment		= Field()
    price		= Field()
    tm_moonSellCount = Field()
    date		= Field()
    history		= Field()