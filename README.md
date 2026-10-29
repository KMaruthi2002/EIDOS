# EIDOS

**Show it once.** EIDOS watches a screen-recorded tutorial and compiles it into a program an AI agent can run. Every step carries a **visual contract** taken from the video, so the agent checks its own work. In a pilot benchmark, a skill learned from one video kept working on new data, on randomly redesigned versions of the app, in a second spreadsheet app, and through mid-task interruptions.

Built by Maruthi Kunchala (Team Parallax) for the Meta Global AI Hackathon 2026.

## The problem

There are billions of hours of screen-recorded how-to videos. Agents can't learn from them. Recent research ([Watch & Learn](https://arxiv.org/abs/2510.04673), [Learning from Online Videos at Inference Time](https://arxiv.org/abs/2511.04137), [GUIDE](https://arxiv.org/abs/2603.26266)) mostly uses tutorial videos as in-context examples, with gains of roughly +2 to +7.5 points on OSWorld; Watch & Learn also fine-tunes on trajectories it extracts from videos. As far as I found, none of them compile a video into a parameterized program whose steps are checked against the video during the run, or test learning in one app and running in another.

## What EIDOS does

```
tutorial video ──► steps + visual contracts ──► intent program ──► run on a new screen, checking each step
     (pixels)        (what was touched,          (inputs, relative     (perceive, ground, act,
                      what changed, what          targets, formulas     check the contract,
                      it must show after)         explained by role)    try another route if it fails)
```

1. **Watch.** Finds the pointer, click markers and drags in the video frames, reads what was typed off the screen, and finds the region each action changed. The sample tutorial is recorded by a script (`eidos/recorder.py`) with a highlighted pointer and click rings, like the click highlighting in common screen recorders; offline, EIDOS finds the pointer by that highlight color.
2. **Understand.** Rewrites each step without pixels: `=SUM(E2:E11)` becomes "sum the Revenue column over all data rows"; a toolbar click becomes "make the row bold" because the text got heavier.
3. **Compile.** Produces a program with inputs (`label`, `label_column`, `sum_column`) and a contract per step. On a sheet with different column names, the user binds the inputs (for example `sum_column=Value`); unbound, EIDOS falls back to the first column for the label and the last for the sum.
4. **Run and check.** On a new screen, EIDOS reads the table, finds where the target column moved, rewrites the formula for that screen (for example `=SUM(A2:A11)` after the columns were shuffled, `=SUM(E1:E10)` in an app that numbers rows differently), and checks every step before moving on. A contract is checked against independent evidence (for example, the header above the cell it wrote), not just against its own choice.

## Meta models

| Model | Job in EIDOS | Offline stand-in in this repo |
|---|---|---|
| SAM 3.1 | Track the pointer and click markers; segment changed regions; find a control on a new screen from a concept ("bold text button") | Color segmentation, frame differencing, template matching |
| Muse Spark | Read each before/after pair and state the step's purpose in screen-independent terms | OCR plus table rules |
| Muse Wonder | Generalize the step trace into a program with inputs and contracts | Rules for the step types in this pilot |
| Muse Image | Draw a card for each learned skill | Not used offline |

**Status of the live models.** EIDOS is designed around these four models, but every result in this repo ran offline with the stand-ins. Today the live path is partial: `eidos/meta.py` has a client for all four, SAM 3.1 concept search is wired into the runner as a route for finding a control, Muse Wonder's program is saved alongside the offline one by `learn`, and `python -m eidos check-live` calls each model once. The endpoint and model IDs in `meta.py` still need confirming against the Meta Model API once a key is available. Set `META_MODEL_API_KEY` (or put it in `.env`) to enable it.

## Pilot benchmark

One tutorial (App A, sales data) is compiled once, then run under conditions the video never showed:

- **new data**: a different dataset and size
- **redesign**: randomly generated redesigns of App A (dark theme, sidebar, resized cells, shuffled columns)
- **other app**: App B, a different spreadsheet library with a different toolbar, layout, and row numbering
- **interruption**: a "What's new" dialog opens at a random moment and blocks input until dismissed

