from chatops.runbooks import list_runbooks, request_runbook, confirm_runbook, cancel_runbook, dry_run_runbook


def test_list_runbooks_returns_all():
    assert len(list_runbooks()) == 7


def test_list_runbooks_has_fields():
    for rb in list_runbooks():
        assert all(k in rb for k in ["name", "description", "preview"])


def test_request_unknown_runbook():
    result = request_runbook("nonexistent")
    assert result["status"] == "error"
    assert "Available" in result["message"]


def test_request_valid_runbook():
    result = request_runbook("clear_tmp")
    assert result["status"] == "confirm"
    assert "confirm clear_tmp" in result["message"]


def test_confirm_without_request():
    assert confirm_runbook("clear_tmp")["status"] == "error"


def test_confirm_wrong_name():
    request_runbook("clear_tmp")
    assert confirm_runbook("large_logs")["status"] == "error"


def test_cancel_clears_pending():
    request_runbook("clear_tmp")
    cancel_runbook()
    assert confirm_runbook("clear_tmp")["status"] == "error"


def test_request_then_confirm_executes():
    request_runbook("listening_services")
    assert confirm_runbook("listening_services")["status"] == "ok"


def test_confirm_returns_output():
    request_runbook("listening_services")
    result = confirm_runbook("listening_services")
    assert isinstance(result.get("output"), str)
    assert len(result["output"]) > 0


# ── New runbooks ──────────────────────────────────────────────────────────────

def test_runbook_flush_cache_exists():
    names = [rb["name"] for rb in list_runbooks()]
    assert "flush_cache" in names


def test_runbook_rotate_logs_exists():
    names = [rb["name"] for rb in list_runbooks()]
    assert "rotate_logs" in names


def test_runbook_rotate_secret_exists():
    names = [rb["name"] for rb in list_runbooks()]
    assert "rotate_secret" in names


def test_runbook_rotate_secret_executes():
    request_runbook("rotate_secret")
    result = confirm_runbook("rotate_secret")
    assert result["status"] == "ok"
    assert "secret" in result["output"].lower() or len(result["output"]) > 10


def test_runbook_flush_cache_request():
    result = request_runbook("flush_cache")
    assert result["status"] == "confirm"
    assert "flush_cache" in result["message"]


def test_runbook_rotate_logs_request():
    result = request_runbook("rotate_logs")
    assert result["status"] == "confirm"
    assert "rotate_logs" in result["message"]


# ── Dry-run mode ──────────────────────────────────────────────────────────────

def test_dry_run_unknown_runbook():
    result = dry_run_runbook("nonexistent_xyz")
    assert result["status"] == "error"
    assert "Available" in result["message"]


def test_dry_run_clear_tmp_returns_ok():
    result = dry_run_runbook("clear_tmp")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]


def test_dry_run_clear_tmp_no_deletion():
    result = dry_run_runbook("clear_tmp")
    # Should describe intent, not confirm deletion
    assert "Would delete" in result["output"]


def test_dry_run_disk_breakdown():
    result = dry_run_runbook("disk_breakdown")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]


def test_dry_run_large_logs():
    result = dry_run_runbook("large_logs")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]


def test_dry_run_flush_cache():
    result = dry_run_runbook("flush_cache")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]


def test_dry_run_rotate_logs():
    result = dry_run_runbook("rotate_logs")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]
    assert "dry" in result["output"].lower() or "debug" in result["output"].lower()


def test_dry_run_rotate_secret_no_secret_generated():
    result = dry_run_runbook("rotate_secret")
    assert result["status"] == "ok"
    assert "[DRY RUN]" in result["output"]
    # No actual secret should be produced
    assert "would generate" in result["output"].lower() or "no secret" in result["output"].lower()


def test_dry_run_does_not_require_confirmation():
    # dry_run should work without any _pending state
    cancel_runbook()
    result = dry_run_runbook("clear_tmp")
    assert result["status"] == "ok"
