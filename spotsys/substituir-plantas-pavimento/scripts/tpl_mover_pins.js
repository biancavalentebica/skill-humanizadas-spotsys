// Editor do 360: MOVE pins existentes de UMA planta de pavimento (arrasta por eventos de ponteiro; funciona com a janela escondida).
// Placeholders: __TITULO__ (botao do pavimento no Editor), __MOVER__ = {"<cota>": [x%, y%], ...} (posicao nova em % da imagem).
// Cada arraste grava sozinho: PATCH /portfolio360/editor/buildings/<id>/floor-plan-pins/<uuid> {"x","y"} 200. Um pin por vez.
// Testado no Lagoa (11) em 22/10/2026.
async (page) => {
  const TITULO = "__TITULO__", MOVER = __MOVER__;
  const hit = (el) => el.evaluate(b => { b.scrollIntoView({block:'center'}); for (const t of ['pointerdown','mousedown','pointerup','mouseup','click']) b.dispatchEvent(new (t.startsWith('pointer')?PointerEvent:MouseEvent)(t,{bubbles:true,cancelable:true,view:window})); });
  const reqs = [];
  const h = r => { const m = r.request().method(); if (m !== 'GET' && /api-spotsys/.test(r.url())) reqs.push(m + ' ' + r.url().split('?')[0].slice(-60) + ' => ' + r.status() + ' ' + (r.request().postData() || '').slice(0, 120)); };
  page.on('response', h);
  const out = [];
  try {
    const tab = page.getByRole('tab', { name: 'Editor do 360', exact: true });
    if ((await tab.getAttribute('aria-selected')) !== 'true') { await hit(tab); await page.waitForTimeout(6000); }
    await hit(page.getByRole('button', { name: TITULO, exact: true }));
    await page.waitForTimeout(2500);
    if (await page.getByRole('button', { name: 'Editar Pins' }).count()) { await hit(page.getByRole('button', { name: 'Editar Pins' })); await page.waitForTimeout(2000); }
    for (const [cota, [tx, ty]] of Object.entries(MOVER)) {
      const n0 = reqs.length;
      const r = await page.evaluate(async ([cota, tx, ty]) => {
        const img = document.querySelector('img[alt="Planta baixa"]');
        const pins = document.querySelectorAll(`button[data-testid="editor360-pin"][data-cota="${cota}"]`);
        if (pins.length !== 1) return 'PAROU: pins com cota ' + cota + ' = ' + pins.length;
        const pin = pins[0], alvo = pin.firstElementChild;
        const R = img.getBoundingClientRect(), P = pin.getBoundingClientRect();
        const sx = P.x + P.width / 2, sy = P.y + P.height / 2, ex = R.x + R.width * tx / 100, ey = R.y + R.height * ty / 100;
        const ev = (el, t, x, y, b) => el.dispatchEvent(new PointerEvent(t, { bubbles: true, cancelable: true, composed: true, view: window, clientX: x, clientY: y, pointerId: 1, pointerType: 'mouse', isPrimary: true, button: 0, buttons: b }));
        const me = (el, t, x, y, b) => el.dispatchEvent(new MouseEvent(t, { bubbles: true, cancelable: true, view: window, clientX: x, clientY: y, button: 0, buttons: b }));
        const antes = pin.style.left + ',' + pin.style.top;
        ev(alvo, 'pointerdown', sx, sy, 1); me(alvo, 'mousedown', sx, sy, 1);
        for (let i = 1; i <= 10; i++) { const x = sx + (ex - sx) * i / 10, y = sy + (ey - sy) * i / 10; ev(alvo, 'pointermove', x, y, 1); ev(window, 'pointermove', x, y, 1); me(document, 'mousemove', x, y, 1); await new Promise(r => setTimeout(r, 30)); }
        ev(alvo, 'pointerup', ex, ey, 0); ev(window, 'pointerup', ex, ey, 0); me(document, 'mouseup', ex, ey, 0);
        return antes;
      }, [cota, tx, ty]);
      if (String(r).startsWith('PAROU')) { out.push(r); break; }
      for (let i = 0; i < 10 && reqs.length === n0; i++) await page.waitForTimeout(500);
      const novos = reqs.slice(n0);
      const ok = novos.length === 1 && / => 200 /.test(novos[0]) && /floor-plan-pins/.test(novos[0]);
      out.push(cota + ': ' + r + ' -> ' + tx + '%,' + ty + '% ' + (ok ? 'OK' : 'VER: ' + novos.join(' | ')));
      if (!ok) break;
      await page.waitForTimeout(800);
    }
    await hit(page.getByRole('button', { name: 'Sair edição' }));
    await page.waitForTimeout(1000);
  } finally { page.off('response', h); }
  return { out, reqs };
}