Systems: **replay** (repeat the tutorial's exact clicks and keys), **EIDOS**, and **EIDOS with checks off** (ablation). Success is judged from each app's internal state, which the agent never sees.

| Condition | Runs | Copy the clicks | EIDOS, checks off | EIDOS |
|---|---|---|---|---|
| Same app, same data | 1 | 1/1 | 1/1 | 1/1 |
| New data | 1 | 0/1 | 1/1 | 1/1 |
| Redesigned app | 24 | 0/24 | 23/24 | 23/24 |
| Different app | 2 | 0/2 | 2/2 | 2/2 |
| Interrupted mid-task | 16 | 2/16 | 0/16 | 14/16 |
| **All** | 44 | 3/44 | 27/44 | 41/44 |

EIDOS's own verdict matched the truth on **44/44** runs (0 silent failures). All of its failures were reported by EIDOS itself. Copying the clicks failed silently 41 times. Held-out seed 9001, results in `runs/bench_test/`.

**Protocol.** Seed 7 is the development set, used while fixing bugs. Each held-out round was run once and its results kept unchanged:

- Round 1 (seed 2026, `runs/bench_test_v1/`): EIDOS 25/28 with 1 silent failure. On narrow columns it wrote the label one column off, and its check only read back the cell it had chosen. This led to an independent check (the header above the cell must be the intended column) and a gridline fix.
- Round 2 (seed 4242, `runs/bench_test_v2/`): EIDOS 28/28, but checks-off also 28/28, so nothing yet showed the contracts making a run succeed. This led to the interruption condition and contract-driven repair (a failed contract makes EIDOS dismiss what is in the way and redo the step).
- Final (seed 9001, `runs/bench_test/`): the table above.

**What the ablation shows.** On redesigns and new apps, checks-off does about as well as EIDOS: there, the gains come from the intent program. The contracts matter when something goes wrong mid-run: with a dialog interrupting the task, EIDOS finished 14/16 and checks-off 0/16. Checks-off has no way to notice the failure, so it carries on as if every step worked.

**Scope.** This is a pilot: one task family (add a totals row), one scripted tutorial, two open-source spreadsheet apps ([x-spreadsheet](https://github.com/myliang/x-spreadsheet) and [Jspreadsheet CE](https://github.com/jspreadsheet/ce), both MIT), tutorials with a visible click highlight. The alternative route for bold (Ctrl+B) is built in, not learned from the video. The next step is more task families and real third-party tutorial videos with the live Meta models.

## Add-on: physical skills (simulated robot)

The same idea, off the screen. `physical/` learns a stacking task from a demonstration video and runs it on a simulated robot arm.

- **Learn** (`physical/skill.py: learn`): tracks coloured objects through the video, finds each pick-and-place, and records what it achieved as a physical contract, for example "green is on blue".
- **Run** (`run`): a Franka Panda arm (MuJoCo, model from MuJoCo Menagerie) performs each step. It finds the blocks and checks each contract only through its own cameras: one overhead and two level side views, so a block hidden under another can still be located. After every step it re-checks all earlier contracts, so a stack that gets knocked over is noticed and rebuilt from the lowest broken step.
- **Honest scope:** the arm's motions are scripted (inverse kinematics plus a pick-and-place routine), not learned. EIDOS decides what to do and how to check it. Objects are found by colour offline; in live mode SAM 3.1 would segment them by name. Scoring uses the simulator's true block positions, which the robot never reads.

In the recorded showcase (`python physical/showcase.py`), the table is bumped after the second placement. With checks, EIDOS detects the broken contracts and rebuilds the stack; with checks off, it reports success next to a fallen stack.

Setup: `physical/setup.sh` (MuJoCo plus the Panda model; on headless Linux, OSMesa).

## EIDOS Studio (the app)

```bash
python -m eidos studio        # then open http://localhost:8000
```

A local web app over the same engine:

1. **Learn**: drop a screen recording (or use the sample). The steps, their intents and their visual contracts appear as EIDOS finds them.
2. **Run**: choose where to run the skill: App A or App B, any mix of redesigns (dark theme, sidebar, bigger cells, shuffled columns), the sample or new data, and optionally a dialog that interrupts the task. Choose the agent: EIDOS, EIDOS with checks off, or copying the clicks.
3. **Watch**: the agent's screen streams live while each step is grounded, acted on and checked; repairs show as they happen.
4. **Verdict**: what the agent says next to the truth from the app's internal state (which the agent never sees), so silent failures are visible.

## Run it

```bash
pip install -r requirements.txt && python -m playwright install chromium
# Tesseract OCR is needed for offline mode (apt install tesseract-ocr / brew install tesseract)

python -m eidos serve &                                        # the two test apps on :8765
python -m eidos record                                         # record the sample tutorial
python -m eidos learn videos/tutorial_totals.mp4 runs/skill    # video -> program
python -m eidos run runs/skill "http://localhost:8765/tabula.html"             # run in App B
python -m eidos run runs/skill "http://localhost:8765/gridline.html?theme=dark&side=180&colw=140&rowh=32&order=4,0,1,2,3"

python bench/run_bench.py http://localhost:8765 24 9001 16    # final held-out benchmark
python bench/showcase.py                                       # demo recordings
python web/build_demo.py                                       # demo page -> web/demo/
```

## Layout

```
apps/        the two target apps (self-hosted, MIT) with redesign parameters
eidos/       extract.py (video -> steps + contracts), compiler.py (-> program),
             runner.py (perceive, ground, act, check), vision.py (offline perception),
             meta.py (Meta Model API), score.py (benchmark oracle), studio.py (the app's server)
bench/       benchmark and showcase runners
web/         demo page template and builder; studio/ (the EIDOS Studio front end)
video/       explainer video source (Remotion)
```
