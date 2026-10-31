# EIDOS explainer video

The launch explainer is built in code with Remotion. All footage is real: recordings from CaptainCook4D (Apache 2.0) and HoloAssist (CDLA-Permissive-2.0), the benchmark runs, and the Studio; some clips are sped up.

- `src/launch2.tsx`: the current video (composition `EidosLaunch2`): real world, screens and robots. Its narration is `narration_v5.json` (voiced into `public/vo5/`, timings in `src/timeline5.json`), its data `src/world_data.json`, and its music `public/music/bed2.mp3`, made by `make_music.py` from `music_scenes.json`.
- `src/launch.tsx`: the earlier screens-only launch video (composition `EidosLaunch`).
- `narration_v4.json`: the narration script. `tts_make.mjs` voices it into `public/vo4/` (Kokoro TTS) and writes `src/timeline4.json`.
- `make_music.py`: synthesizes the original background track into `public/music/bed.wav` from the scene starts in `music_scenes.json` (convert to `bed.mp3` with ffmpeg).
- `src/story.tsx`, `src/Explainer.tsx`: earlier cuts, kept for reference.

## Render

```console
npm i
npx remotion render src/index.ts EidosLaunch2 out/EIDOS_launch.mp4
```
