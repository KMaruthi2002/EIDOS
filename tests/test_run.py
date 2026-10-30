"""End-to-end runs on hard layouts (slow: real browser, real OCR)."""
import json
import random
from pathlib import Path

import pytest
from eidos.ui.run import run_ui, replay_ui
from eidos.ui.tasks import URL, fresh_inputs, score

ROOT = Path(__file__).resolve().parent.parent
HARD = {"mail": "skin=B&theme=dark&order=2,0,1", "calendar": "skin=B&theme=dark&order=3,1,2,0&labels=left",
        "expense": "skin=A&theme=dark&labels=top&btn=top&scale=1.2&order=2,0,1", "settings": "skin=B&theme=dark&order=2,1,0"}


def prog(task):
    return json.loads((ROOT / "runs" / f"ui_skill_{task}" / "program.json").read_text())


@pytest.mark.slow
@pytest.mark.asyncio
@pytest.mark.parametrize("task", list(HARD))
async def test_eidos_on_a_hard_redesign(studio, task, tmp_path):
    p = prog(task)
    inputs = {**p["inputs"], **fresh_inputs(task, random.Random(123))}
    rep = await run_ui(p, f"{studio}{URL}?task={task}&{HARD[task]}", tmp_path, inputs)
    truth = score(task, rep["oracle_state"], inputs)
    assert truth["success"], truth
    assert rep["all_contracts_passed"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_eidos_repairs_an_interruption_and_verdict_is_honest(studio, tmp_path):
    p = prog("mail")
    inputs = {**p["inputs"], **fresh_inputs("mail", random.Random(7))}
    rep = await run_ui(p, f"{studio}{URL}?task=mail&skin=A&popup=5", tmp_path, inputs)
    truth = score("mail", rep["oracle_state"], inputs)
    assert rep["all_contracts_passed"] == truth["success"]   # never a silent failure
    assert truth["success"]


@pytest.mark.slow
@pytest.mark.asyncio
async def test_copying_the_clicks_works_only_where_the_video_was(studio, tmp_path):
    tr = json.loads((ROOT / "runs" / "ui_skill_mail" / "trace.json").read_text())
    same = await replay_ui(tr, f"{studio}{URL}?task=mail&skin=A", tmp_path / "a")
    assert score("mail", same["oracle_state"], prog("mail")["inputs"])["success"]
    other = await replay_ui(tr, f"{studio}{URL}?task=mail&skin=B", tmp_path / "b")
    assert not score("mail", other["oracle_state"], prog("mail")["inputs"])["success"]
