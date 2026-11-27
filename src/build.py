"""Build the single-file prototype: src/template.html + src/screens.json + src/layers/*.png"""
import base64, json, pathlib
root = pathlib.Path(__file__).resolve().parent
S = json.loads((root/'screens.json').read_text())
GLOW = {0, 1, 2, 3}  # composed from layers over the animated glow, no flat image needed
screens = [{**s, 'src': None if i in GLOW else s['src']} for i, s in enumerate(S)]
assets = {p.stem: 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode() for p in sorted((root/'layers').glob('*.png'))}
html = (root/'template.html').read_text()
html = html.replace('__ASSETS__', json.dumps(assets)).replace('__SCREENS__', json.dumps(screens, ensure_ascii=False))
for out in ('LifeLayer_Display_Prototype.html', 'index.html'):
    (root.parent/out).write_text(html)
print('built', len(html)//1024, 'KB')
