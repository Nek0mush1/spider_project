import scrapy


class DoubanBookItem(scrapy.Item):
    url = scrapy.Field()             # 豆瓣完整链接（唯一键）
    title = scrapy.Field()           # 书名
    authors = scrapy.Field()         # 作者（多人逗号分隔）
    publisher = scrapy.Field()       # 出版社
    pubdate = scrapy.Field()         # 出版日期
    price = scrapy.Field()           # 定价
    rating = scrapy.Field()          # 豆瓣评分（0-10）
    votes = scrapy.Field()           # 评分人数
