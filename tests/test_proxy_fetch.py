from douban_books.proxy_fetch import (
    CurlFetchError,
    build_curl_command,
    expand_proxy_candidates,
    parse_curl_output,
    parse_proxy_url,
    raise_for_blocked_response,
)


def test_build_curl_command_includes_proxy_and_browser_headers():
    command = build_curl_command(
        url="https://book.douban.com/top250?start=0",
        proxy_url="https://user:pass@cn.decodo.com:30001",
        referer="https://book.douban.com/",
        timeout=25,
    )

    assert command[0] == "curl"
    assert "-x" in command
    assert "https://cn.decodo.com:30001" in command
    assert "-U" in command
    assert "user:pass" in command
    assert "https://book.douban.com/top250?start=0" in command
    assert "https://book.douban.com/" in command
    assert any("Accept: text/html,application/xhtml+xml" in value for value in command)
    assert any("Accept-Language: zh-CN" in value for value in command)
    assert any("Sec-Fetch-Site: same-origin" in value for value in command)
    assert any(value.startswith("Mozilla/5.0") for value in command)


def test_parse_curl_output_extracts_status_and_final_url():
    stdout = "<html>ok</html>\nCURLMETA:200 https://book.douban.com/top250?start=0\n"

    result = parse_curl_output(stdout)

    assert result.status_code == 200
    assert result.final_url == "https://book.douban.com/top250?start=0"
    assert result.body == "<html>ok</html>"


def test_raise_for_blocked_response_on_sec_redirect():
    result = parse_curl_output(
        "<title>豆瓣 - 登录跳转页</title>\n"
        "CURLMETA:403 https://sec.douban.com/b?r=https%3A%2F%2Fbook.douban.com%2Ftop250%3Fstart%3D0\n"
    )

    try:
        raise_for_blocked_response(result, "https://book.douban.com/top250?start=0")
    except CurlFetchError as exc:
        assert "sec.douban.com" in str(exc)
    else:
        raise AssertionError("Expected CurlFetchError for blocked response")


def test_parse_proxy_url_splits_auth_and_host():
    proxy = parse_proxy_url("https://user:pass@cn.decodo.com:30001")

    assert proxy.scheme == "https"
    assert proxy.username == "user"
    assert proxy.password == "pass"
    assert proxy.hostport == "cn.decodo.com:30001"


def test_expand_proxy_candidates_supports_port_range():
    proxies = expand_proxy_candidates(
        single_url="https://user:pass@cn.decodo.com:30001",
        pool="",
        ports="30001,30003",
    )

    assert proxies == [
        "https://user:pass@cn.decodo.com:30001",
        "https://user:pass@cn.decodo.com:30003",
    ]
