import scrapy


class BookItem(scrapy.Item):
    name = scrapy.Field()
    author = scrapy.Field()
    publisher = scrapy.Field()
    price = scrapy.Field()
    original_price = scrapy.Field()
    rating = scrapy.Field()
    rating_people = scrapy.Field()
    sales = scrapy.Field()
    detail_url = scrapy.Field()
    category = scrapy.Field()
