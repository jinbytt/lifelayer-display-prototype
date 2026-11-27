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


names = {n for e in ENTER.values() for n in e['L'] + e.get('T', []) + [o[0] if isinstance(o, list) else o for o in e['O']]}
names |= {e['C']['src'] for e in ENTER.values() if 'C' in e}
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
  /* selectable cards — Figma selected state: 6px inside gradient stroke #EE6920→#7BC0C7,
     drop shadow #B9D4C5 72% blur 52 y16, check circle #E7481C (off: #F3EFEA) */
  .frame{--u:calc(100cqw / 1920)}
  .pick{pointer-events:auto;cursor:pointer;border-radius:calc(var(--r) * var(--u));
    transition:box-shadow .25s ease-out,transform .2s ease-out;-webkit-tap-highlight-color:transparent}
  .pick:active{transform:scale(.985)}
  .pick::after{content:'';position:absolute;inset:0;border-radius:inherit;padding:calc(6 * var(--u));pointer-events:none;
    background:linear-gradient(160deg,#ee6920,#7bc0c7);opacity:0;transition:opacity .25s ease-out;
    -webkit-mask:linear-gradient(#000 0 0) content-box,linear-gradient(#000 0 0);-webkit-mask-composite:xor;
    mask:linear-gradient(#000 0 0) content-box exclude,linear-gradient(#000 0 0)}
  .pick.on::after{opacity:1}
  .pick.on{box-shadow:0 calc(16 * var(--u)) calc(52 * var(--u)) rgba(185,212,197,.72)!important}
  .card{position:absolute;inset:0;background:#fff;box-shadow:var(--sh0)}
  .card .cimg{position:absolute;inset:0;border-radius:inherit;background-repeat:no-repeat}
  /* cards whose Figma render has the selected stroke baked in: crop 6px and scale the inner area back to full size */
  .card.inset{overflow:hidden}
  .card.inset .cimg{clip-path:inset(calc(6 * var(--u)));transform:scale(var(--sx),var(--sy))}
  .card .chk{position:absolute;width:calc(32 * var(--u));height:calc(32 * var(--u));border-radius:50%;
    background:var(--off,#f3efea) url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'%3E%3Cpath d='M6 12.5l4 4 8-9' fill='none' stroke='%23fff' stroke-width='2.6' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center/62% no-repeat;
    transition:background-color .25s ease-out}
  .card.on .chk{background-color:#e7481c}
  .pick.ov{position:absolute}
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
    const box=(e,x,y,w,h)=>Object.assign(e.style,{left:x/19.2+'%',top:y/10.8+'%',width:w/19.2+'%',height:h/10.8+'%'});
    const toggle=e=>{e.stopPropagation();e.currentTarget.classList.toggle('on');};
    if(E.C){ // card list rebuilt per card: crop of the Figma render + CSS card shell and selection
      const C=E.C,[ox,oy,W,H]=EBOX[C.src],base=120+E.O.length*110;
      C.cards.forEach(([x,y,w,h,on,inset],k)=>{
        const wr=el('div','lyr k-up');box(wr,x,y,w,h);wr.style.setProperty('--d',(base+k*90)+'ms');wr.style.setProperty('--dur','650ms');
        const cd=el('div','card pick'+(on?' on':'')+(inset?' inset':''));if(inset){cd.style.setProperty('--sx',w/(w-12));cd.style.setProperty('--sy',h/(h-12));}cd.style.setProperty('--r',C.r);cd.style.setProperty('--sh0',C.sh);
        const ph=el('div','cimg');Object.assign(ph.style,{backgroundImage:`url(${EIMG[C.src]})`,backgroundSize:`${W/w*100}% ${H/h*100}%`,
          backgroundPosition:`${(x-ox)/(W-w)*100}% ${(y-oy)/(H-h)*100}%`});cd.appendChild(ph);
        if(C.chk){const c=el('i','chk');Object.assign(c.style,{left:C.chk[0]/w*100+'%',top:C.chk[1]/h*100+'%'});if(C.chkOff)c.style.setProperty('--off',C.chkOff);cd.appendChild(c);}
        cd.onclick=toggle;wr.appendChild(cd);d.appendChild(wr);});
    }
    (E.T||[]).forEach(n=>{const im=el('img','ebg');im.src=EIMG[n];im.alt='';pos(n,im);d.appendChild(im);});
    if(E.P) E.P.cards.forEach(([x,y,w,h])=>{const o=el('div','pick ov');o.style.setProperty('--r',E.P.r);box(o,x,y,w,h);o.onclick=toggle;d.appendChild(o);});
  } else {
  const b=el('img');b.src=s.src;b.alt=s.code+' '+s.name;d.appendChild(b);
  }"""
assert old in html
html = html.replace(old, new, 1)

old = "if(s.layers){nodes[i].classList.remove('play')"
assert old in html
html = html.replace(old, "if(s.layers||ENTER[i]){nodes[i].classList.remove('play')", 1)

old = "if(e.target.closest('.hov,.tabhit'))return;"
assert old in html
html = html.replace(old, "if(e.target.closest('.hov,.tabhit,.pick'))return;", 1)

for out in ('LifeLayer_Display_Prototype.html', 'index.html'):
    (ROOT.parent / out).write_text(html)
print('built', len(html) // 1024, 'KB')
