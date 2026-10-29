"""Trace -> EIDOS program.

A program is a list of intent-level steps with typed targets, inputs, and
visual contracts. It never stores pixel coordinates or cell addresses as
truth; those are resolved against whatever screen the program runs on.

Live mode: Muse Wonder reads the trace and writes the program (and can find
loops, conditions and inputs that rules would miss). Offline mode: the rules
below cover the step types the offline extractor produces.
"""
from __future__ import annotations

import json
from pathlib import Path

ROW_WORDS = {
    "first_empty_after_data": "the first empty row below the data",
}


def row_phrase(ref: str) -> str:
    return ROW_WORDS.get(ref, ref.replace("_", " "))


def compile_trace(trace: dict, name: str = "Add a totals row") -> dict:
    steps, inputs = [], {}
    anchor_row = None
    for s in trace["steps"]:
        c = s["contract"]
        if s["action"] == "enter_text" and "formula" in s:
            f = s["formula"]
            inputs.setdefault("sum_column", f["column"])
            step = {
                "do": "enter_formula",
                "intent": f"{f['fn'].title()} the {{sum_column}} column over all data rows, in the same row",
                "target": {"row": "same_as:" + str(anchor_row) if anchor_row else s["target"]["row"],
                           "column": "{sum_column}"},
                "formula": {"fn": f["fn"], "column": "{sum_column}", "rows": f["rows"]},
                "learned_from": f["as_typed"],
                "contract": {"cell_shows_number": {"fn": f["fn"], "column": "{sum_column}", "rows": f["rows"]}},
            }
        elif s["action"] == "enter_text":
            inputs.setdefault("label", s["text"])
            label_col = s["target"]["column"]
            inputs.setdefault("label_column", label_col)
            step = {
                "do": "enter_text",
                "intent": "Write {label} in the {label_column} column of " + row_phrase(s["target"]["row"]),
                "target": {"row": s["target"]["row"], "column": "{label_column}"},
                "text": "{label}",
                "learned_from": s["text"],
                "contract": {"cell_shows_text": "{label}"},
            }
            anchor_row = len(steps) + 1
        elif s["action"] == "select_range":
            step = {
                "do": "select_row",
                "intent": "Select that row across the whole table",
                "target": {"row": "same_as:" + str(anchor_row) if anchor_row else s["target"]["row"],
                           "from": "first_column", "to": "last_column"},
                "contract": {"selection_covers_row": True},
            }
        elif s["action"] == "press_control":
            effect = s["target"].get("effect")
            step = {
                "do": "apply_format" if effect == "text_heavier" else "press_control",
                "intent": "Make the selected row bold" if effect == "text_heavier" else s["intent"],
                "format": "bold" if effect == "text_heavier" else None,
                "ground": {
                    "look": s["target"].get("control_look"),          # template from the tutorial
                    "concept": "bold text formatting button",        # SAM 3.1 text prompt (live)
                    "alternatives": ["shortcut:Control+b"],          # other ways to reach the same intent
                },
                "contract": {"selection_text_heavier": True},
            }
        else:
            continue
        step["id"] = len(steps) + 1
        step["video_time"] = [round(s["t_start"], 2), round(s["t_end"], 2)]
        step["evidence"] = {"pre": s["crops"].get("pre"), "post": s["crops"].get("post"),
                            "changed_box": c.get("changed_box")}
        steps.append(step)
    return {
        "eidos": "0.1",
        "name": name,
        "learned_from": trace["video"],
        "source_screen": trace["screen"],
        "inputs": inputs,
        "steps": steps,
    }


def bind(text, inputs: dict):
    if isinstance(text, str):
        for k, v in inputs.items():
            text = text.replace("{" + k + "}", str(v))
    return text


if __name__ == "__main__":
    import sys
    trace = json.loads(Path(sys.argv[1]).read_text())
    prog = compile_trace(trace)
    out = Path(sys.argv[1]).with_name("program.json")
    out.write_text(json.dumps(prog, indent=2))
    print(out)
