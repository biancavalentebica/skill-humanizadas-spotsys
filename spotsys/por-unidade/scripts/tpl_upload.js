async (page) => {
  const ID = __ID__;
  const itens = __ITENS__;
  const F = { force: true, timeout: 8000 };
  const HIT = el => { el.scrollIntoView({ block: 'center' }); const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
    const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
    el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
    el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
    el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); };
  const hit = loc => loc.evaluate(HIT);
  const url = 'https://spotsys.seazone.dev/lancamentos/empreendimentos-360/' + ID;
  const count = () => page.evaluate(() => { const t = document.body.innerText; const i = t.indexOf('Plantas Baixas'); return i < 0 ? null : parseInt(t.slice(i + 14, i + 30).trim()); });
  if (!page.url().endsWith('/empreendimentos-360/' + ID) || (await count()) === null) {
    if (!page.url().endsWith('/empreendimentos-360/' + ID)) { await page.goto(url); await page.waitForTimeout(3500); }
    await page.evaluate(async () => {
      const sleep = ms => new Promise(r => setTimeout(r, ms));
      const hit = el => { const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
        const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
        el.dispatchEvent(new PointerEvent('pointerover',o)); el.dispatchEvent(new MouseEvent('mouseover',o));
        el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
        try{el.focus()}catch(e){}
        el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
        el.dispatchEvent(new MouseEvent('click',{...o,buttons:0})); };
      for (let k = 0; k < 6; k++) {
        const tab = [...document.querySelectorAll('[role=tab]')].find(t => t.textContent.trim() === 'Por unidade');
        if (tab) { hit(tab); await sleep(2000); if (tab.getAttribute('aria-selected') === 'true') break; } else await sleep(1500);
      }
      for (let k = 0; k < 20 && !document.body.innerText.includes('Plantas Baixas'); k++) await sleep(1000);
      await sleep(1500);
    });
  }
  // 28/10/2026: a aba Por unidade ganhou as subabas Por cota / Por imagem; Plantas Baixas fica em Por imagem
  const porImagem = async () => {
    for (let k = 0; k < 15 && (await count()) === null; k++) {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('button')].find(b => b.textContent.trim() === 'Por imagem');
        if (!el) return;
        const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
        const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
        el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
        el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
        el.dispatchEvent(new MouseEvent('click',{...o,buttons:0}));
      });
      await page.waitForTimeout(1500);
    }
  };
  const log = [];
  for (const it of itens) {
    const nomeArq = it.f.split(String.fromCharCode(92)).pop();
    await porImagem();
    const antes = await count();
    if (antes === null) { log.push('ERRO secao nao carregou'); break; }
    await page.waitForFunction(() => !/Passo [12] de 2/.test(document.body.innerText), null, { timeout: 15000 });
    let aberto = false;
    for (let k = 0; k < 4 && !aberto; k++) {
      await page.evaluate(() => {
        const el = [...document.querySelectorAll('button')].filter(b => b.textContent.trim() === 'Adicionar')[0];
        el.scrollIntoView({ block: 'center' });
        const b = el.getBoundingClientRect(), cx = b.x+b.width/2, cy = b.y+b.height/2;
        const o = {bubbles:true,cancelable:true,composed:true,clientX:cx,clientY:cy,button:0,buttons:1,pointerId:1,pointerType:'mouse',isPrimary:true};
        el.dispatchEvent(new PointerEvent('pointerdown',o)); el.dispatchEvent(new MouseEvent('mousedown',o));
        el.dispatchEvent(new PointerEvent('pointerup',{...o,buttons:0})); el.dispatchEvent(new MouseEvent('mouseup',{...o,buttons:0}));
        el.dispatchEvent(new MouseEvent('click',{...o,buttons:0}));
      });
      aberto = await page.waitForSelector('input[type="file"]', { state: 'attached', timeout: 4000 }).then(() => true).catch(() => false);
    }
    if (!aberto) { log.push(nomeArq + ' ERRO modal nao abriu'); break; }
    await page.setInputFiles('input[type="file"]', it.f);
    await page.waitForTimeout(1500);
    const ok = await page.evaluate(n => document.body.innerText.includes(n) && /Passo 1 de 2/.test(document.body.innerText), nomeArq);
    if (!ok) { log.push(nomeArq + ' ERRO arquivo nao apareceu no modal'); break; }
    let p2 = false;
    for (let k = 0; k < 4 && !p2; k++) {
      await hit(page.getByRole('button', { name: /Pr.ximo/ }));
      p2 = await page.waitForFunction(() => /Passo 2 de 2/.test(document.body.innerText), null, { timeout: 4000 }).then(() => true).catch(() => false);
    }
    if (!p2) { log.push(nomeArq + ' ERRO nao avancou para passo 2 (modal aberto)'); break; }
    await page.waitForTimeout(800);
    for (const u of it.u) { await hit(page.getByRole('button', { name: u, exact: true }).last()); await page.waitForTimeout(250); }
    await page.waitForTimeout(800);
    const sel = await page.evaluate(() => { const m = document.body.innerText.match(/\((\d+) selecionadas?\)/); return m && +m[1]; });
    if (sel !== it.u.length) { log.push(nomeArq + ' ERRO sel=' + sel + ' esperado=' + it.u.length + ' (modal aberto)'); break; }
    const respP = page.waitForResponse(r => r.request().method() === 'POST' && /spot-images/.test(r.url()), { timeout: 30000 }).catch(() => null);
    const bulkP = new Promise(res => {
      let t;
      const fim = v => { page.off('response', onR); page.off('requestfailed', onF); clearTimeout(t); res(v); };
      const onR = r => { if (/vistas-unit-images\/bulk/.test(r.url()) && r.request().method() !== 'OPTIONS') fim(String(r.status())); };
      const onF = q => { if (/vistas-unit-images\/bulk/.test(q.url())) fim('FALHOU ' + ((q.failure() || {}).errorText || '')); };
      page.on('response', onR); page.on('requestfailed', onF);
      t = setTimeout(() => fim('sem bulk'), 40000);
    });
    await hit(page.getByRole('button', { name: /^Salvar \(/ }));
    const r = await respP;
    const bulk = await bulkP;
    await page.waitForTimeout(2000);
    log.push(nomeArq + ' [' + it.u.join(' ') + '] img=' + (r ? r.status() : 'sem resp') + ' bulk=' + bulk + ' ' + antes + '->' + (await count()));
    if (!/^20\d$/.test(bulk)) { log.push('PAROU: associacao nao confirmada em ' + nomeArq); break; }
  }
  return log;
}
