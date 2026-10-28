async (page) => {
  const ID = __ID__;
  const NOVAS = __NOVAS__;   // { unidade: bytes do arquivo local }
  const ANT = __ANT__;       // { unidade: [spot_image_id antigos] } das que recebem arquivo novo
  const MANTER = __MANTER__; // { unidade: [spot_image_id] } das que tinham planta e nao tem arquivo novo
  const reqP = page.waitForRequest(r => /api-spotsys\.seazone\.com\.br\/api\/v1\//.test(r.url()) && !!r.headers()['x-user-token'], { timeout: 40000 });
  await page.goto('https://spotsys.seazone.dev/lancamentos/empreendimentos-360/' + ID);
  const h = (await reqP).headers();
  const hdr = {};
  for (const k of ['x-user-token', 'x-szi-api-key', 'x-user-email', 'content-type']) if (h[k]) hdr[k] = h[k];
  const res = await page.evaluate(async ([ID, NOVAS, ANT, MANTER, hdr]) => {
    const B = 'https://api-spotsys.seazone.com.br/api/v1/';
    const all = async (path) => { let p = 1, acc = []; for (;;) { const r = await fetch(B + path + '&per_page=100&page=' + p, { headers: hdr }); if (!r.ok) throw new Error(path + ' ' + r.status); const j = await r.json(); const d = j.data || []; acc = acc.concat(d); if (d.length < 100) break; p++; } return acc; };
    const units = await all('spot-building-units?building_id=' + ID);
    const imgs = (await all('vistas-unit-images?building_id=' + ID)).filter(i => i.role === 'planta');
    const code = {}, outd = {}; units.forEach(u => { code[u.id] = u.code; outd[u.code] = u.is_outdated_area === true; });
    const por = {}; imgs.forEach(i => { const c = code[i.szi_unit_id]; (por[c] = por[c] || []).push(i); });
    const prob = [], tam = {};
    for (const [u, bytes] of Object.entries(NOVAS)) {
      const l = por[u] || [];
      if (l.length !== 1) { prob.push(u + ': ' + l.length + ' plantas (esperado 1)'); continue; }
      if ((ANT[u] || []).includes(l[0].spot_image_id)) { prob.push(u + ': continua com a planta antiga'); continue; }
      if (!(l[0].url in tam)) { const r = await fetch(l[0].url, { method: 'HEAD' }); tam[l[0].url] = +r.headers.get('content-length'); }
      if (tam[l[0].url] !== bytes) prob.push(u + ': bytes ' + tam[l[0].url] + ' diferente do arquivo local ' + bytes);
      if (outd[u]) prob.push(u + ': Area desatualizada ainda marcada');
    }
    for (const [u, ids] of Object.entries(MANTER)) {
      const atual = (por[u] || []).map(i => i.spot_image_id).sort().join(',');
      if (atual !== ids.slice().sort().join(',')) prob.push(u + ': planta mudou e nao deveria (sem arquivo novo)');
    }
    const semPlanta = units.map(u => u.code).filter(c => !por[c]);
    return { id: ID, ok: prob.length === 0, problemas: prob, unidades: units.length, com_planta: Object.keys(por).length,
      imagens: new Set(imgs.map(i => i.spot_image_id)).size, sem_planta: semPlanta, novas_conferidas: Object.keys(NOVAS).length };
  }, [ID, NOVAS, ANT, MANTER, hdr]);
  await page.evaluate(r => { window.__autoVer = r; }, res);
  return res;
}
