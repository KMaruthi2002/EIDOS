"""Learning from the tutorial videos: steps and values must match what the recorder did."""
import json
from pathlib import Path

import pytest
from eidos.ui.learn import analyze
from eidos.ui.tasks import TUTORIALS

ROOT = Path(__file__).resolve().parent.parent
KIND = {"click": "press", "type": "type", "choose": "choose", "toggle": "toggle"}


@pytest.mark.parametrize("task", list(TUTORIALS))
def test_learned_steps_match_the_recording(task, tmp_path):
    trace, prog = analyze(ROOT / "videos" / f"tutorial_{task}.mp4", tmp_path)
    want = TUTORIALS[task]
    assert [s["do"] for s in prog["steps"]] == [KIND[a[0]] for a in want]
    for s, a in zip(prog["steps"], want):
        if a[0] in ("type", "choose"):
            assert s["target"]["field"].lower() == a[1].lower()
            assert s["learned_from"] == a[2]
        elif a[0] == "click":
            assert s["target"]["text"].lower() == a[1].lower()
        else:
            assert s["target"]["row"].lower() == a[1].lower()
    # every typed or picked value became an input
    typed = {a[2] for a in want if a[0] in ("type", "choose")}
    assert set(prog["inputs"].values()) == typed
    # submit steps are checked against the values showing up, or a confirmation
    assert prog["steps"][-1]["contract"]["screen_shows"]
