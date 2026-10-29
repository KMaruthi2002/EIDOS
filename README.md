# EIDOS

**Show it once.** EIDOS watches a screen-recorded tutorial and compiles it into a program an AI agent can run. Every step carries a **visual contract** taken from the video, so the agent checks its own work, and the skill keeps working when the data, the design, or the whole app changes.

Built by Maruthi Kunchala (Team Parallax) for the Meta Global AI Hackathon 2026.

## The problem

There are billions of hours of screen-recorded how-to videos. Agents can't learn from them. Recent research ([Watch & Learn](https://arxiv.org/abs/2510.04673), [Learning from Online Videos at Inference Time](https://arxiv.org/abs/2511.04137), [GUIDE](https://arxiv.org/abs/2603.26266)) uses tutorial videos as *hints* in an agent's context, with gains of roughly +2 to +7 points on OSWorld. None of them turn a video into a reusable program, check the agent's run against the video, or test learning in one app and running in another.

## What EIDOS does

```
tutorial video ──► steps + visual contracts ──► intent program ──► run on any screen, checking each step
     (pixels)        (what was touched,          (inputs, relative     (perceive, ground, act,
                      what changed, what          targets, formulas     check the contract,
                      it must show after)         explained by role)    try another route if it fails)
```

1. **Watch.** Finds the pointer, click markers, drags and typed text in the video, and the region each action changed.
2. **Understand.** Rewrites each step without pixels: `=SUM(E2:E11)` becomes "sum the Revenue column over all data rows"; a toolbar click becomes "make the row bold" because the text got heavier.
3. **Compile.** Produces a program with inputs (`label`, `label_column`, `sum_column`) and a contract per step.
4. **Run and check.** On a new screen, EIDOS reads the table, finds where the target column moved, rewrites the formula for that screen (for example `=SUM(A2:A11)` after the columns were shuffled, `=SUM(E1:E10)` in an app that numbers rows differently), and checks every step before moving on. A contract is checked against independent evidence (for example, the header above the cell it wrote), not just against its own choice.

## Meta models

| Model | Job in EIDOS | Offline stand-in in this repo |
|---|---|---|
| SAM 3.1 | Track the pointer and click markers; segment changed regions; find a control on a new screen from a concept ("bold text button") | Color segmentation, frame differencing, template matching |
| Muse Spark | Read each before/after pair and state the step's purpose in screen-independent terms | OCR plus table rules |
| Muse Wonder | Generalize the step trace into a program with inputs and contracts | Rules for the step types in this pilot |
| Muse Image | Draw a card for each learned skill | Not used offline |

Set `META_MODEL_API_KEY` to switch on the live models (`eidos/meta.py`). Without it, everything runs offline, which is how every result below was produced, so they can be reproduced without a key.

## Pilot benchmark

One tutorial (App A, sales data) is compiled once, then run under conditions the video never showed:

- **new data**: a different dataset and size
- **redesign**: randomly generated redesigns of App A (dark theme, sidebar, resized cells, shuffled columns)
- **other app**: App B, a different spreadsheet library with a different toolbar, layout, and row numbering

Systems: **replay** (repeat the tutorial's exact clicks and keys), **EIDOS**, and **EIDOS with checks off** (ablation). Success is judged from each app's internal state, which the agent never sees.

RESULTS_TABLE

**Protocol.** Seed 7 is the development set, used while fixing bugs. Held-out round 1 (seed 2026) found a silent failure: on narrow columns EIDOS wrote the label one column off, and its check only read back the cell it had chosen. That led to an independent header check and a gridline fix. Round 1 results are kept unchanged in `runs/bench_test_v1/`. The headline numbers come from a fresh seed (4242) run once after those fixes.

**What the ablation shows.** Turning the checks off barely changes the success rate here. The contracts' main effect in this pilot is that the agent *knows* when it failed: without them, a failed run looks exactly like a good one.

**Scope.** This is a pilot: one task family (add a totals row), two open-source spreadsheet apps ([x-spreadsheet](https://github.com/myliang/x-spreadsheet) and [Jspreadsheet CE](https://github.com/jspreadsheet/ce), both MIT), recorded tutorials with a visible click highlight. The next step is more task families and real third-party tutorial videos with the live Meta models.

## Run it

```bash
pip install -r requirements.txt && python -m playwright install chromium
# Tesseract OCR is needed for offline mode (apt install tesseract-ocr / brew install tesseract)

python -m eidos serve &                                        # the two test apps on :8765
python -m eidos record                                         # record the sample tutorial
python -m eidos learn videos/tutorial_totals.mp4 runs/skill    # video -> program
python -m eidos run runs/skill "http://localhost:8765/tabula.html"             # run in App B
python -m eidos run runs/skill "http://localhost:8765/gridline.html?theme=dark&side=180&colw=140&rowh=32&order=4,0,1,2,3"

python bench/run_bench.py http://localhost:8765 24 4242       # held-out benchmark
python bench/showcase.py                                       # demo recordings
python web/build_demo.py                                       # demo page -> web/demo/
```

## Layout

```
apps/        the two target apps (self-hosted, MIT) with redesign parameters
eidos/       extract.py (video -> steps + contracts), compiler.py (-> program),
             runner.py (perceive, ground, act, check), vision.py (offline perception),
             meta.py (Meta Model API), score.py (benchmark oracle)
bench/       benchmark and showcase runners
web/         demo page template and builder
video/       explainer video source (Remotion)
```
