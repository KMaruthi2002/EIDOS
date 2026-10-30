# EIDOS

**Show it once.** EIDOS compiles a video of someone doing a task into a program: steps, the order they really need, values you can change, and a **visual contract** for every step, meaning what must be true on camera once the step is done. The same compiler runs in three worlds:

- **The real world, live.** Learn a hands-on task (cooking, a PC repair, electrical maintenance) from one ordinary video. Then point a camera at someone doing it: EIDOS follows along step by step, says what comes next, checks each finished step against the video, and raises an alert the moment a step is skipped, done out of order, or done wrong.
- **Screens.** An agent runs the learned program on apps the video never showed, and checks its own work.
- **Robots.** A simulated arm runs a learned stacking program and notices when its work is knocked over.

⟦HEADLINE⟧

Built by Maruthi Kunchala (Team Parallax) for the Meta Global AI Hackathon 2026.

## The problem

People film themselves doing things all the time: cooking, fixing, assembling, clicking through software. There are billions of hours of it, but an AI still can't watch one of those videos and come away with a skill it can check. For hands-on work, research systems detect mistakes in procedures after training on many labelled recordings of the same task (for example on [CaptainCook4D](https://arxiv.org/abs/2312.14556) and [HoloAssist](https://arxiv.org/abs/2309.17024)). EIDOS learns a task from one video, with no labels, and turns it into a program a camera can check while the task is being done.

On screens, there are billions of hours of screen-recorded how-to videos, and an agent still can't watch one and come away with a skill it can check. Recent research turns tutorial videos into action trajectories for computer-use agents: as in-context examples and training data ([Watch & Learn](https://arxiv.org/abs/2510.04673)), as one trajectory added to context at each step ([Learning from Online Videos at Inference Time](https://arxiv.org/abs/2511.04137)), or as planning and grounding knowledge ([GUIDE](https://arxiv.org/abs/2603.26266), which reports gains of over 5% on OSWorld). As far as I found, none of them compiles one video into a parameterized program whose steps are checked against what the video showed during the run, or tests learning in one app and running in another. Agents that copy recorded clicks break when the app changes, and have no way to notice.

## The real world, live

```
one video ──► notes, 8 s at a time ──► program ──► calibrated on a ──► live: which step is it?
 (any task)     (Muse Spark)            (Muse Wonder)  second video       did it finish? does it match the video?
                                         + outlines (SAM 3.1)              anything skipped or out of order?
```

1. **Watch.** The video is read in overlapping 8-second windows, one frame per second. For each window Muse Spark says what the person does: the action, the objects and tools, any amount it can read or see, and what is visibly different afterwards (`eidos/world/learn.py`).
2. **Compile.** Muse Wonder turns the notes into a program: steps in plain words, written so they hold for anyone (the mug, not the red mug), amounts as inputs you can change, the steps each step really needs, and a visual contract per step. The frames where each step starts and ends are kept as evidence, and SAM 3.1 outlines what each contract is about in them.
3. **Show it again.** A second correct demonstration calibrates the program (`eidos/world/calibrate.py`). The program is run on it exactly as it would run live: a step the second person never did becomes optional (a habit, not a requirement), a dependency they did not respect is dropped, and a contract that fails on correct work is switched off. Every change is recorded with its reason, and the person who owns the skill can mark any step optional or required with one click.
4. **Live.** Frames arrive from a camera about once a second (`eidos/world/session.py`). Every 3 seconds Muse Spark looks at the last 6 seconds and says which step is happening, or none. Each look is independent, so one wrong look can't derail the next; a step starts when it wins 2 of the last 3 looks. Alerts:
   - **Out of order**: a required step starts before a step it needs. Needs pass through optional steps: if opening a cabinet is optional but needs the power off, removing a part from it still needs the power off.
   - **Check failed**: a required step ended and the result doesn't match its contract, judged against the frame where the demonstration finished the same step. Only a failure seen twice, a few seconds apart, is reported; if the result isn't clearly visible, nothing is.
   - **Skipped**: when the task is finished, a required step was never seen.
   Before an order or skipped alert, EIDOS **looks back** over everything so far for the missing step, the way a person rewinds before accusing someone. The alert is dropped only if the step is clearly found.

Nothing uses frames from the future: each decision at time t uses frames up to t. In the Studio's **Real world** tab, EIDOS watches your camera, or plays a recording as if it were live, and speaks the next step and any alert if you want it to.

