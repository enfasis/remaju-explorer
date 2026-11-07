from remaju.collector import LIST_ID, challenge, collect_sample, initial_state, redact


def test_sensitive_values_are_redacted():
    assert "secret" not in redact('<input name="javax.faces.ViewState" value="secret">')
    assert "secret" not in redact('<update id="javax.faces.ViewState"><![CDATA[secret]]></update>')
    assert "secret" not in redact('/resource;jsessionid=secret?x=1')


def test_known_html_fixture_has_jsf_state(sample_data_dir):
    html = (sample_data_dir / "list_page.html").read_text(encoding="utf-8")
    state, fields = initial_state(html)
    assert state
    assert fields["javax.faces.ViewState"] == state


def test_challenge_is_distinct_from_site_image_captcha():
    assert challenge("<div class='h-captcha'>")
    assert not challenge('<input name="captcha">')


def test_sample_collection_uses_declared_interaction_offline(monkeypatch, tmp_path, sample_data_dir, list_xml):
    html = (sample_data_dir / "list_page.html").read_text(encoding="utf-8")
    calls = []

    class Response:
        status_code = 200

        def __init__(self, text):
            self.text = text

        def raise_for_status(self):
            pass

    class Session:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def request(self, method, url, **kwargs):
            calls.append((method, kwargs))
            return Response(html if method == "GET" else list_xml)

    monkeypatch.setattr("remaju.collector.requests.Session", Session)
    report = collect_sample(tmp_path)
    assert report["status"] == "partial"
    assert report["count"] > 0
    assert report["publishable"] is False
    assert [call[0] for call in calls] == ["GET", "POST"]
    assert calls[1][1]["data"]["javax.faces.source"] == LIST_ID
    assert calls[1][1]["data"]["javax.faces.ViewState"] == initial_state(html)[0]
