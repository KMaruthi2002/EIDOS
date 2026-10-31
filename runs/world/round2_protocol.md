# Round 2 protocol (fixed before any round 2 run)

- Recipes: test2 (six recipes, chosen by rule after round 1, never run before).
- Code: version 4 (ranked looks on Muse Spark Open, evidence tracker, search-back), frozen at this commit.
- Calibration: seen 0.9 (as on the development recipes).
- Live tracker: seen 2.0, absent 0.35, min_p 0.
  Chosen on the development recipes (dev and dev4, 70 recordings) as the setting with the best
  accuracy there (67%; always answering "mistake": 69%), so no setting beat the base rate in development.
- Baselines: Muse Spark Open asked directly, with the same step list and frames spread over the whole recording.
- Run once; results in runs/world/test2_v4/ and summary_test2_v4.json.
