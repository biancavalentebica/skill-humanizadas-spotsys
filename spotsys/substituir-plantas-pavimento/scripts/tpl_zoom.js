// Editor do 360: deixa o zoom dos pins (slider "Escala dos pins") em 1 = 100% nas plantas listadas.
// Placeholder: __TITULOS__ = ["<titulo>", ...] (plantas de pavimento COM pins).
// Funciona com a janela escondida: clique pela sequencia HIT e tecla por dispatchEvent (cada passo de 0,1 grava sozinho:
// PATCH /portfolio360/editor/buildings/<id>/escala 200). Trocar de pavimento sai do modo edicao.
async (page) => {
  const TITULOS = __TITULOS__;
  const hit = (el) => el.evaluate(b => { b.scrollIntoView({block:'center'}); for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /supabase\.co\/rest|api-spotsys/.test(r.url())) reqs.push(m + ' ' + r.url().split('?')[0].slice(-45) + ' => ' + r.status() + ' ' + (r.request().postData() || '').slice(0, 120)); };
  page.on('response', h);
  const out = [];
  try {
    const tab = page.getByRole('tab', { name: 'Editor do 360', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(6000); }
    for (const nome of TITULOS) {
      await hit(page.getByRole('button', { name: nome, exact: true }));
      await page.waitForTimeout(3000);
      await hit(page.getByRole('button', { name: 'Editar Pins' }));
      await page.waitForTimeout(2000);
      const s = page.getByRole('slider', { name: 'Escala dos pins' });
      const vals = [await s.getAttribute('aria-valuenow', { timeout: 10000 })];
      for (let i = 0; i < 30 && Math.abs(Number(await s.getAttribute('aria-valuenow')) - 1) > 1e-9; i++) {
        const key = Number(await s.getAttribute('aria-valuenow')) < 1 ? 'ArrowRight' : 'ArrowLeft';
        await s.evaluate((el, key) => { el.focus(); el.dispatchEvent(new KeyboardEvent('keydown', { key, code: key, bubbles: true, cancelable: true })); el.dispatchEvent(new KeyboardEvent('keyup', { key, code: key, bubbles: true })); }, key);
        await page.waitForTimeout(800);
        vals.push(await s.getAttribute('aria-valuenow'));
        if (vals.length > 2 && vals[vals.length - 1] === vals[vals.length - 2]) break;
      }
      await page.waitForTimeout(2000);
      await hit(page.getByRole('button', { name: 'Sair edição' }));
      await page.waitForTimeout(1500);
      out.push(nome + ': ' + vals.join(' -> '));
    }
  } finally { page.off('response', h); }
  return { out, reqs };
}
