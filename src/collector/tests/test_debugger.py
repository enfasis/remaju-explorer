from utils.debugger import challenge, redact


def test_sensitive_values_are_redacted():
    assert "secret" not in redact('<input name="javax.faces.ViewState" value="secret">')
    assert "secret" not in redact('<update id="javax.faces.ViewState"><![CDATA[secret]]></update>')
    assert "secret" not in redact('/resource;jsessionid=secret?x=1')


def test_challenge_is_distinct_from_site_image_captcha():
    assert challenge("<div class='h-captcha'>")
    assert not challenge('<input name="captcha">')
