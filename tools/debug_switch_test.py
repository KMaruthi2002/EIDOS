import cv2, json
from pathlib import Path
from eidos.ui import see as S
def test_dump(shot):
    out = Path('debug'); out.mkdir(exist_ok=True)
    for design in ["skin=A&theme=dark&labels=top&scale=1.2", "skin=A"]:
        img = shot(f"task=settings&{design}", lambda p: p.get_by_text("Security", exact=True).first.click())
        tag = design.replace('&', '_').replace('=', '-')
        cv2.imwrite(str(out / f'{tag}.png'), img)
        lines = S.lines(img)
        (out / f'{tag}.json').write_text(json.dumps([[l.text, l.x, l.y, l.w, l.h] for l in lines], indent=1))
        print(design, [l.text for l in lines])
        print('hits', S.find_text(lines, "Two-factor sign-in", 0.8)[:3])
