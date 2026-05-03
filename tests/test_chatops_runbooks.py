from chatops.runbooks import list_runbooks, request_runbook, confirm_runbook, cancel_runbook


def test_list_runbooks_returns_all():
    assert len(list_runbooks()) == 4


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
