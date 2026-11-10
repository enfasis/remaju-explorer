import pytest

from utils.extract import LIST_ID
from utils.jsf import JsfSession, parse_partial_response
from utils.site import DETAIL_URL, click, list_page

LIST_PAGE = list_page(0)


def test_partial_response_extracts_updates_and_redirect():
    response = parse_partial_response('<partial-response><changes><update id="component"><![CDATA[<div>hello</div>]]></update><update id="javax.faces.ViewState"><![CDATA[token]]></update></changes><redirect url="/list"/></partial-response>')
    assert response.updates == {"component": "<div>hello</div>", "javax.faces.ViewState": "token"}
    assert response.redirect == "/list"


@pytest.mark.parametrize("payload", ["not xml", "<html/>", '<!DOCTYPE x [<!ENTITY x "hello">]><partial-response/>' , '<partial-response><changes><update id="a"/><update id="a"/></changes></partial-response>'])
def test_invalid_partial_responses_fail(payload):
    with pytest.raises(ValueError):
        parse_partial_response(payload)


def test_list_interaction_preserves_form_fields_and_builds_exact_payload():
    fields = {"form": "form", "javax.faces.ViewState": "old"}
    assert LIST_PAGE.payload(fields, "current") == {
        "form": "form",
        "javax.faces.ViewState": "current",
        "javax.faces.partial.ajax": "true",
        "javax.faces.source": LIST_ID,
        "javax.faces.partial.execute": LIST_ID,
        "javax.faces.partial.render": LIST_ID,
        "javax.faces.behavior.event": "page",
        "javax.faces.partial.event": "page",
        f"{LIST_ID}_pagination": "true",
        f"{LIST_ID}_first": "0",
        f"{LIST_ID}_rows": "4",
    }
    assert fields["javax.faces.ViewState"] == "old"


def test_interaction_uses_refreshed_state_on_next_request():
    session = JsfSession({"form": "form"}, "first")
    sent = []

    def send(action, payload):
        sent.append((action, payload))
        return f'<partial-response><changes><update id="{LIST_ID}">list</update><update id="javax.faces.ViewState">second</update></changes></partial-response>'

    session.perform(LIST_PAGE, send)
    session.perform(LIST_PAGE, send)
    assert [item[0] for item in sent] == ["list-page", "list-page"]
    assert [item[1]["javax.faces.ViewState"] for item in sent] == ["first", "second"]


@pytest.mark.parametrize("body", [
    '<partial-response><error><error-message>failed</error-message></error></partial-response>',
    '<partial-response><redirect url="/login"/></partial-response>',
    '<partial-response><changes><update id="other">x</update></changes></partial-response>',
    f'<partial-response><changes><update id="{LIST_ID}">x</update><update id="javax.faces.ViewState"></update></changes></partial-response>',
    'invalid',
])
def test_failed_interaction_does_not_change_state(body):
    session = JsfSession({}, "original")
    with pytest.raises(ValueError):
        session.perform(LIST_PAGE, lambda action, payload: body)
    assert session.state == "original"


def test_transport_failure_does_not_change_state():
    session = JsfSession({}, "original")

    def fail(action, payload):
        raise TimeoutError()

    with pytest.raises(TimeoutError):
        session.perform(LIST_PAGE, fail)
    assert session.state == "original"


def test_source_view_state_update_id_refreshes_state():
    session = JsfSession({}, "first")
    session.perform(LIST_PAGE, lambda action, payload: f'<partial-response><changes><update id="{LIST_ID}">list</update><update id="j_id1:javax.faces.ViewState:0"><![CDATA[second]]></update></changes></partial-response>')
    assert session.state == "second"


def test_navigation_click_accepts_redirect_and_sends_button():
    session = JsfSession({"form": "form"}, "state")
    sent = []
    interaction = click("detail-click", "form:list:0:j_idt169", DETAIL_URL)
    session.perform(interaction, lambda action, payload: sent.append(payload) or '<partial-response><redirect url="/remaju/pages/publico/mostrarDetalleRemate.xhtml"/></partial-response>')
    assert sent[0]["javax.faces.source"] == "form:list:0:j_idt169"
    assert sent[0]["form:list:0:j_idt169"] == "form:list:0:j_idt169"
    assert sent[0]["javax.faces.partial.execute"] == "@all"
    assert "javax.faces.partial.render" not in sent[0]


@pytest.mark.parametrize("target", [DETAIL_URL, "/remaju/pages/publico/mostrarDetalleRemate.xhtml", "mostrarDetalleRemate.xhtml"])
def test_navigation_accepts_only_the_expected_destination(target):
    session = JsfSession({}, "state")
    interaction = click("detail-click", "button", DETAIL_URL)
    session.perform(interaction, lambda action, payload: f'<partial-response><redirect url="{target}"/></partial-response>')


@pytest.mark.parametrize("target", [
    "/remaju/error/error500.xhtml",
    "/remaju/index.xhtml",
    "https://other.example/remaju/pages/publico/mostrarDetalleRemate.xhtml",
    "http://remaju.pj.gob.pe/remaju/pages/publico/mostrarDetalleRemate.xhtml",
    "/remaju/pages/publico/mostrarDetalleRemate.xhtml?token=secret",
    "",
])
def test_unexpected_navigation_does_not_change_state_or_expose_secrets(target):
    session = JsfSession({}, "original")
    interaction = click("tracking-click", "button", DETAIL_URL)
    body = f'<partial-response><redirect url="{target}"/><changes><update id="javax.faces.ViewState">new</update></changes></partial-response>'
    with pytest.raises(ValueError, match="Unexpected tracking-click redirect") as error:
        session.perform(interaction, lambda action, payload: body)
    assert "secret" not in str(error.value)
    assert session.state == "original"


def test_navigation_requires_a_redirect():
    interaction = click("detail-close", "button", DETAIL_URL)
    with pytest.raises(ValueError, match=r"Unexpected detail-close redirect: \(missing\)"):
        JsfSession({}, "state").perform(interaction, lambda action, payload: "<partial-response/>")
