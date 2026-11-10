from utils.debugger import challenge, diagnostic_error, diagnostic_url, redact


def test_sensitive_values_are_redacted():
    assert "secret" not in redact('<input name="javax.faces.ViewState" value="secret">')
    assert "secret" not in redact('<update id="javax.faces.ViewState"><![CDATA[secret]]></update>')
    assert "secret" not in redact('/resource;jsessionid=secret?x=1')


def test_challenge_is_distinct_from_site_image_captcha():
    assert challenge("<div class='h-captcha'>")
    assert not challenge('<input name="captcha">')


def test_challenge_recognizes_other_interactive_providers():
    assert challenge('<div class="g-recaptcha">')
    assert challenge('<div class="cf-turnstile">')
    assert challenge('<script src="/cdn-cgi/challenge-platform/test">')


def test_diagnostic_urls_omit_credentials_query_values_and_fragments():
    url = "https://user:secret@example.com/path;jsessionid=secret?token=secret#secret"
    assert diagnostic_url(url) == "https://example.com/path;jsessionid=[redacted]?[redacted]"
    assert diagnostic_url("/challenge?token=secret") == "/challenge?[redacted]"


def test_errors_do_not_expose_url_secrets():
    error = ValueError("503 Server Error for url: https://example.com/path?token=secret")
    assert diagnostic_error(error) == "503 Server Error for url: https://example.com/path?[redacted]"
