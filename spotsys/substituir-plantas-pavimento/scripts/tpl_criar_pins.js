// Editor do 360: CRIA pins numa planta de pavimento (clique na planta em modo edicao -> dialogo "Novo pin na planta"
// -> Vincular a cota -> Adicionar). Funciona com a janela escondida.
// Placeholders: __TITULO__ (botao do pavimento no Editor), __CRIAR__ = {"<cota>": [x%, y%], ...}.
// Cada um grava: POST /portfolio360/editor/buildings/<id>/floor-plan-pins {"spot_image_id","x","y","szi_unit_id"} 201.
// Para se a cota ja tiver pin nesta planta. Testado no Lagoa (11) em 22/10/2026.
async (page) => {
  const TITULO = "__TITULO__", CRIAR = __CRIAR__;
  const hit = (el) => el.evaluate(b => { b.scrollIntoView({block:'center'}); for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window,button:0})); });
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /api-spotsys/.test(r.url())) reqs.push(m + ' ' + r.url().split('?')[0].slice(-50) + ' => ' + r.status() + ' ' + (r.request().postData() || '').slice(0, 120)); };
  page.on('response', h);
  const out = [];
  try {
    const tab = page.getByRole('tab', { name: 'Editor do 360', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(6000); }
    await hit(page.getByRole('button', { name: TITULO, exact: true }));
    await page.waitForTimeout(2500);
    if (await page.getByRole('button', { name: 'Editar Pins' }).count()) { await hit(page.getByRole('button', { name: 'Editar Pins' })); await page.waitForTimeout(2000); }
    for (const [cota, [tx, ty]] of Object.entries(CRIAR)) {
      const ja = await page.locator(`button[data-testid="editor360-pin"][data-cota="${cota}"]`).count();
      if (ja) { out.push('PAROU: ' + cota + ' ja tem pin nesta planta'); break; }
      // 28/10 (Penha): o dialogo fantasma (x undefined) as vezes aparece depois da checagem; fechar antes de clicar
      for (let k = 0; k < 4; k++) {
        const f0 = page.locator('[role=dialog]').filter({ hasText: 'undefined%' });
        if (!(await f0.count())) break;
        await page.keyboard.press('Escape').catch(() => {});
        if (await f0.count()) await hit(f0.first().getByRole('button', { name: 'Close' })).catch(() => {});
        await page.waitForTimeout(800);
      }
      await page.evaluate(([tx, ty]) => {
        const img = document.querySelector('img[alt="Planta baixa"]');
        const R = img.getBoundingClientRect(), x = R.x + R.width * tx / 100, y = R.y + R.height * ty / 100;
        const el = document.elementFromPoint(x, y) || img;
        for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) el.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window,clientX:x,clientY:y,button:0,buttons:t.endsWith('down')?1:0,pointerId:1,isPrimary:true}));
      }, [tx, ty]);
      await page.waitForTimeout(1500);
      const dlg = page.locator('[role=dialog]').filter({ hasText: 'Novo pin na planta' }).filter({ hasNotText: 'undefined%' });
      if ((await dlg.count()) !== 1) { out.push('PAROU: dialogos validos em ' + cota + ' = ' + (await dlg.count())); break; }
      await hit(dlg.locator('button[role=combobox]'));
      await page.waitForTimeout(1200);
      const opt = page.locator(`[role=option][data-value="${cota} (${cota})"]`);
      if ((await opt.count()) !== 1) { out.push('PAROU: opcao ' + cota + ' = ' + (await opt.count())); await hit(dlg.getByRole('button', { name: 'Close' })); break; }
      await hit(opt);
      await page.waitForTimeout(800);
      const sel = (await dlg.locator('button[role=combobox]').innerText()).trim();
      if (sel !== cota + ' (' + cota + ')') { out.push('PAROU: selecionado ' + sel); await hit(dlg.getByRole('button', { name: 'Close' })); break; }
      const n0 = reqs.length;
      await hit(dlg.getByRole('button', { name: 'Adicionar', exact: true }));
      for (let i = 0; i < 24 && reqs.length === n0; i++) await page.waitForTimeout(500);
      const novos = reqs.slice(n0);
      const ok = novos.length === 1 && /floor-plan-pins => 201 /.test(novos[0]);
      out.push(cota + ': ' + tx + '%,' + ty + '% ' + (ok ? 'OK' : 'VER: ' + novos.join(' | ')));
      if (!ok) break;
      await page.waitForTimeout(1000);
      // o clique em Adicionar vaza para a planta e abre um dialogo "fantasma" (x undefined): fechar sem adicionar
      const fant = page.locator('[role=dialog]').filter({ hasText: 'undefined%' });
      if (await fant.count()) { await hit(fant.getByRole('button', { name: 'Close' })); await page.waitForTimeout(800); }
    }
    await hit(page.getByRole('button', { name: 'Sair edição' })).catch(() => out.push('aviso: nao saiu da edicao (recarregar a pagina)'));
    await page.waitForTimeout(1000);
  } finally { page.off('response', h); }
  return { out, reqs };
}
