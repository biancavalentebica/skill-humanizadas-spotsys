// Editor do 360: clica em Publicar e confere POST /portfolio360/buildings/<id>/publicar 200 (nao tem dialogo).
async (page) => {
  const hit = (el) => el.evaluate(b => { for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /api-spotsys/.test(r.url())) reqs.push(m + ' ' + r.url().split('?')[0].slice(-50) + ' => ' + r.status()); };
  page.on('response', h);
  try {
    const tab = page.getByRole('tab', { name: 'Editor do 360', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(6000); }
    if (await page.evaluate(() => [...document.querySelectorAll('button')].some(b => b.innerText.trim() === 'Sair edição'))) return { erro: 'modo edicao aberto: sair antes de publicar' };
    await hit(page.getByRole('button', { name: 'Publicar', exact: true }));
    await page.waitForTimeout(5000);
  } finally { page.off('response', h); }
  const pub = await page.evaluate(() => ([...document.querySelectorAll('span,div,p')].map(e => e.innerText).find(t => /^Publicado em/.test(t || '')) || '').split('\n')[0]);
  return { ok: reqs.some(r => /\/publicar => 200/.test(r)), reqs, pub };
}
