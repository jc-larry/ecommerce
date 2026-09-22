const { LiveGarmentEngine } = require('./eng/live-garment-engine.js');
const data = require('./video_landmarks.json');
const toLm = f => f.map(p => ({ x: p[0], y: p[1], z: p[2], visibility: p[3] }));
const base = data.frames.filter(Boolean).map(toLm);

const oldRule = lm => [11, 12, 23, 24].every(i => (lm[i].visibility ?? 0) > 0.5);
function run(nombre, frames) {
  const eng = new LiveGarmentEngine(); eng.rig = { kind: 'top' }; eng.setVideoAspect(816 / 464);
  let viejo = 0, nuevo = 0, parpadeoNuevo = 0, parpadeoViejo = 0, pn = null, pv = null;
  for (const lm of frames) {
    const o = oldRule(lm), n = eng.resolveBody(lm) !== null;
    viejo += o; nuevo += n;
    if (pn !== null && n !== pn) parpadeoNuevo++;
    if (pv !== null && o !== pv) parpadeoViejo++;
    pn = n; pv = o;
  }
  const pct = x => (100 * x / frames.length).toFixed(1) + '%';
  console.log(`${nombre.padEnd(46)} regla vieja ${pct(viejo).padStart(6)} (${String(parpadeoViejo).padStart(3)} parpadeos)  ->  nuevo ${pct(nuevo).padStart(6)} (${String(parpadeoNuevo).padStart(3)} parpadeos)`);
  return nuevo / frames.length;
}
const conf = (fs, fn) => fs.map(lm => lm.map((p, i) => ({ ...p, visibility: fn(p, i) })));

const r1 = run('A. Video tal cual', base);
const r2 = run('B. Caderas fuera de cuadro (persona cerca)', conf(base, (p, i) => (i === 23 || i === 24) ? 0.05 : p.visibility));
const r3 = run('C. Visibilidad oscilando 0.45<->0.55', base.map((lm, k) => lm.map(p => ({ ...p, visibility: k % 2 ? 0.55 : 0.45 }))));
const r4 = run('D. Caderas Y hombros a 0.3 (borde de sombra)', conf(base, (p, i) => [11, 12, 23, 24].includes(i) ? 0.3 : p.visibility));

// Caderas estimadas vs reales (error relativo al ancho de hombros) en el video
const eng = new LiveGarmentEngine(); eng.rig = { kind: 'top' }; eng.setVideoAspect(816 / 464); let err = [];
for (const lm of base) {
  if ((lm[23].visibility ?? 0) < 0.8 || (lm[24].visibility ?? 0) < 0.8) continue;
  const v = eng.resolveBody(lm.map((p, i) => (i === 23 || i === 24) ? { ...p, visibility: 0.05 } : p));
  const span = Math.hypot(lm[11].x - lm[12].x, lm[11].y - lm[12].y);
  const m = (a, b) => ({ x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 });
  const real = m(lm[23], lm[24]), est = m(v[23], v[24]);
  err.push(Math.hypot(real.x - est.x, real.y - est.y) / span);
}
err.sort((a, b) => a - b);
console.log(`\nCadera estimada vs real (con caderas visibles, n=${err.length}): mediana ${err[err.length >> 1].toFixed(2)} · p90 ${err[Math.floor(err.length * .9)].toFixed(2)} anchos de hombros`);

// Mascara: vacia -> no fiable; llena sobre el torso -> fiable
const W = 100, H = 100, empty = new Float32Array(W * H), full = new Float32Array(W * H).fill(1);
const lm = base[Math.floor(base.length / 2)];
console.log('Mascara vacia cubre torso :', LiveGarmentEngine.maskCoversTorso(empty, W, H, lm, 816 / 464));
console.log('Mascara llena cubre torso :', LiveGarmentEngine.maskCoversTorso(full, W, H, lm, 816 / 464));
process.exit(r1 > 0.98 && r2 > 0.98 && r3 > 0.98 ? 0 : 1);
