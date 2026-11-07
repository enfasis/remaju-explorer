from remaju.collector import challenge, initial_state, redact


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
