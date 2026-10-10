// Carregador: decide de onde vem o código e as imagens.
// Modo desenvolvimento ligado: último commit do GitHub (via jsDelivr), basta recarregar a página.
// Desligado: arquivos instalados no servidor.
const MODULE_ID = "interactive-assets";
const REPO = "igorpdasilvaa/asset-foundry";

Hooks.once("init", () => {
  game.settings.register(MODULE_ID, "devMode", {
    name: "Modo desenvolvimento (GitHub)",
    hint: "Carrega código e imagens do último commit do GitHub a cada recarregamento, sem precisar atualizar o módulo.",
    scope: "world",
    config: true,
    type: Boolean,
    default: false,
    requiresReload: true
  });
});

async function latestCommit() {
  try {
    const r = await fetch(`https://api.github.com/repos/${REPO}/commits/main`, {
      headers: { Accept: "application/vnd.github.sha" },
      cache: "no-store"
    });
    if (r.ok) return (await r.text()).trim();
    console.warn(`${MODULE_ID} | GitHub respondeu ${r.status}, usando arquivos locais`);
  } catch (e) {
    console.warn(`${MODULE_ID} | falha ao consultar o GitHub, usando arquivos locais`, e);
  }
  return null;
}

Hooks.once("ready", async () => {
  let version = game.modules.get(MODULE_ID).version;
  let root = null;
  if (game.settings.get(MODULE_ID, "devMode")) {
    const sha = await latestCommit();
    if (sha) {
      root = `https://cdn.jsdelivr.net/gh/${REPO}@${sha}`;
      version = sha.slice(0, 7);
    }
  }
  const core = root
    ? await import(`${root}/scripts/core.js`)
    : await import(`./core.js?v=${version}`);
  await core.start({ base: root ? `${root}/assets` : `modules/${MODULE_ID}/assets`, version });
  if (root) ui.notifications.info(`Interactive Assets carregado do GitHub (${version})`);
  else if (game.settings.get(MODULE_ID, "devMode")) ui.notifications.warn("Interactive Assets: GitHub indisponível, usando a versão instalada");
});
