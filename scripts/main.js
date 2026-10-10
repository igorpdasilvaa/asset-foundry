const MODULE_ID = "interactive-assets";
const BASE = `modules/${MODULE_ID}/assets`;
let REGISTRY = {};

/** Estados guardados no próprio Tile: flags.interactive-assets = { asset, states: [{id,name,src}], index } */
function getData(tile) {
  return tile?.getFlag(MODULE_ID, "data") ?? null;
}

async function setState(tile, index) {
  const data = getData(tile);
  if (!data?.states?.length) return;
  const i = ((index % data.states.length) + data.states.length) % data.states.length;
  await tile.update({
    "texture.src": data.states[i].src,
    [`flags.${MODULE_ID}.data.index`]: i
  });
}

async function nextState(tile) {
  const data = getData(tile);
  if (data) await setState(tile, (data.index ?? 0) + 1);
}

/** Cria o Tile do asset no centro da visão atual (ou em x,y). */
async function placeAsset(assetId, { x, y } = {}) {
  const def = REGISTRY[assetId];
  if (!def) return ui.notifications.warn(`Asset "${assetId}" não encontrado.`);
  const g = canvas.grid.size;
  const width = def.size.w * g;
  const height = def.size.h * g;
  const center = canvas.stage.pivot;
  const states = def.states.map(s => ({ ...s, src: `${BASE}/${s.src}` }));
  const [tile] = await canvas.scene.createEmbeddedDocuments("Tile", [{
    x: Math.round((x ?? center.x) - width / 2),
    y: Math.round((y ?? center.y) - height / 2),
    width, height,
    texture: { src: states[0].src },
    flags: { [MODULE_ID]: { data: { asset: assetId, states, index: 0 } } }
  }]);
  return tile;
}

Hooks.once("init", () => {
  game.modules.get(MODULE_ID).api = {
    placeAsset, nextState, setState,
    get assets() { return REGISTRY; }
  };
});

Hooks.once("ready", async () => {
  try {
    REGISTRY = await (await fetch(`${BASE}/assets.json`)).json();
    console.log(`${MODULE_ID} | ${Object.keys(REGISTRY).length} asset(s) carregado(s)`);
  } catch (err) {
    console.error(`${MODULE_ID} | falha ao carregar assets.json`, err);
  }
});

/** Botão no HUD do Tile para alternar o estado. Funciona em v12 (jQuery) e v13 (HTMLElement). */
Hooks.on("renderTileHUD", (hud, html) => {
  const tile = hud.object?.document;
  const data = getData(tile);
  if (!data?.states?.length) return;
  const root = html instanceof HTMLElement ? html : html[0];
  const col = root.querySelector(".col.right") ?? root;
  const current = data.states[data.index ?? 0];
  const next = data.states[((data.index ?? 0) + 1) % data.states.length];

  const btn = document.createElement("div");
  btn.className = "control-icon ia-state";
  btn.dataset.tooltip = `Mudar para: ${next.name}`;
  btn.innerHTML = `<i class="fas fa-repeat"></i><span class="ia-label">${current.name}</span>`;
  btn.addEventListener("click", async ev => {
    ev.preventDefault();
    await nextState(tile);
    hud.render?.();
  });
  col.appendChild(btn);
});
