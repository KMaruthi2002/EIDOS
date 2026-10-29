"""The everyday task families: what the tutorial shows, how to score a run,
and how to draw fresh inputs for each benchmark run.

Scoring reads the app's internal state (window.__eidosState), which the agent
never sees.
"""
from __future__ import annotations

import random

URL = "/apps/everyday/index.html"

# What the person does in each tutorial video (App A, default design).
# ("click", text) clicks the visible control with that text; ("type", label, value)
# clicks the field with that label and types; ("choose", label, value) opens the
# dropdown and picks; ("toggle", label) flips the switch on that row.
TUTORIALS = {
    "mail": [("click", "Compose"), ("type", "To", "maya@northwind.com"), ("type", "Subject", "Q3 report"),
             ("type", "Message", "Attached is the Q3 report."), ("click", "Send")],
    "calendar": [("click", "New event"), ("type", "Title", "Team lunch"), ("type", "Date", "Nov 12"),
                 ("choose", "Time", "1:00 PM"), ("type", "Location", "Cafe Lumen"), ("click", "Save")],
    "expense": [("click", "New expense"), ("type", "Merchant", "Delta Air Lines"), ("type", "Amount", "412.50"),
                ("choose", "Category", "Travel"), ("click", "Submit")],
    "settings": [("click", "Security"), ("toggle", "Two-factor sign-in"),
                 ("type", "Recovery email", "ruth.backup@example.com"), ("click", "Save changes")],
}
TITLES = {"mail": "Send an email", "calendar": "Add a calendar event", "expense": "Submit an expense",
          "settings": "Turn on two-factor sign-in"}
N_FIELDS = {"mail": 3, "calendar": 4, "expense": 3, "settings": 3}   # for the order= redesign

FIRST = ["ana", "li.wei", "omar", "julia", "kenji", "sofia", "dev", "nadia"]
DOMAINS = ["acme.io", "harbor.co", "fieldnote.org", "brightlane.com"]


def fresh_inputs(task: str, rng: random.Random) -> dict:
    """New data for one run: the skill must use these, not the tutorial's values."""
    if task == "mail":
        return {"to": f"{rng.choice(FIRST)}@{rng.choice(DOMAINS)}",
                "subject": rng.choice(["Budget review", "Offsite plan", "Signed contract", "Travel receipts", "Hiring update"]),
                "message": rng.choice(["See you at ten.", "Notes are attached.", "Please review by Friday.", "Thanks for the help."])}
    if task == "calendar":
        return {"title": rng.choice(["Dentist", "Project kickoff", "Coffee with Sam", "Yoga class", "Parent meeting"]),
                "date": f"{rng.choice(['Nov', 'Dec'])} {rng.randint(2, 28)}",
                "time": rng.choice(["8:30 AM", "9:00 AM", "10:00 AM", "11:30 AM", "2:30 PM", "4:00 PM"]),
                "location": rng.choice(["Room 4B", "Main St Clinic", "Zoom", "Studio 9", "Library"])}
    if task == "expense":
        return {"merchant": rng.choice(["Uber", "Staples", "Hilton", "Figma", "Amtrak", "Blue Bottle"]),
                "amount": f"{rng.randint(5, 900)}.{rng.randint(0, 99):02d}",
                "category": rng.choice(["Travel", "Meals", "Office supplies", "Software", "Training"])}
    if task == "settings":
        return {"recovery_email": f"{rng.choice(FIRST)}.backup@{rng.choice(DOMAINS)}"}
    raise KeyError(task)


def _norm(s):
    return " ".join(str(s).split()).strip().lower()


def score(task: str, state: dict | None, inputs: dict) -> dict:
    if not state:
        return {"success": False, "why": "no state"}
    if task == "settings":
        s = state["settings"]
        ok = s["Two-factor sign-in"] is True and _norm(s["Recovery email"]) == _norm(inputs["recovery_email"]) \
            and s["Sign-in alerts"] is False and s["Remember this device"] is True and state["saves"] >= 1
        return {"success": ok, "why": "" if ok else f"saved settings: {s}, saves={state['saves']}"}
    recs = state["records"]
    want = {k: _norm(v) for k, v in inputs.items()}
    good = [r for r in recs if all(_norm(r.get(k, "")) == v for k, v in want.items())]
    wrong = [r for r in recs if r not in good]
    ok = len(good) == 1 and not wrong
    why = "" if ok else (f"{len(good)} matching, {len(wrong)} wrong: {wrong[:2]}" if recs else "nothing was saved")
    return {"success": ok, "why": why}
