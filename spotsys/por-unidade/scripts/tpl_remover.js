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
    for (let k = 0; k < 20 && !document.body.innerText.includes('Plantas Baixas'); k++) await sleep(1000);
    await sleep(2500);
  });
  // espera os cartoes carregarem: sem isso, unidade com planta era contada como 'ja sem planta' (Cachoeira, 13/10)
  await page.waitForFunction(() => [...document.querySelectorAll('button')].some(b => (b.getAttribute('title') || '').startsWith('Remover ')), null, { timeout: 30000 }).catch(() => null);
  await page.waitForTimeout(1500);
  const HIT = el => { el.scrollIntoView({ block: 'center' }); const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
    const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
    el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
    el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
    el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); };
  const achar = u => page.evaluateHandle(u => {
    const h = [...document.querySelectorAll('*')].find(e => e.children.length === 0 && e.textContent.trim() === 'Plantas Baixas');
    if (!h) return 'SEM_SECAO';
    let s = h; while (s.parentElement && !s.parentElement.textContent.includes('Imagens Internas')) s = s.parentElement;
    const bs = [...s.querySelectorAll('button')].filter(b => b.getAttribute('title') === 'Remover ' + u);
    return bs.length === 1 ? bs[0] : (bs.length === 0 ? 'NENHUM' : 'VARIOS');
  }, u);
  const permitidas = UNIDS.map(u => 'Remover ' + u + ' desta foto?');
  await page.evaluate(p => { if (!window.__confOrig) window.__confOrig = window.confirm; window.confirm = m => p.includes(m); }, permitidas);
  const log = [], ok = [], ja = [];
  try {
    for (const u of UNIDS) {
      const hnd = await achar(u);
      const el = hnd.asElement();
      if (!el) {
        const v = await hnd.jsonValue();
        if (v === 'NENHUM') { ja.push(u); continue; }   // ja estava sem planta (ex.: rodada anterior parou no meio)
        log.push('PAROU em ' + u + ': botao Remover ' + v); break;
      }
      const respP = page.waitForResponse(r => /vistas-unit-images\/\d+/.test(r.url()) && r.request().method() === 'DELETE', { timeout: 25000 }).catch(() => null);
      await el.evaluate(HIT);
      const r = await respP;
      let depois = 'ELEMENTO';
      for (let k = 0; k < 20 && depois !== 'NENHUM'; k++) {   // a lista recarrega devagar as vezes: espera ate 10 s
        await page.waitForTimeout(500);
        const hd = await achar(u);
        depois = hd.asElement() ? 'ELEMENTO' : await hd.jsonValue();
      }
      if (!r || r.status() >= 300 || depois !== 'NENHUM') { log.push('PAROU em ' + u + ': ' + (r ? 'DELETE ' + r.status() : 'sem DELETE') + ' / depois=' + depois); break; }
      ok.push(u);
    }
  } finally {
    await page.evaluate(() => { if (window.__confOrig) { window.confirm = window.__confOrig; delete window.__confOrig; } });
  }
  return { id: ID, pedidas: UNIDS.length, removidas: ok.length, ja_sem_planta: ja.length, completo: ok.length + ja.length === UNIDS.length && log.length === 0, removidas_lista: ok.join(' '), log };
}