### Examples

| Skill (learned from one video) | Source | What happens live |
|---|---|---|
| Replace a part in an electrical control cabinet | HoloAssist R189 | On a recording edited so the disconnect switch is never turned off: "Out of order: step 3 (Remove the old electrical component…) started before step 1 (Turn the disconnect switch to OFF)", raised while the video plays, also through a camera feed |
| Seasoned tomato slices with mozzarella | CaptainCook4D 12_2 | On another cook who never adds the olive oil (labelled in the dataset): "Skipped: Pour oil over the tomato slices" |
| Install RAM in a desktop computer; install a graphics card | HoloAssist R181, R196 | Learned from one technician's head-camera video each; followed live on other technicians |

### Benchmark: live mistake detection on CaptainCook4D

[CaptainCook4D](https://aria-research-lab.github.io/projects/CaptainCook4D) (Peddi et al., NeurIPS 2024) has first-person recordings of people cooking recipes, many with deliberate mistakes labelled step by step: missing steps, wrong order, wrong amounts, wrong technique, wrong timing or temperature. For each recipe, EIDOS learns from the first recording without mistakes and calibrates on the second; no labels are used to learn. Every other recording of that recipe, by other people in other kitchens, is run through the live runner as if it were a camera feed. The question is the dataset's error-recognition question: did this recording contain a mistake? The labels are used only to score.

The comparison is **Muse Spark asked directly**: it gets the same compiled step list and 24 frames spread over the whole recording (so it sees the end, which a live system can't) and is asked whether the person made any mistake.

⟦BENCH⟧

**What the numbers mean.** On the development recipes, most of EIDOS's false alarms on correct recordings were real deviations from the demonstration that the recipe doesn't require: the demonstrator rinsed the mug first and other people didn't, so the dataset doesn't call it a mistake. EIDOS is faithful to what it was shown; marking that step optional removes the alert. The visual checks rarely fire (6 of 199 checks on the development recipes), and when they do they mostly name mistakes nothing else can see, such as "Tomato is chopped into small irregular pieces, not 6 slices".

**Protocol.** Two recipes were used for development (`runs/world/dev/`, earlier versions kept in `runs/world/archive/`). The eight test recipes were chosen by a rule before any test run (the next eight shortest by average recording length) and run once with the frozen code (`runs/world/test/`). Looks are cached in `runs/world/looks/`, so scores can be recomputed without a key.

**Scope.** Recordings are first-person, 360p, sampled at one frame per second; the step tracker can miss short steps, and amounts and temperatures are hard to see at this size. Learning from one video can't tell a habit from a requirement; calibration on a second video and the one-click override handle that. A real deployment would also want a check on what's being held (a wrong ingredient), which the contracts only partly cover.

## Screens: how it works

```
tutorial video ──► steps + visual contracts ──► program with inputs ──► run on a new screen, checking each step
     (pixels)        (what was touched, what      (targets by label,       (perceive, ground, act, check;
                      changed, what it must        typed values become      on a failed check: clear what is
                      show afterwards)             inputs)                  in the way and redo the step)
```

1. **Watch.** Finds the pointer, click markers and drags in the video frames, reads the screen with OCR, and finds what each action changed. The tutorials are recorded by scripts (`eidos/recorder.py`, `eidos/ui/recorder.py`) with a highlighted pointer and click rings, like the click highlighting in common screen recorders; offline, EIDOS finds the pointer by that highlight color.
2. **Understand.** Decides what kind of step each click was from what was touched and what changed, and names its target by the text on screen, never by position.
3. **Compile.** Produces a program: every value the person typed or picked becomes an input named after its field, and every step gets a contract.
4. **Run and check.** On a new screen, EIDOS finds each target again from a fresh screenshot, acts, and checks the step's contract before moving on. If a check fails, it presses Escape (which closes the benchmark's interrupting dialog), looks again and redoes the step, up to twice; if it still fails, it stops and reports the failure.

### Everyday apps

Four step types cover the four everyday task families here:

| Step | Learned from the video as | Contract checked on the new screen |
|---|---|---|
| press | a click on a button or menu item, named by its text | text that newly appeared after the click: for a submit, every entered value must show up outside the form; for other presses, at least two of the (up to three) new phrases seen in the video. Text already on screen before the click doesn't count |
| type | a click into a box, then typing, named by the box's label | the box shows the value, re-read after typing, and the label next to the box is the intended one |
| choose | a click on a box, then on an entry of the list that opened | the box shows the chosen value, and its label is the intended one |
| switch | a click on an on/off switch, named by its row | the switch on that row is on (filled with color) or off (grey); EIDOS clicks only if it isn't already in the wanted state |

For example, from a 19-second tutorial of someone sending an email, EIDOS learns: press "Compose"; type {to} into "To"; type {subject} into "Subject"; type {message} into "Message"; press "Send", after which both {to} and {subject} must newly appear on screen outside the form. The tutorial's values become the defaults for `to`, `subject` and `message`.

Targets are named by their label; position is used only to break ties (for example, a list's entries are looked for below its box). The label is verified when a box is chosen, and re-read after typing. This is what stopped an early bug where "Message" matched the heading "New message" and EIDOS typed into the wrong box; the first version's check only read back the box it had chosen, so it passed.

### Spreadsheets

The first task family: add a bold totals row. `=SUM(E2:E11)` becomes "sum the Revenue column over all data rows"; a toolbar click becomes "make the row bold" because the text got heavier. On a new screen EIDOS reads the table, finds where the column moved, rewrites the formula for that screen (`=SUM(A2:A11)` after the columns were shuffled, `=SUM(E1:E10)` in an app that numbers rows differently), and checks the header above the cell it wrote.

## Meta models

On screens EIDOS runs fully offline and uses Meta's models where they add something pixels and OCR can't; every answer is a proposal checked against the screen. In the real world, Meta's models are how EIDOS sees.

| Model | What it does in EIDOS | Where |
|---|---|---|
| Muse Spark (`muse-spark-1.3`), real world | Watches the demonstration 8 seconds at a time; live, says which step is happening every 3 seconds (minimal reasoning, median about 3 s a look); checks each finished step against the demonstration's frame; searches back before an alert | `eidos/world/learn.py`, `eidos/world/run.py` |
| Muse Wonder (`muse-wonder-1.0`), real world | Compiles the window notes into the program: steps, inputs, dependencies, contracts (Muse Spark is the fallback) | `eidos/world/learn.py` `compile_program` |
| SAM 3.1 (`sam-3.1`), real world | Outlines what each contract is about in the demonstration's evidence frame (the dashed outline in the Studio) | `eidos/world/learn.py` `outline` |
| Muse Spark Open, real world | Can be chosen to watch live instead of Muse Spark (about 10 s a look on Baseten, so alerts come later) | Studio, `reader: open` |
| Muse Spark (`muse-spark-1.3`) | When a learned label isn't on the new screen, EIDOS gives Muse Spark the screenshot and the text it read there, and asks which item plays the same role ("the button labelled Send in the tutorial"). The answer must be one of those items, so EIDOS can find it from pixels and check it like any other label. It also maps a press's expected phrases ("Settings saved") to the new wording ("Changes applied") before the contract is checked | `eidos/live.py` `match_label`, `eidos/ui/run.py` |
| SAM 3.1 (`sam-3.1`) | A second opinion on every field, button and switch EIDOS finds ("input box", "Deliver button", "toggle switch"). Advisory: logged, never overrides the pixel check | `eidos/ui/run.py` `sam_check`; spreadsheet runner fallback |
| Muse Image (`muse-image-1.0`) | Draws each learned skill's card in the Studio (`runs/*/card.webp`, which keep Meta's AI label) | `eidos/studio.py` |
| Muse Wonder (`muse-wonder-1.0`) | Compiles a step trace into a program with inputs and contracts; saved next to the offline program by the spreadsheet `learn` command and tried by `check-live`, not used for running | `eidos/live.py` `wonder_compile` |
| Muse Spark Open (`meta-models/muse-spark-open-1026`, on Baseten) | The same screen reader as Muse Spark, through an OpenAI-compatible endpoint (`EIDOS_READER=open`) | `eidos/live.py` `baseten_chat` |

Keys go in `.env` (`MODEL_API_KEY`, `BASETEN_API_KEY`), which is not committed. `python -m eidos check-live` makes one real call to each model. A live system enters a benchmark only if a test call with its key succeeds.

On the design C held-out runs, Muse Spark was asked a median of 11 times per run, at a median of 2.3 seconds per call. SAM 3.1's box agreed with EIDOS's own (overlap of at least half) on 109 of 151 checks (72%); in most disagreements SAM's top box didn't overlap EIDOS's at all, often because a phrase like "input box" fits every field on the form. Each of those runs still succeeded, which is why SAM stays advisory.

## Screens: benchmarks

Each skill is learned once, from one tutorial video in App A, then run under conditions the video never showed. Three systems run the same conditions: **copying the clicks** (replay the tutorial's exact pointer positions and keystrokes), **EIDOS with checks off** (the same skill and perception, acting once per step without checking), and **EIDOS**. Success is judged from each app's internal state, which no system sees.

### Everyday tasks (held-out round 2, seed 50505, run once)

Four tasks (mail, calendar, expense, settings). Each app has two designs built for the benchmark: design A, where the tutorial was recorded, and design B, a second design of the same app with the same field labels and button texts but a different layout (top menu, modal form, labels above fields, pill buttons, serif type). Every run except "same" uses new values for the inputs.

Four systems: **copy the clicks** (the tutorial's pointer positions and keystrokes, typing the tutorial's values), **copy the clicks, new values** (same clicks, typing this run's values, which separates layout from data), **EIDOS with checks off** (the same skill and perception, acting once per step without checking; it still reports a step it couldn't ground), and **EIDOS**. Copying the clicks has no verdict of its own.

| Condition | Runs | Copy the clicks | Copy the clicks, new values | EIDOS, checks off | EIDOS |
|---|---|---|---|---|---|
| Same app, same values | 4 | 4/4 | 4/4 | 4/4 | 4/4 |
| New values | 4 | 0/4 | 2/4 | 4/4 | 4/4 |
| Redesigned app (dark theme, menu moved, labels above or beside fields, fields shuffled, buttons moved, larger text) | 24 | 0/24 | 0/24 | 24/24 | 24/24 |
| Design B with random variations | 12 | 0/12 | 0/12 | 12/12 | 12/12 |
| Interrupted by a dialog at a random moment | 16 | 0/16 | 1/16 | 0/16 | 16/16 |
| **All** | 60 | 4/60 | 7/60 | 44/60 | 60/60 |

EIDOS's own verdict matched the truth on **60/60** runs (0 silent failures); it repaired a step in 16 of them. Checks off claimed success on 5 runs that had failed, all of them interrupted. Results in `runs/bench_everyday_test2/`.

**Protocol.** Seed 7 is the development set, used while fixing bugs (`runs/bench_everyday_dev/`). Each held-out seed is run once and its results are kept unchanged:

- Round 1 (seed 31337, `runs/bench_everyday_test/`, three systems): EIDOS 58/60, checks off 42/60, copy the clicks 4/60, 0 silent failures. Both EIDOS failures were calendar runs on design B where OCR misread entries of the open Time list, so EIDOS stopped and reported it. An independent review of the code and claims then found that some press checks were too lenient (half of the expected text was enough, and text already on screen could count), that copying the clicks was compared only with the tutorial's values, and that larger text sizes made the calendar app clip "9:00 AM". The fixes: press checks count only text that newly appeared and require every entered value; the list is read row by row; a second copy-the-clicks baseline types the new values; checks off reads a switch's state the same way EIDOS does; the app's list columns no longer clip.
- Round 2 (seed 50505): the table above, with the fixed code.
- The first development run had 4 silent failures: on design B, "Message" matched the heading "New message", EIDOS typed into the wrong box, and the check only read back the box it had chosen. That led to label verification when a box is chosen and after typing, and to submit checks that ignore text inside form fields.

### Renamed controls (design C, held-out seed 60606, run once)

Design C keeps the apps' layout but renames every control and message: "Compose" becomes "New email", "To" becomes "Recipient", "Send" becomes "Deliver", "Save changes" becomes "Apply", "Settings saved" becomes "Changes applied", and so on (`apps/everyday/index.html`, `words=alt`). Half of the 32 runs also get a random redesign, and all use new values. Nothing learned by label can be found as written, so this tests reading for meaning.

| Task | Runs | Copy the clicks | Copy the clicks, new values | EIDOS, checks off | EIDOS (offline) | EIDOS + Muse Spark | EIDOS + Muse Spark Open |
|---|---|---|---|---|---|---|---|
| Mail | 8 | 0/8 | 3/8 | 0/8 | 0/8 | 8/8 | 8/8 |
| Calendar | 8 | 0/8 | 0/8 | 0/8 | 0/8 | 8/8 | 8/8 |
| Expense | 8 | 0/8 | 1/8 | 0/8 | 0/8 | 8/8 | 8/8 |
| Settings | 8 | 0/8 | 3/8 | 0/8 | 0/8 | 8/8 | 8/8 |
| **All** | 32 | 0/32 | 7/32 | 0/32 | 0/32 | **32/32** | **32/32** |

Every system's verdict matched the truth on 32/32 (offline EIDOS and checks off stop at the first label they can't find and say so). Muse Spark's picks included To → Recipient, Message → Body, Date → Day, Time → Starts at, Two-factor sign-in → Two-step verification and Send → Deliver; each pick was then grounded and checked from pixels. Results in `runs/bench_everyday_words/`; development seed 8 in `runs/bench_everyday_words_dev/` (30/32, then two settings fixes: offer joined two-line labels and single button words as candidates).

Muse Spark Open, Meta's open-weights model served on Baseten, ran the same 32 held-out conditions afterwards, once, with no code changes between its development run and this one: **32/32**, verdict matched the truth on 32/32 (`runs/bench_everyday_words_open/`). On the development seed it also finished 32/32, but on one settings run it reported a failure for a save that had worked (it didn't map "Settings saved" to "Changes applied"), a cautious error rather than a silent one. Its calls were slower (median 5.8 s against 2.3 s for Muse Spark; median run 103 s against 53 s).

