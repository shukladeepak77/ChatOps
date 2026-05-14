from chatops.db import kb_add, kb_list, kb_search, kb_get, kb_delete
from chatops.router import route_message


def _resp(msg, role="admin"):
    return route_message(msg, caller_role=role).get("response", "")


# ── DB-level KB tests ─────────────────────────────────────────────────────────

def test_kb_add_returns_id():
    aid = kb_add("Test Title", "Test content body", tags="ops")
    assert isinstance(aid, int) and aid > 0


def test_kb_list_empty():
    assert kb_list() == []


def test_kb_list_after_add():
    kb_add("Article One", "Content one")
    kb_add("Article Two", "Content two")
    articles = kb_list()
    assert len(articles) == 2


def test_kb_list_fields():
    kb_add("Field Test", "Body here", tags="test")
    a = kb_list()[0]
    assert all(k in a for k in ["id", "title", "tags", "created_by", "created_at"])


def test_kb_get_existing():
    aid = kb_add("Get Test", "Some content")
    article = kb_get(aid)
    assert article is not None
    assert article["title"] == "Get Test"
    assert article["content"] == "Some content"


def test_kb_get_nonexistent():
    assert kb_get(9999) is None


def test_kb_search_by_title():
    kb_add("Nginx Setup Guide", "How to configure nginx")
    results = kb_search("nginx")
    assert len(results) >= 1
    assert any("Nginx" in r["title"] for r in results)


def test_kb_search_by_content():
    kb_add("Memory Tuning", "Use vm.swappiness to reduce swap usage")
    results = kb_search("swappiness")
    assert len(results) >= 1


def test_kb_search_by_tags():
    kb_add("Tagged Article", "Some body", tags="monitoring,alerts")
    results = kb_search("monitoring")
    assert len(results) >= 1


def test_kb_search_no_results():
    results = kb_search("xyznotfound123")
    assert results == []


def test_kb_delete_existing():
    aid = kb_add("To Delete", "Will be removed")
    assert kb_delete(aid) is True
    assert kb_get(aid) is None


def test_kb_delete_nonexistent():
    assert kb_delete(9999) is False


# ── Router-level KB tests ─────────────────────────────────────────────────────

def test_route_list_kb_empty():
    resp = _resp("list kb")
    assert "empty" in resp.lower() or "Knowledge base" in resp


def test_route_add_kb():
    resp = _resp("add kb High CPU Fix: Check top processes and kill offending PID")
    assert "added" in resp.lower()
    assert "High CPU Fix" in resp


def test_route_show_kb():
    aid = kb_add("Show Test", "Detailed content here", tags="test")
    resp = _resp(f"show kb {aid}")
    assert "Show Test" in resp
    assert "Detailed content here" in resp


def test_route_show_kb_invalid_id():
    resp = _resp("show kb 9999")
    assert "No KB article" in resp


def test_route_search_kb_found():
    kb_add("Redis Cache", "Flush redis with FLUSHALL command")
    resp = _resp("search kb redis")
    assert "Redis" in resp


def test_route_search_kb_not_found():
    resp = _resp("search kb xyznotfound123")
    assert "No KB articles" in resp


def test_route_delete_kb_admin():
    aid = kb_add("Delete Me", "Content")
    resp = _resp(f"delete kb {aid}", role="admin")
    assert "deleted" in resp.lower()


def test_route_delete_kb_non_admin():
    aid = kb_add("Protected", "Content")
    resp = _resp(f"delete kb {aid}", role="operator")
    assert "denied" in resp.lower() or "Access" in resp


def test_route_list_kb_shows_articles():
    kb_add("Article A", "Body A")
    kb_add("Article B", "Body B")
    resp = _resp("list kb")
    assert "Article A" in resp
    assert "Article B" in resp
