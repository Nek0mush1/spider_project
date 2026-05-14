import pytest, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── 空库检查使用独立测试库 ──
_test_url = os.environ.get("TEST_DATABASE_URL")
if not _test_url or not _test_url.endswith("_test"):
    pytest.skip("TEST_DATABASE_URL 未设置或不以 _test 结尾", allow_module_level=True)
# ──────────────────────────


def test_quality_empty_db_prints_message(monkeypatch):
    """空数据库时 quality_checks 打印提示而不是除零崩溃"""
    monkeypatch.setenv("DATABASE_URL", _test_url)
    from dangdang_scrapy.db import reset_engine, init_db, get_engine
    from sqlalchemy import text

    reset_engine()
    init_db()
    # 确保表是空的
    with get_engine().begin() as conn:
        conn.execute(text("DELETE FROM books"))

    import quality_checks
    # 捕获 print 输出
    from io import StringIO
    captured = StringIO()
    old_stdout = sys.stdout
    sys.stdout = captured
    try:
        quality_checks.run()
    finally:
        sys.stdout = old_stdout

    output = captured.getvalue()
    assert "数据库为空" in output or "数据质量报告" in output
