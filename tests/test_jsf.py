import pytest

from remaju.jsf import parse_partial_response


def test_partial_response_extracts_updates_and_redirect():
    response = parse_partial_response('<partial-response><changes><update id="component"><![CDATA[<div>hello</div>]]></update><update id="javax.faces.ViewState"><![CDATA[token]]></update></changes><redirect url="/list"/></partial-response>')
    assert response.updates == {"component": "<div>hello</div>", "javax.faces.ViewState": "token"}
    assert response.redirect == "/list"


@pytest.mark.parametrize("payload", ["not xml", "<html/>", '<!DOCTYPE x [<!ENTITY x "hello">]><partial-response/>' , '<partial-response><changes><update id="a"/><update id="a"/></changes></partial-response>'])
def test_invalid_partial_responses_fail(payload):
    with pytest.raises(ValueError):
        parse_partial_response(payload)
