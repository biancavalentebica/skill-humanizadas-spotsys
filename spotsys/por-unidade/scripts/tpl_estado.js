async (page) => {
  const NOMES = __NOMES__;
  const reqP = page.waitForRequest(r => /api-spotsys\.seazone\.com\.br\/api\/v1\//.test(r.url()) && !!r.headers()['x-user-token'], { timeout: 40000 });
  await page.goto('https://spotsys.seazone.dev/lancamentos/empreendimentos-360/1');
  const h = (await reqP).headers();
  const hdr = {};
  for (const k of ['x-user-token', 'x-szi-api-key', 'x-user-email', 'content-type']) if (h[k]) hdr[k] = h[k];
  await page.evaluate(async ([NOMES, hdr]) => {
    const B = 'https://api-spotsys.seazone.com.br/api/v1/';
    const all = async (path) => { let p = 1, acc = []; for (;;) { const r = await fetch(B + path + '&per_page=100&page=' + p, { headers: hdr }); if (!r.ok) throw new Error(path + ' ' + r.status); const j = await r.json(); const d = j.data || []; acc = acc.concat(d); if (d.length < 100) break; p++; } return acc; };
    const norm = s => String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/\s+/g, ' ').trim();
    const blds = await all('spot-buildings?sort=full_name');
    const out = {};
    for (const n of NOMES) {
      const m = blds.filter(b => norm(b.short_name) === norm(n.alvo));
      if (m.length !== 1) { out[n.pasta] = { erro: m.length ? 'nome bate com mais de um empreendimento' : 'empreendimento nao encontrado no SpotSys' }; continue; }
      const id = m[0].id;
      const units = await all('spot-building-units?building_id=' + id);
      const imgs = await all('vistas-unit-images?building_id=' + id);
      out[n.pasta] = { id, nome: m[0].short_name,
        units: units.map(u => ({ id: u.id, code: u.code, outdated: u.is_outdated_area === true })),
        plantas: imgs.filter(i => i.role === 'planta').map(i => ({ vui: i.id, img: i.spot_image_id, unit: i.szi_unit_id, url: i.url })) };
    }
    window.__autoEstado = out;
  }, [NOMES, hdr]);
  return 'ok: ' + Object.keys(await page.evaluate(() => window.__autoEstado)).length + ' pasta(s) lidas';
}
