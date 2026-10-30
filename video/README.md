# EIDOS explainer video

The launch explainer is built in code with Remotion. All EIDOS footage in it is real screen capture from the benchmark runs and the Studio; some clips are sped up.

- `src/launch.tsx`: the launch video (composition `EidosLaunch`).
- `narration_v4.json`: the narration script. `tts_make.mjs` voices it into `public/vo4/` (Kokoro TTS) and writes `src/timeline4.json`.
- `make_music.py`: synthesizes the original background track into `public/music/bed.wav` from the scene starts in `music_scenes.json` (convert to `bed.mp3` with ffmpeg).
- `src/story.tsx`, `src/Explainer.tsx`: earlier cuts, kept for reference.

## Render

```console
npm i
npx remotion render src/index.ts EidosLaunch out/EIDOS_launch.mp4
```