### Spreadsheets (held-out seed 9001, run once)

| Condition | Runs | Copy the clicks | EIDOS, checks off | EIDOS |
|---|---|---|---|---|
| Same app, same data | 1 | 1/1 | 1/1 | 1/1 |
| New data | 1 | 0/1 | 1/1 | 1/1 |
| Redesigned app | 24 | 0/24 | 23/24 | 23/24 |
| Different app | 2 | 0/2 | 2/2 | 2/2 |
| Interrupted mid-task | 16 | 2/16 | 0/16 | 14/16 |
| **All** | 44 | 3/44 | 27/44 | 41/44 |

EIDOS's own verdict matched the truth on **44/44** runs. Results in `runs/bench_test/`. This is the third held-out spreadsheet round; the fixes made after the first two were informed by them (each run once): seed 2026, EIDOS 25/28 with 1 silent failure (it wrote the label one column off and its check only read back its own cell), which led to the header check; seed 4242, EIDOS 28/28 but checks off also 28/28, which led to the interruption condition and contract-driven repair.

### What the ablation shows

On redesigns and the second design or app, checks off does about as well as EIDOS: there the gains come from the skill itself (targets by label, values as inputs). The checks matter when something goes wrong mid-run: with a dialog interrupting the task, EIDOS finished **30/32** across both held-out benchmarks (16/16 everyday, 14/16 spreadsheet) and checks off **0/32**. In the everyday runs, checks off still claimed success on 5 of the 16 interrupted runs; on the others it failed to find a later target and reported that. The spreadsheet benchmark doesn't record a verdict for checks off. The ablation also removes the repair routes: in spreadsheets, checks off doesn't try Ctrl+B when the bold button isn't found.

