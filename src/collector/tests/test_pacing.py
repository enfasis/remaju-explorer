from unittest.mock import Mock

from utils.site import RemajuSite, list_page, polite_pause


def test_pause_is_half_second_plus_jitter(monkeypatch):
    sleep = Mock()
    jitter = Mock(return_value=0.25)
    monkeypatch.setattr("utils.site.time.sleep", sleep)
    monkeypatch.setattr("utils.site.random.uniform", jitter)
    polite_pause()
    jitter.assert_called_once_with(0, 0.5)
    sleep.assert_called_once_with(0.75)


def test_get_and_post_both_pause_before_request():
    events = []
    trace = Mock()
    trace.request.side_effect = lambda *args: events.append("request") or "response"
    site = RemajuSite(trace, Mock(), lambda: events.append("pause"))
    site.view = Mock()
    site.view.perform.side_effect = lambda interaction, request: (request("list-page", {}), None)
    site.get("https://example.org", "list-init")
    site.post("https://example.org", list_page(0))
    assert events == ["pause", "request", "pause", "request"]
