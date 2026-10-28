// Baixa arquivos do Drive pelo Chrome Claude (ja logado no Google). Os arquivos caem em ~/Downloads
// (o evento de download do Playwright nao chega pelo CDP): depois mover para a pasta do empreendimento e conferir tamanho.
// Placeholder: __IDS__ = ["<file id>", ...] (copiar da listagem do Drive, nunca de cabeca).
async (page) => {
  const IDS = __IDS__;
  const p = await page.context().newPage();
  try {
    for (const id of IDS) {
      await p.goto('https://drive.usercontent.google.com/download?id=' + id + '&export=download&confirm=t', { timeout: 30000 }).catch(() => {});
      await p.waitForTimeout(3000);
    }
    await p.waitForTimeout(15000);
  } finally { await p.close(); }
  return 'disparados ' + IDS.length + ' downloads (conferir ~/Downloads)';
}
