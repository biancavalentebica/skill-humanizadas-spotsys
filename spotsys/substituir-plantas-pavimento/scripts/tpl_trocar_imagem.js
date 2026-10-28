// Troca a imagem de UMA planta de pavimento (aba Plantas > Editar > Upload > Salvar).
// Placeholders: __TITULO__ (titulo exato da linha), __ARQ__ (caminho absoluto do arquivo, barras /).
// Arquivo grande: setInputFiles demora (59 MB ~1 min); se a chamada do MCP cair, o modal fica aberto -> conferir e Salvar a mao.
// Espera o upload terminar (preview com URL do storage) antes de Salvar; confere PATCH spot_images 204.
async (page) => {
  const TITULO = "__TITULO__", ARQ = "__ARQ__";
  const hit = (el) => el.evaluate(b => { b.scrollIntoView({block:'center'}); for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /supabase\.co|api-spotsys/.test(r.url())) reqs.push({ m, u: r.url().split('?')[0].replace(/^https:\/\/[^/]+/, ''), s: r.status(), b: (r.request().postData() || '').slice(0, 300) }); };
  page.on('response', h);
  try {
    const tab = page.getByRole('tab', { name: 'Plantas', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(5000); }
    const row = page.locator('table tbody tr').filter({ has: page.locator('td', { hasText: new RegExp('^' + TITULO + '$') }) });
    if ((await row.count()) !== 1) return { erro: 'linhas com o titulo: ' + (await row.count()) };
    const antes = await row.locator('img').getAttribute('src');
    await hit(row.locator('button[title="Editar"]'));
    await page.waitForTimeout(2000);
    const modal = page.locator('body > div').last();
    const tit = await modal.locator('input[placeholder="Ex: Planta tipo A"]').inputValue();
    if (tit !== TITULO) return { erro: 'modal errado: ' + tit };
    await modal.locator('input[type=file]').setInputFiles(ARQ, { timeout: 240000 });
    let nova = null;
    for (let i = 0; i < 300 && !nova; i++) {
      await page.waitForTimeout(1000);
      nova = await modal.evaluate(d => { if (/Enviando/.test(d.innerText)) return null; const i = [...d.querySelectorAll('img')].map(x => x.src).find(s => /\/storage\/v1\/object\/public\//.test(s)); return i || null; });
    }
    if (!nova || nova === antes) { await hit(modal.getByRole('button', { name: 'Cancelar', exact: true })); return { erro: 'upload nao terminou / mesma url', nova, reqs }; }
    await hit(modal.getByRole('button', { name: 'Salvar', exact: true }));
    for (let i = 0; i < 30; i++) { await page.waitForTimeout(1000); if (await page.locator('body > div').last().evaluate(d => !/Editar planta/.test(d.innerText))) break; }
    await page.waitForTimeout(2000);
    const patch = reqs.find(r => r.m === 'PATCH' && /\/rest\/v1\/spot_images/.test(r.u));
    const ok = !!patch && patch.s < 300 && patch.b.includes(nova);
    return { ok, titulo: TITULO, antes, nova, reqs: reqs.map(r => r.m + ' ' + r.u.slice(0, 80) + ' => ' + r.s) };
  } finally { page.off('response', h); }
}
