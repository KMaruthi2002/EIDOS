import sys, json, time, torch, torchaudio as ta
from chatterbox.tts import ChatterboxTTS
torch.set_num_threads(2)
t0=time.time(); model = ChatterboxTTS.from_pretrained(device="cpu"); print("loaded", round(time.time()-t0,1), "s", flush=True)
spec=json.load(open(sys.argv[1])); out=sys.argv[2]; import os; os.makedirs(out, exist_ok=True)
import re
for s in spec["scenes"]:
    sents=re.findall(r"[^.!?]+[.!?]+", s["text"]) or [s["text"]]
    parts=[]
    for i,sent in enumerate(sents):
        t1=time.time()
        wav=model.generate(sent.strip(), audio_prompt_path="ref.wav", exaggeration=spec.get("exaggeration",0.5), cfg_weight=spec.get("cfg",0.5), temperature=0.7)
        f=f"{out}/{s['id']}.p{i}.wav"; ta.save(f, wav, model.sr); parts.append(f)
        print(s["id"], i, round(wav.shape[-1]/model.sr,2), "s in", round(time.time()-t1,1), "s", flush=True)
    json.dump({"parts":parts,"sents":sents}, open(f"{out}/{s['id']}.json","w"))
print("done")
