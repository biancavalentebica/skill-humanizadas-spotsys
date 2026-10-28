// Le o estado do empreendimento no 360 (so leitura): plantas de pavimento, pins, unidades e publicacao.
// Placeholder: __ID__ (id do empreendimento). Guarda tudo em window.__estado.
// Depois: browser_evaluate "() => JSON.stringify(window.__estado)" filename=<pav>/<id>_estado_<antes|depois>.json
async (page) => {
  const ID = "__ID__";
  const BASE = 'https://api-spotsys.seazone.com.br/api/v1/';
  const hit = (el) => el.evaluate(b => { for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const reqP = page.waitForRequest(r => r.url().startsWith(BASE + 'spot-building-units?building_id=' + ID + '&'), { timeout: 60000 }).catch(() => null);
  const edP = page.waitForResponse(r => r.url().split('?')[0] === BASE + 'portfolio360/editor/buildings/' + ID && r.request().method() === 'GET', { timeout: 60000 }).catch(() => null);
  await page.goto('https://spotsys.seazone.dev/lancamentos/empreendimentos-360/' + ID);
  const req = await reqP;
  if (!req) return { erro: 'nao capturou a requisicao de unidades (pagina em branco? recarregar sem cache)' };
  await page.waitForTimeout(4000);
  await hit(page.getByRole('tab', { name: 'Editor do 360', exact: true }));
  const edR = await edP;
  if (!edR) return { erro: 'editor nao carregou' };
  const editor = await edR.json();
  const h = req.headers();
  const headers = {};
  for (const k of ['x-user-token', 'x-szi-api-key', 'x-user-email']) if (h[k]) headers[k] = h[k];
  const res = await page.evaluate(async ([BASE, ID, headers]) => {
    const units = [];
    for (let p = 1; p < 20; p++) {
      const r = await fetch(BASE + 'spot-building-units?building_id=' + ID + '&per_page=100&page=' + p, { headers });
      const j = await r.json();
      units.push(...j.data);
      if (units.length >= j.total || !j.data.length) break;
    }
    const pub = await (await fetch(BASE + 'portfolio360/buildings/' + ID + '/publicacao', { headers })).json();
    return { units: units.map(u => ({ id: u.id, code: u.code })), pub };
  }, [BASE, ID, headers]);
  const estado = { id: ID, lido_em: new Date().toISOString(), editor, units: res.units, pub: res.pub };
  await page.evaluate(x => { window.__estado = x; }, estado);
  const pins = editor.floor_plan_pins;
  const porUn = {};
  pins.forEach(p => { porUn[p.szi_unit_id] = (porUn[p.szi_unit_id] || 0) + 1; });
  return {
    publicacao: res.pub,
    unidades: res.units.length,
    pins: pins.length,
    sem_pin: res.units.filter(u => !porUn[u.id]).map(u => u.code),
    pin_repetido: res.units.filter(u => porUn[u.id] > 1).map(u => u.code),
    plantas: editor.floor_plans.map(f => f.id + ' | ' + f.title + ' | ordem ' + f.sort_order + ' | zoom ' + f.pin_scale + ' | area ' + f.is_outdated_area + ' | pins ' + pins.filter(p => String(p.spot_image_id) === String(f.id)).length + ' | ' + f.image_url.split('/').slice(-1)[0])
  };
}
