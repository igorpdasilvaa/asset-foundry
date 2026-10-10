const MODULE_ID = "interactive-assets";
const BASE = `modules/${MODULE_ID}/assets`;
let REGISTRY = {};

/**
 * Estados guardados no documento (Tile ou Token):
 * flags.interactive-assets.data = { asset, states: [{id,name,src,broken?}], index }
 * Assets com "actor" no assets.json viram Tokens com PV/CA (dnd5e) e quebram ao chegar a 0 PV.
 */
function getData(doc) {
  return doc?.getFlag(MODULE_ID, "data") ?? null;
}

/** Só um GM executa as automações, para não aplicar nada em dobro. */
function isResponsibleGM() {
  return game.user.isGM && (game.users.activeGM ? game.users.activeGM.isSelf : true);
}

function brokenIndex(data) {
  const i = data.states.findIndex(s => s.broken);
  return i === -1 ? data.states.length - 1 : i;
}

async function setState(doc, index, { syncHP = true } = {}) {
  const data = getData(doc);
  if (!data?.states?.length) return;
  const i = ((index % data.states.length) + data.states.length) % data.states.length;
  await doc.update({
    "texture.src": data.states[i].src,
    [`flags.${MODULE_ID}.data.index`]: i
  });
  // Trocar o estado manualmente num Token também ajusta a vida: quebrada = 0 PV, inteira = PV cheio.
  const hp = doc.actor?.system?.attributes?.hp;
  if (syncHP && hp) {
    const value = data.states[i].broken ? 0 : hp.max;
    if (hp.value !== value) await doc.actor.update({ "system.attributes.hp.value": value }, { [MODULE_ID]: { fromState: true } });
  }
}

async function nextState(doc) {
  const data = getData(doc);
  if (data) await setState(doc, (data.index ?? 0) + 1);
}

/** Ator base (um por asset) usado como modelo para os Tokens. */
async function getBaseActor(assetId, def) {
  let actor = game.actors.find(a => a.getFlag(MODULE_ID, "asset") === assetId);
  if (actor) return actor;
  let folder = game.folders.find(f => f.type === "Actor" && f.getFlag(MODULE_ID, "root"));
  folder ??= await Folder.create({ name: "Interactive Assets", type: "Actor", flags: { [MODULE_ID]: { root: true } } });
  const a = def.actor;
  return Actor.create({
    name: def.name,
    type: "npc",
    img: `${BASE}/${def.states[0].src}`,
    folder: folder.id,
    system: {
      attributes: { ac: { calc: "flat", flat: a.ac ?? 10 }, hp: { value: a.hp, max: a.hp } },
      traits: { di: { value: a.immunities ?? [] } },
      details: { cr: 0 }
    },
    prototypeToken: {
      name: def.name,
      width: def.size.w,
      height: def.size.h,
      actorLink: false,
      lockRotation: true,
      disposition: CONST.TOKEN_DISPOSITIONS.NEUTRAL,
      displayBars: CONST.TOKEN_DISPLAY_MODES.OWNER_HOVER,
      bar1: { attribute: "attributes.hp" },
      sight: { enabled: false },
      texture: { src: `${BASE}/${def.states[0].src}` }
    },
    flags: { [MODULE_ID]: { asset: assetId } }
  });
}

/** Coloca o asset no centro da visão atual (ou em x,y): Token se tiver "actor", senão Tile. */
async function placeAsset(assetId, { x, y } = {}) {
  const def = REGISTRY[assetId];
  if (!def) return ui.notifications.warn(`Asset "${assetId}" não encontrado.`);
  const g = canvas.grid.size;
  const width = def.size.w * g;
  const height = def.size.h * g;
  const center = canvas.stage.pivot;
  const pos = { x: Math.round((x ?? center.x) - width / 2), y: Math.round((y ?? center.y) - height / 2) };
  const states = def.states.map(s => ({ ...s, src: `${BASE}/${s.src}` }));
  const flags = { [MODULE_ID]: { data: { asset: assetId, states, index: 0 } } };

  if (def.actor) {
    const actor = await getBaseActor(assetId, def);
    const tokenData = await actor.getTokenDocument({ ...pos, flags });
    const [token] = await canvas.scene.createEmbeddedDocuments("Token", [tokenData.toObject()]);
    return token;
  }

  const [tile] = await canvas.scene.createEmbeddedDocuments("Tile", [{
    ...pos, width, height,
    texture: { src: states[0].src },
    flags
  }]);
  return tile;
}

/** Tokens de asset afetados por uma mudança no ator (Token sem vínculo = ator sintético). */
function tokensForActor(actor) {
  if (actor.isToken) return [actor.token];
  return actor.getActiveTokens(false, true);
}

Hooks.once("init", () => {
  game.settings.register(MODULE_ID, "autoDamage", {
    name: "Aplicar dano automaticamente em assets",
    hint: "Quando uma rolagem de dano do dnd5e tem um asset como alvo, o dano é aplicado sozinho (sem clicar em aplicar no chat).",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });
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

/** PV chegou a 0 → imagem quebrada. PV voltou acima de 0 → imagem inteira. */
Hooks.on("updateActor", async (actor, changes, options) => {
  if (!isResponsibleGM() || options?.[MODULE_ID]?.fromState) return;
  if (foundry.utils.getProperty(changes, "system.attributes.hp.value") === undefined) return;
  const hp = actor.system.attributes.hp.value;
  for (const token of tokensForActor(actor)) {
    const data = getData(token);
    if (!data?.states?.length) continue;
    const broken = brokenIndex(data);
    const current = data.index ?? 0;
    if (hp <= 0 && current !== broken) {
      await setState(token, broken, { syncHP: false });
      ChatMessage.create({ content: `<p><strong>${token.name}</strong> se despedaça!</p>`, speaker: ChatMessage.getSpeaker({ token }) });
    } else if (hp > 0 && data.states[current]?.broken) {
      await setState(token, 0, { syncHP: false });
    }
  }
});

/** Rolagem de dano do dnd5e com um asset como alvo → aplica o dano nele. */
Hooks.on("createChatMessage", async message => {
  if (!isResponsibleGM() || !game.settings.get(MODULE_ID, "autoDamage")) return;
  const flags = message.flags?.dnd5e;
  if (flags?.roll?.type !== "damage") return;
  let targets = flags.targets;
  if (!targets?.length && flags.originatingMessage) targets = game.messages.get(flags.originatingMessage)?.flags?.dnd5e?.targets;
  if (!targets?.length) return;

  const damages = message.rolls.map(r => ({
    value: r.total,
    type: r.options?.type,
    properties: new Set(r.options?.properties ?? [])
  }));
  for (const t of targets) {
    const actor = fromUuidSync(t.uuid);
    const token = actor?.token ?? actor?.getActiveTokens(false, true)[0];
    if (!getData(token) || !actor?.system?.attributes?.hp) continue;
    await actor.applyDamage(damages);
  }
});

/** Botão de troca de estado no HUD (Tile e Token). Funciona em v12 (jQuery) e v13 (HTMLElement). */
function addHudButton(hud, html) {
  const doc = hud.object?.document;
  const data = getData(doc);
  if (!data?.states?.length || !game.user.isGM) return;
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
    await nextState(doc);
    hud.render?.();
  });
  col.appendChild(btn);
}
Hooks.on("renderTileHUD", addHudButton);
Hooks.on("renderTokenHUD", addHudButton);
