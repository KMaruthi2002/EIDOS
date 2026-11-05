"""Save recorded runs for the sample skills' practice recordings, so the Studio can follow them
without a model key.

A recorded run is the list of looks Muse Spark gave on that recording during the benchmark's
development runs (version 3: ranked guesses over the last 20 seconds, one every 3 seconds),
cached in runs/world/looks/. Replaying it through the live session gives exactly what EIDOS did
live, at the same moments. Nothing is invented: a recording without cached looks gets no replay.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOOKS = ROOT / "runs" / "world" / "looks"
# sample -> (benchmark demonstration, {practice id: benchmark recording})
RUNS = {"tomato": ("12_2", {"skipped-oil": "12_6", "clean": "12_9"})}


def main():
    for name, (demo, recs) in RUNS.items():
        out = ROOT / "samples" / "world" / name / "replays"
        out.mkdir(exist_ok=True)
        for pid, rid in recs.items():
            src = next(LOOKS.glob(f"{demo}__{rid}__*__ranked20.json"), None)
            if not src:
                print("no recorded looks for", name, pid)
                continue
            looks = json.loads(src.read_text())
            (out / f"{pid}.json").write_text(json.dumps({
                "mode": "v3", "model": "Muse Spark (muse-spark-1.3)",
                "about": f"A recorded run: the looks Muse Spark gave on this recording (CaptainCook4D {rid}), replayed at the same moments. No key needed.",
                "source": f"runs/world/looks/{src.name}", "looks": looks}, indent=0))
            print("saved", name, pid, len(looks), "looks")


if __name__ == "__main__":
    main()
