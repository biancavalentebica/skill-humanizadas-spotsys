async (page) => {
  const ID = __ID__;
  const UNIDS = __UNIDS__;
  const url = 'https://spotsys.seazone.dev/lancamentos/empreendimentos-360/' + ID;
  if (!page.url().endsWith('/empreendimentos-360/' + ID)) { await page.goto(url); await page.waitForTimeout(3500); }
  await page.evaluate(async () => {
    const sleep = ms => new Promise(r => setTimeout(r, ms));
    const hit = el => { const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
      const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
      el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
      el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
      el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); };
    for (let k = 0; k < 6; k++) {
      const tab = [...document.querySelectorAll('[role=tab]')].find(t => t.textContent.trim() === 'Por unidade');
      if (tab) { hit(tab); await sleep(2000); if (tab.getAttribute('aria-selected') === 'true') break; } else await sleep(1500);
    }
    for (let k = 0; k < 20 && !document.querySelector('[role=switch]'); k++) await sleep(1000);
    await sleep(1500);
  });
  const HIT = el => { el.scrollIntoView({ block: 'center' }); const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
    const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
    el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
    el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
    el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); };
  const achar = u => page.evaluateHandle(u => {
    const sw = [...document.querySelectorAll('[role=switch]')].filter(s => {
      let r = s.parentElement; for (let k = 0; k < 4 && r && r.textContent.trim() === ''; k++) r = r.parentElement;
      return r && r.textContent.trim() === u;
    });
    return sw.length === 1 ? sw[0] : (sw.length === 0 ? 'NENHUMA' : 'VARIAS');
  }, u);
  const log = [], desmarcadas = [], ja = [];
  for (const u of UNIDS) {
    const hnd = await achar(u);
    const el = hnd.asElement();
    if (!el) { log.push('PAROU em ' + u + ': chave ' + (await hnd.jsonValue())); break; }
    if ((await el.getAttribute('aria-checked')) !== 'true') { ja.push(u); continue; }
    const respP = page.waitForResponse(r => /spot-building-units\/\d+/.test(r.url()) && r.request().method() === 'PATCH', { timeout: 20000 }).catch(() => null);
    await el.evaluate(HIT);
    const r = await respP;
    await page.waitForTimeout(500);
    const body = r ? (r.request().postData() || '') : '';
    if (!r || r.status() !== 200 || !/"is_outdated_area":false/.test(body)) { log.push('PAROU em ' + u + ': ' + (r ? r.status() + ' ' + body : 'sem PATCH')); break; }
    desmarcadas.push(u);
  }
  return { id: ID, pedidas: UNIDS.length, desmarcadas: desmarcadas.length, ja_desmarcadas: ja.length, completo: desmarcadas.length + ja.length === UNIDS.length, lista: desmarcadas.join(' '), log };
}
