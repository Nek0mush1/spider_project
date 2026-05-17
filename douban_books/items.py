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
    want_to_read = scrapy.Field()    # 想读人数
    reading = scrapy.Field()         # 在读人数
    read = scrapy.Field()            # 读过人数


class ReviewItem(scrapy.Item):
    book_url = scrapy.Field()
    review_url = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    rating = scrapy.Field()
    useful_count = scrapy.Field()
    useless_count = scrapy.Field()
    useful_ratio = scrapy.Field()
    replies_count = scrapy.Field()
    reviewer_name = scrapy.Field()
    reviewer_url = scrapy.Field()
    published_at = scrapy.Field()


class RatingDistributionItem(scrapy.Item):
    book_url = scrapy.Field()
    source = scrapy.Field()          # official | derived
    sample_size = scrapy.Field()
    star_5_count = scrapy.Field()
    star_4_count = scrapy.Field()
    star_3_count = scrapy.Field()
    star_2_count = scrapy.Field()
    star_1_count = scrapy.Field()
    star_5_pct = scrapy.Field()
    star_4_pct = scrapy.Field()
    star_3_pct = scrapy.Field()
    star_2_pct = scrapy.Field()
    star_1_pct = scrapy.Field()
    want_to_read = scrapy.Field()
    reading = scrapy.Field()
    read = scrapy.Field()


class UserProfileItem(scrapy.Item):
    reviewer_url = scrapy.Field()
    display_name = scrapy.Field()
    following_count = scrapy.Field()
    followers_count = scrapy.Field()
