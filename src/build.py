"""Build LifeLayer_Display_Prototype.html (+ index.html) from src/base.html.

Adds the screen-entry motion: on screens listed in src/enter/screens.json the flat
screenshot is replaced by the Figma background layers (L) plus the content objects
(O), and the objects fade in and rise one by one each time the screen is entered.
Layer images live in src/enter/webp, positions (Figma render bounds) in boxes.json.
"""
import base64, json, pathlib, re, struct

ROOT = pathlib.Path(__file__).resolve().parent
ENTER = json.loads((ROOT / 'enter/screens.json').read_text())
POS = json.loads((ROOT / 'enter/boxes.json').read_text())


def webp_size(b: bytes):
    kind = b[12:16]
    if kind == b'VP8X':
        return 1 + int.from_bytes(b[24:27], 'little'), 1 + int.from_bytes(b[27:30], 'little')
    if kind == b'VP8L':
        bits = int.from_bytes(b[21:25], 'little')
        return (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    if kind == b'VP8 ':
        w, h = struct.unpack('<HH', b[26:30])
        return w & 0x3FFF, h & 0x3FFF
    raise ValueError('unknown webp chunk %r' % kind)


names = {n for e in ENTER.values() for n in e['L'] + [o[0] if isinstance(o, list) else o for o in e['O']]}
img, box = {}, {}
for n in sorted(names):
    data = (ROOT / 'enter/webp' / f'{n}.webp').read_bytes()
    w, h = webp_size(data)
    img[n] = 'data:image/webp;base64,' + base64.b64encode(data).decode()
    box[n] = POS[n] + [w, h]

html = (ROOT / 'base.html').read_text()

# drop the flat screenshots that the layered screens no longer use
m = re.search(r'const S=(\[.*?\]);\n', html)
S = json.loads(m.group(1))
for k in ENTER:
    S[int(k)]['src'] = None
html = html[:m.start()] + 'const S=' + json.dumps(S, ensure_ascii=False) + ';\n' + html[m.end():]

CSS = """  /* screen entry: objects fade in and rise one by one */
  .ebg{position:absolute;pointer-events:none;user-select:none;-webkit-user-drag:none}
  .scr.play .lyr.k-up{animation-name:kUp;animation-timing-function:cubic-bezier(.2,.8,.2,1)}
  @keyframes kUp{from{opacity:0;transform:translateY(1.25cqw)}to{opacity:1;transform:none}}
"""
anchor = '  @media (prefers-reduced-motion:reduce){'
assert anchor in html
html = html.replace(anchor, CSS + anchor, 1)

DATA = ('const ENTER=' + json.dumps(ENTER) + ';\nconst EBOX=' + json.dumps(box) +
        ';\nconst EIMG=' + json.dumps(img) + ';\n')
anchor = 'const app=document.getElementById'
assert anchor in html
html = html.replace(anchor, DATA + anchor, 1)

old = """  } else {
  const b=el('img');b.src=s.src;b.alt=s.code+' '+s.name;d.appendChild(b);
  }"""
new = """  } else if(ENTER[i]){
    const E=ENTER[i],pos=(n,e)=>{const [x,y,w,h]=EBOX[n];Object.assign(e.style,{left:x/19.2+'%',top:y/10.8+'%',width:w/19.2+'%',height:h/10.8+'%'});};
    d.style.background=E.bg;
    E.L.forEach(n=>{const im=el('img','ebg');im.src=EIMG[n];im.alt='';pos(n,im);d.appendChild(im);});
    E.O.forEach((o,k)=>{const [n,dl]=Array.isArray(o)?o:[o,120+k*110];
      const w=el('div','lyr k-up');pos(n,w);w.style.setProperty('--d',dl+'ms');w.style.setProperty('--dur','650ms');
      const im=el('img');im.src=EIMG[n];im.alt='';w.appendChild(im);d.appendChild(w);});
  } else {
  const b=el('img');b.src=s.src;b.alt=s.code+' '+s.name;d.appendChild(b);
  }"""
assert old in html
html = html.replace(old, new, 1)

old = "if(s.layers){nodes[i].classList.remove('play')"
assert old in html
html = html.replace(old, "if(s.layers||ENTER[i]){nodes[i].classList.remove('play')", 1)

for out in ('LifeLayer_Display_Prototype.html', 'index.html'):
    (ROOT.parent / out).write_text(html)
print('built', len(html) // 1024, 'KB')