### Scope

This is a pilot. The target apps are built for the benchmark (the everyday apps in `apps/everyday/`) or open-source ([x-spreadsheet](https://github.com/myliang/x-spreadsheet) and [Jspreadsheet CE](https://github.com/jspreadsheet/ce), both MIT). The tutorials are scripted recordings with a visible click highlight. Five task families, no scrolling, and repair is "press Escape and redo the step" (the benchmark's dialog closes on Escape; other kinds of interruption would need other routes). The alternative route for bold in spreadsheets (Ctrl+B) is built in, not learned. Design C renames controls but keeps their meaning one-to-one; a real redesign can also merge or split steps. The next step is real third-party tutorial videos and real apps.

## Robots: physical skills in simulation

The same idea, off the screen. `physical/` learns a stacking task from a demonstration video and runs it on a simulated robot arm.

- **Learn** (`physical/skill.py: learn`): tracks coloured objects through the video, finds each pick-and-place, and records what it achieved as a physical contract, for example "green is on blue".
- **Run** (`run`): a Franka Panda arm (MuJoCo, model from MuJoCo Menagerie) performs each step. It finds the blocks and checks each contract only through its own cameras: one overhead and two level side views, so a block hidden under another can still be located. After every step it re-checks all earlier contracts, so a stack that gets knocked over is noticed and rebuilt from the lowest broken step.
- **Honest scope:** the arm's motions are scripted (inverse kinematics plus a pick-and-place routine), not learned. EIDOS decides what to do and how to check it. Objects are found by colour offline; in live mode SAM 3.1 would segment them by name. Scoring uses the simulator's true block positions, which the robot never reads.

In the recorded showcase (`python physical/showcase.py`, one run of each), a simulated knock after the second placement moves the green block off the stack (the simulator moves it directly). With checks, EIDOS sees the broken contracts through its cameras and rebuilds the stack; with checks off, nothing re-checks the stack, so the run ends reporting done next to a broken stack. The demonstration video it learns from is `physical/demo/sim_demo.mp4`, rendered by the simulator.

Setup: `physical/setup.sh` (MuJoCo plus the Panda model; on headless Linux, OSMesa).

## EIDOS Studio (the app)

```bash
python -m eidos studio        # then open http://localhost:8000
```

A local web app over the same engine, with two tabs: **Screens** and **Real world**.

**Real world** (`/world`, needs a Meta Model API key):

- **Learn from a video**: drop any video of a hands-on task. The notes appear as EIDOS watches, then the program, with the evidence frames and SAM outlines.
- **Follow along live**: choose your camera (on a phone or laptop, point it at your hands and the work), a practice recording, or any video file played in real time. The current step, what EIDOS sees, the next step, checks and alerts update as it happens; it can speak the next step and alerts.
- Three sample skills ship with practice recordings: tomato salad (CaptainCook4D), installing RAM and replacing a part in an electrical cabinet (HoloAssist), including a recording edited so the power is never switched off.
- Mark any step optional or required with one click before starting.

**Screens**: the four everyday apps are served by the Studio itself.

1. **Show it a task**, three ways:
   - **Teach it live.** Pick an app (Mail, Calendar, Expenses, Settings) and do the task once inside the Studio. Your pointer and keys go to a real browser running the app, which is recorded the way screen recorders record tutorials (highlighted pointer, click rings). When you press "Finish and learn", EIDOS learns from that video file alone, the same as from any other recording.
   - **Pick a sample tutorial** (email, calendar event, expense, two-factor sign-in, spreadsheet totals).
   - **Drop a screen recording** and say which app it shows.
2. **Watch it learn**: the recording plays with each step outlined as EIDOS finds it, with its inputs and contracts.
3. **Run it anywhere**: design A, B or C (renamed controls), any mix of redesigns, the video's values, new values or **your own values**, and optionally a dialog that interrupts the task. Choose the agent: EIDOS, EIDOS + Muse Spark (with a key), EIDOS with checks off, or copying the clicks. The agent's screen streams live while each step is grounded, acted on and checked; repairs and model matches show as they happen.
4. **Verdict**: what the agent says next to the truth from the app's internal state (which the agent never sees), so silent failures are visible. For a skill you taught, success means the app saved a record with every value the run entered.

Skills you teach are kept in `studio_data/` and listed on the first screen, where each can be downloaded as JSON or deleted.

## Run it

```bash
pip install -r requirements.txt && python -m playwright install chromium
# Tesseract OCR and ffmpeg are needed (apt install tesseract-ocr ffmpeg / brew install tesseract ffmpeg)
# Optional: put MODEL_API_KEY (Meta Model API) and BASETEN_API_KEY in a .env file to enable the live models

python -m eidos studio                                             # the app: open http://localhost:8000 (Real world tab: /world)

# Real world (needs MODEL_API_KEY; videos and annotations download to ../data, outside the repo)
git clone https://github.com/CaptainCook4D/annotations ../data/cc_ann
python bench/world_bench.py prep  --split dev                      # download recordings, keep one frame per second
python bench/world_bench.py learn --split dev                      # learn each recipe from one video, calibrate on a second
python bench/world_bench.py run   --split dev                      # every other recording, as if live
python bench/world_bench.py baseline --split dev                   # Muse Spark asked directly
python bench/world_bench.py score --split dev                      # (the same for --split test)
python tools/make_world_samples.py                                 # rebuild the Studio's sample skills

# Everyday tasks (the Studio also serves the everyday apps)
python -m eidos studio &
python -m eidos record-ui                                          # record the four tutorials
python -m eidos learn-ui videos/tutorial_mail.mp4 runs/ui_skill_mail
python -m eidos run-ui runs/ui_skill_mail mail "skin=B&theme=dark&order=2,0,1&popup=4" --new-data
python bench/run_everyday.py http://localhost:8000 dev             # development set (seed 7)
# held-out seeds are run once; their recorded results are protected (pass --force to overwrite)
python bench/run_everyday.py http://localhost:8000 test2           # held-out round 2 (seed 50505)
python bench/run_everyday.py http://localhost:8000 words           # design C, renamed controls (seed 60606; live systems need a key)
python bench/run_everyday.py http://localhost:8000 words_open      # the same conditions with Muse Spark Open only
python -m eidos check-live                                         # one real call to each Meta model

# Spreadsheets
python -m eidos serve &                                            # the two spreadsheet apps on :8765
python -m eidos record
python -m eidos learn videos/tutorial_totals.mp4 runs/skill
python -m eidos run runs/skill "http://localhost:8765/gridline.html?theme=dark&side=180&colw=140&rowh=32&order=4,0,1,2,3"
python bench/run_bench.py http://localhost:8765 24 9001 16        # held-out spreadsheet benchmark

python bench/showcase.py                                           # demo recordings
python web/build_demo.py                                           # demo page -> web/demo/
```

## Tests

```bash
python -m pytest -q -m "not slow"     # perception, learning, Studio API, Meta client (minutes)
python -m pytest -q                   # plus end-to-end runs and a click-through of the Studio
```

- `tests/test_perception.py`: every field is found by its label on four designs of each form, and switch states are read correctly.
- `tests/test_learn.py`: each tutorial video is learned into exactly the steps and values the recorder performed.
- `tests/test_run.py`: EIDOS on a hard redesign of each task, an interrupted run with an honest verdict, and copying the clicks working only where the video was recorded.
- `tests/test_studio.py`: the Studio's API, and a browser click-through from choosing a sample to the verdict.
- `tests/test_teach.py`: teaching live end to end (a scripted person records Mail through the teach API, EIDOS learns it, and the skill runs on design B with new values), plus the teach API's guards and the success rule for taught skills.
- `tests/test_world.py`: the live runner offline, with scripted looks: steps start only on agreement, order alerts pass through optional steps, optional steps never alert, skipped steps are reported, calibration drops a dependency a correct demonstration didn't follow, searching back dismisses only a step it clearly finds, and a live session feeds out-of-order answers to the tracker in time order.
- `tests/test_meta_client.py`: the Meta Model API client against a fake server (a test double); it checks the request shape and the parsing of replies, not model quality.

## Layout

```
apps/        spreadsheet apps (self-hosted, MIT) and everyday/ (mail, calendar, expense,
             settings; designs A, B and C), all with redesign parameters
eidos/       world/ (the real world: learn.py video -> program, calibrate.py, run.py looks,
             tracker, checks and searching back, session.py live sessions, server.py Studio API)
             ui/ (everyday tasks: see.py perception, learn.py video -> program,
             run.py perceive/ground/act/check, tasks.py scoring and inputs)
             extract.py (video -> steps + contracts), compiler.py (-> program),
             runner.py (perceive, ground, act, check), vision.py (offline perception),
             live.py (Meta Model API and Muse Spark Open on Baseten), meta.py (spreadsheet
             client), score.py (benchmark oracle), studio.py (the app's server),
             teach.py (teaching live: the recorded browser behind "Teach it live")
bench/       benchmark and showcase runners (world_bench.py, run_everyday.py, run_bench.py)
samples/     world/: the Studio's sample real-world skills with practice recordings
tools/       make_world_samples.py
web/         demo page template and builder; studio/ and world/ (the EIDOS Studio front end)
video/       explainer video source (Remotion)
```

## Credits

Real-world recordings: [CaptainCook4D](https://github.com/CaptainCook4D/annotations) (Apache License 2.0; annotations MIT) and [HoloAssist](https://holoassist.github.io/) (CDLA-Permissive-2.0). Spreadsheet apps: x-spreadsheet and Jspreadsheet CE (MIT). Robot model: MuJoCo Menagerie.
