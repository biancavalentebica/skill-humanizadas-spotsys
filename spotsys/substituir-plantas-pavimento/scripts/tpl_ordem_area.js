// Aba Plantas: acerta a Ordem e desliga a Area desatualizada das plantas de PAVIMENTO.
// Placeholders: __ORDEM__ = {"<titulo>": <ordem>, ...} (todas as plantas de pavimento, na sequencia final)
//               __AREA__  = ["<titulo>", ...] (plantas de pavimento cuja Area desatualizada deve ficar DESLIGADA)
// Confere cada gravacao (POST spot_image_overlays 200). So mexe no que esta diferente.
async (page) => {
  const ORDEM = __ORDEM__, AREA = __AREA__;
  const hit = (el) => el.evaluate(b => { b.scrollIntoView({block:'center'}); for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /supabase\.co\/rest|api-spotsys/.test(r.url())) reqs.push(m + ' ' + r.url().split('?')[0].replace(/^https:\/\/[^/]+/, '') + ' => ' + r.status() + ' ' + (r.request().postData() || '').replace(/"source_360_url":"[^"]*",?/, '').slice(0, 140)); };
  page.on('response', h);
  const out = [];
  try {
    const tab = page.getByRole('tab', { name: 'Plantas', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(5000); }
    const row = t => page.locator('table tbody tr').filter({ has: page.locator('td', { hasText: new RegExp('^' + esc(t) + '$') }) });
    for (const [t, ord] of Object.entries(ORDEM)) {
      if ((await row(t).count()) !== 1) { out.push('PAROU: linhas com titulo ' + t + ' = ' + (await row(t).count())); return { out, reqs }; }
      const atual = (await row(t).locator('td').nth(4).innerText()).trim();
      if (atual === String(ord)) { out.push(t + ': ordem ' + atual + ' (ok)'); continue; }
      await hit(row(t).locator('button[title="Editar"]'));
      await page.waitForTimeout(2000);
      const modal = page.locator('body > div').last();
      if ((await modal.locator('input[placeholder="Ex: Planta tipo A"]').inputValue()) !== t) { out.push('PAROU: modal errado em ' + t); return { out, reqs }; }
      await modal.locator('input[type=number]').fill(String(ord));
      await hit(modal.getByRole('button', { name: 'Salvar', exact: true }));
      for (let i = 0; i < 20; i++) { await page.waitForTimeout(1000); if (await page.locator('body > div').last().evaluate(d => !/Editar planta/.test(d.innerText))) break; }
      await page.waitForTimeout(2000);
      out.push(t + ': ordem ' + atual + ' -> ' + (await row(t).locator('td').nth(4).innerText()).trim());
    }
    for (const t of AREA) {
      const sw = row(t).locator('[role=switch]');
      const a = await sw.getAttribute('aria-checked');
      if (a === 'true') { await hit(sw); await page.waitForTimeout(2500); }
      out.push(t + ': area ' + a + ' -> ' + await sw.getAttribute('aria-checked'));
    }
  } finally { page.off('response', h); }
  return { out, reqs };
}
