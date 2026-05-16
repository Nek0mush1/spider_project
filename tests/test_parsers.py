"""TDD parser tests with fixtures — no network requests. 8-column schema."""

from pathlib import Path

import pytest
from lxml import html as lxml_html
from scrapy.http import HtmlResponse

from douban_books.parsers import (
    extract_subject_id,
    parse_list_items,
    parse_detail,
    parse_votes,
    parse_rating_score,
    parse_info_table,
    parse_title,
)

# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def _html_response(fixture_name: str, url: str | None = None) -> HtmlResponse:
    """Load a fixture HTML file and wrap it in a Scrapy HtmlResponse."""
    path = FIXTURES / fixture_name
    body = path.read_bytes()
    if url is None:
        url = f"https://book.douban.com/subject/1000005/"
    return HtmlResponse(url=url, body=body, encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. test_extract_subject_id
# ---------------------------------------------------------------------------

class TestExtractSubjectId:
    def test_full_url(self):
        assert extract_subject_id("https://book.douban.com/subject/1000005/") == "1000005"

    def test_relative_path(self):
        assert extract_subject_id("/subject/1234567/") == "1234567"

    def test_no_subject_path(self):
        assert extract_subject_id("https://book.douban.com/tag/小说") is None

    def test_empty_string(self):
        assert extract_subject_id("") is None

    def test_none_input(self):
        assert extract_subject_id(None) is None


# ---------------------------------------------------------------------------
# 2. test_parse_list_items
# ---------------------------------------------------------------------------

class TestParseListItems:
    def test_parses_two_items(self):
        response = _html_response("top250_page.html")
        items = parse_list_items(response)

        assert isinstance(items, list)
        assert len(items) == 2

        # First item
        item0 = items[0]
        assert item0["subject_id"] == "1000005"
        assert item0["title"] == "百年孤独"
        assert item0["detail_url"] == "https://book.douban.com/subject/1000005/"
        assert item0["rating_avg"] == 9.2

        # Second item
        item1 = items[1]
        assert item1["subject_id"] == "1008145"
        assert item1["title"] == "围城"
        assert item1["detail_url"] == "https://book.douban.com/subject/1008145/"
        assert item1["rating_avg"] == 9.0


# ---------------------------------------------------------------------------
# 3. test_parse_detail  (8-field schema)
# ---------------------------------------------------------------------------

class TestParseDetail:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.response = _html_response(
            "detail_page.html",
            url="https://book.douban.com/subject/1000005/",
        )
        self.result = parse_detail(self.response)

    def test_url(self):
        assert self.result["url"] == "https://book.douban.com/subject/1000005/"

    def test_title(self):
        assert self.result["title"] == "百年孤独"

    def test_authors(self):
        assert self.result["authors"] == "加西亚·马尔克斯"

    def test_publishing_info(self):
        assert self.result["publisher"] == "南海出版公司"
        assert self.result["pubdate"] == "2011-6"
        assert self.result["price"] == "39.50元"

    def test_rating_and_votes(self):
        assert self.result["rating"] == 9.2
        assert self.result["votes"] == 280000

    def test_all_fields_present(self):
        """Verify exactly the 8 fields are present in the result dict."""
        expected_keys = {
            "url", "title", "authors", "publisher",
            "pubdate", "price", "rating", "votes",
        }
        assert set(self.result.keys()) == expected_keys


# ---------------------------------------------------------------------------
# 4. test_parse_detail_no_rating
# ---------------------------------------------------------------------------

class TestParseDetailNoRating:
    @pytest.fixture(autouse=True)
    def _setup(self):
        self.response = _html_response(
            "detail_no_rating.html",
            url="https://book.douban.com/subject/1008145/",
        )
        self.result = parse_detail(self.response)

    def test_title_present(self):
        assert self.result["title"] == "围城"

    def test_rating_is_none(self):
        assert self.result["rating"] is None

    def test_votes_are_zero(self):
        assert self.result["votes"] == 0

    def test_info_table_still_parsed(self):
        assert self.result["authors"] == "钱锺书"
        assert self.result["publisher"] == "人民文学出版社"
        assert self.result["pubdate"] == "1991-2"
        assert self.result["price"] == "19.00"


# ---------------------------------------------------------------------------
# 5. test_parse_votes_zero_or_missing
# ---------------------------------------------------------------------------

class TestParseVotesZeroOrMissing:
    def test_votes_present(self):
        tree = lxml_html.fromstring(
            '<div><span property="v:votes">280000</span></div>'
        )
        assert parse_votes(tree) == 280000

    def test_votes_are_zero_string(self):
        tree = lxml_html.fromstring(
            '<div><span property="v:votes">0</span></div>'
        )
        assert parse_votes(tree) == 0

    def test_votes_zero_with_text(self):
        tree = lxml_html.fromstring(
            '<div><span property="v:votes">0人评价</span></div>'
        )
        assert parse_votes(tree) == 0

    def test_votes_missing_element(self):
        tree = lxml_html.fromstring("<div></div>")
        assert parse_votes(tree) == 0

    def test_votes_fallback_selector(self):
        tree = lxml_html.fromstring(
            '<div><a class="rating_people"><span>350人评价</span></a></div>'
        )
        assert parse_votes(tree) == 350

    def test_votes_fallback_zero(self):
        tree = lxml_html.fromstring(
            '<div><a class="rating_people"><span>0人评价</span></a></div>'
        )
        assert parse_votes(tree) == 0


# ---------------------------------------------------------------------------
# 6. test_parse_info_table_basics  (4-field reduced schema)
# ---------------------------------------------------------------------------

class TestParseInfoTableBasics:
    def test_authors_from_info(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者:</span>加西亚·马尔克斯<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "加西亚·马尔克斯"

    def test_authors_with_link(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者:</span>'
            '<a href="https://book.douban.com/author/12345/">加西亚·马尔克斯</a>'
            '<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "加西亚·马尔克斯"

    def test_authors_clean_colon_prefix(self):
        """Author value with leading ': ' prefix should be cleaned."""
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者</span>: 张三<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "张三"

    def test_authors_clean_fullwidth_colon(self):
        """Leading fullwidth colon prefix should also be cleaned."""
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者</span>： 李四<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "李四"

    def test_publisher_from_info(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">出版社:</span>南海出版公司<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["publisher"] == "南海出版公司"

    def test_pubdate_from_info(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">出版年:</span>2020-1<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["pubdate"] == "2020-1"

    def test_price_from_info(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">定价:</span>42.00元<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["price"] == "42.00元"

    def test_all_info_fields(self):
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者:</span>张三<br/>'
            '<span class="pl">出版社:</span>人民文学出版社<br/>'
            '<span class="pl">出版年:</span>2020-1<br/>'
            '<span class="pl">定价:</span>42.00<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "张三"
        assert result["publisher"] == "人民文学出版社"
        assert result["pubdate"] == "2020-1"
        assert result["price"] == "42.00"

    def test_no_info_block(self):
        tree = lxml_html.fromstring("<div></div>")
        result = parse_info_table(tree)
        assert result["authors"] is None
        assert result["publisher"] is None
        assert result["pubdate"] is None
        assert result["price"] is None

    def test_ignores_old_fields(self):
        """Old fields like ISBN/translators/series should NOT appear in result."""
        tree = lxml_html.fromstring(
            '<div id="info">'
            '<span class="pl">作者:</span>张三<br/>'
            '<span class="pl">译者:</span>李四<br/>'
            '<span class="pl">ISBN:</span>9781234567890 / 123456789X<br/>'
            '<span class="pl">丛书:</span>测试丛书<br/>'
            '<span class="pl">页数:</span>300<br/>'
            '</div>'
        )
        result = parse_info_table(tree)
        assert result["authors"] == "张三"
        assert result["publisher"] is None
        assert "translators" not in result
        assert "isbn13" not in result
        assert "series" not in result
        assert "pages" not in result


# ---------------------------------------------------------------------------
# 7. test_missing_fields_return_none
# ---------------------------------------------------------------------------

class TestMissingFieldsReturnNone:
    def test_parse_title_missing(self):
        tree = lxml_html.fromstring("<div></div>")
        assert parse_title(tree) is None

    def test_parse_rating_score_missing(self):
        tree = lxml_html.fromstring("<div></div>")
        assert parse_rating_score(tree) is None

    def test_parse_rating_score_zero_string(self):
        tree = lxml_html.fromstring(
            '<strong class="ll rating_num" property="v:average">0.0</strong>'
        )
        assert parse_rating_score(tree) is None

    def test_parse_votes_missing(self):
        tree = lxml_html.fromstring("<div></div>")
        assert parse_votes(tree) == 0
