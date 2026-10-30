"""Perception from pixels: labels, fields, buttons, switches, on/off state."""
import pytest
from eidos.ui import see as S
from eidos.ui.learn import label_for

DESIGNS = ["skin=A", "skin=B", "skin=A&theme=dark&labels=top&scale=1.2", "skin=B&theme=dark&nav=right&labels=left"]
FORMS = {"mail": ("Compose", ["To", "Subject", "Message"], "Send"),
         "calendar": ("New event", ["Title", "Date", "Time", "Location"], "Save"),
         "expense": ("New expense", ["Merchant", "Amount", "Category"], "Submit")}


@pytest.mark.parametrize("design", DESIGNS)
@pytest.mark.parametrize("task", list(FORMS))
def test_every_field_found_by_its_label(shot, task, design):
    opener, labels, submit = FORMS[task]
    img = shot(f"task={task}&{design}", lambda p: p.get_by_text(opener, exact=True).first.click())
    lines, boxes = S.lines(img), S.boxes(img)
    found = {}
    for lab in labels:
        for hit in S.find_text(lines, lab, 0.8):
            f = S.field_for(hit, boxes)
            if f:
                own = label_for(f, lines, boxes)
                if own and S.sim(own.text, lab) >= 0.86:
                    found[lab] = f
                    break
    assert set(found) == set(labels), f"missing {set(labels) - set(found)}"
    assert len({tuple(v) for v in found.values()}) == len(labels), "two labels mapped to one box"
    assert S.find_text(lines, submit, 0.84), f"submit button '{submit}' not read"


@pytest.mark.parametrize("design", DESIGNS)
def test_switch_state(shot, design):
    img = shot(f"task=settings&{design}", lambda p: p.get_by_text("Security", exact=True).first.click())
    lines, boxes = S.lines(img), S.boxes(img)
    state = {}
    for lab in ["Two-factor sign-in", "Sign-in alerts", "Remember this device"]:
        hit = S.find_text(lines, lab, 0.8)
        assert hit, f"label {lab} not read"
        sw = S.switch_for(hit[0], boxes, lines)
        assert sw, f"no switch next to {lab}"
        state[lab] = S.is_on(img, sw)
    assert state == {"Two-factor sign-in": False, "Sign-in alerts": False, "Remember this device": True}
