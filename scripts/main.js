const MODULE_ID = "interactive-assets";
const BASE = `modules/${MODULE_ID}/assets`;
let REGISTRY = {};

/**
 * Estados guardados no documento (Tile ou Token):
 * flags.interactive-assets.data = { asset, states: [{id,name,src,broken?}], index }
 * Assets com "actor" no assets.json viram Tokens; com "hp" eles têm PV/CA (dnd5e) e quebram ao chegar a 0 PV.
 * Cada estado pode trazer "light" (luz do token) e "sound" (som ambiente que acompanha o token).
 * Com "burn" no asset: dano do tipo configurado acende o estado "burning", que causa dano por rodada
 * (em combate) ou a cada N segundos (fora de combate); chegar a 0 PV queimando leva ao estado "burnt".
 */
function getData(doc) {
  return doc?.getFlag(MODULE_ID, "data") ?? null;
}

/** Só um GM executa as automações, para não aplicar nada em dobro. */
function isResponsibleGM() {
  return game.user.isGM && (game.users.activeGM ? game.users.activeGM.isSelf : true);
}

/** Asset com vida: PV e estado "quebrado" andam juntos. */
function isDamageable(data) {
  return data.damageable ?? (REGISTRY[data.asset]?.actor?.hp != null);
}

function brokenIndex(data) {
  const i = data.states.findIndex(s => s.broken && !s.burnt);
  return i === -1 ? data.states.length - 1 : i;
}

const stateIndex = (data, flag) => data.states.findIndex(s => s[flag]);
const currentState = data => data.states[data.index ?? 0];

async function setState(doc, index, { syncHP = true } = {}) {
  const data = getData(doc);
  if (!data?.states?.length) return;
  const i = ((index % data.states.length) + data.states.length) % data.states.length;
  const update = {
    "texture.src": data.states[i].src,
    [`flags.${MODULE_ID}.data.index`]: i
  };
  if (doc.documentName === "Token" && data.states.some(s => s.light)) update.light = lightFor(data.states[i]);
  await doc.update(update);
  // Trocar o estado manualmente num Token também ajusta a vida: quebrada = 0 PV, inteira = PV cheio.
  const hp = doc.actor?.system?.attributes?.hp;
  // Pegando fogo mantém a vida atual (ou enche, se estava em 0).
  if (syncHP && hp && isDamageable(data)) {
    const s = data.states[i];
    const value = s.broken ? 0 : (s.burning && hp.value > 0 ? hp.value : hp.max);
    if (hp.value !== value) await doc.actor.update({ "system.attributes.hp.value": value }, { [MODULE_ID]: { fromState: true } });
  }
}

async function nextState(doc) {
  const data = getData(doc);
  if (data) await setState(doc, (data.index ?? 0) + 1);
}

function stateFlags(assetId, def) {
  const states = def.states.map(s => ({
    ...s,
    src: `${BASE}/${s.src}`,
    ...(s.sound ? { sound: { ...s.sound, src: `${BASE}/${s.sound.src}` } } : {})
  }));
  const data = { asset: assetId, states, index: 0, damageable: def.actor?.hp != null };
  if (def.burn) data.burn = def.burn;
  return { [MODULE_ID]: { data } };
}

/** Estado sem "light" apaga a luz do token. */
function lightFor(state) {
  return state.light ?? { bright: 0, dim: 0 };
}

/* ---------- Som que acompanha o token ---------- */

function linkedSound(token) {
  return token.parent?.sounds.find(s => s.getFlag(MODULE_ID, "token") === token.id);
}

function tokenCenter(token) {
  const g = token.parent.grid.size;
  return { x: token.x + (token.width * g) / 2, y: token.y + (token.height * g) / 2 };
}

/** Cria, move, troca ou remove o AmbientSound ligado ao token conforme o estado atual. */
async function syncSound(token) {
  const data = getData(token);
  if (!data?.states?.length || !token.parent) return;
  const want = data.states[data.index ?? 0]?.sound;
  const sound = linkedSound(token);
  if (!want) {
    if (sound) await sound.delete();
    return;
  }
  const { x, y } = tokenCenter(token);
  const props = { x, y, path: want.src, radius: want.radius ?? 30, volume: want.volume ?? 0.5, easing: true, walls: true, repeat: true };
  if (!sound) {
    await token.parent.createEmbeddedDocuments("AmbientSound", [{ ...props, flags: { [MODULE_ID]: { token: token.id } } }]);
  } else if (sound.x !== x || sound.y !== y || sound.path !== props.path || sound.radius !== props.radius || sound.volume !== props.volume) {
    await sound.update(props);
  }
}

/**
 * Ator base (um por asset) usado como modelo para os Tokens.
 * Os estados ficam também no token protótipo, então arrastar o ator da barra lateral já funciona.
 */
async function getBaseActor(assetId, def) {
  let actor = game.actors.find(a => a.getFlag(MODULE_ID, "asset") === assetId);
  if (actor) {
    // Mantém o token protótipo em dia com o assets.json (novos estados, luz, som...).
    const flags = stateFlags(assetId, def);
    const current = getData(actor.prototypeToken);
    if (JSON.stringify(current) !== JSON.stringify(flags[MODULE_ID].data)) {
      const update = { [`prototypeToken.flags.${MODULE_ID}.data`]: flags[MODULE_ID].data };
      if (def.states.some(s => s.light)) update["prototypeToken.light"] = lightFor(def.states[0]);
      await actor.update(update);
    }
    return actor;
  }
  let folder = game.folders.find(f => f.type === "Actor" && f.getFlag(MODULE_ID, "root"));
  folder ??= await Folder.create({ name: "Interactive Assets", type: "Actor", flags: { [MODULE_ID]: { root: true } } });
  const a = def.actor;
  const system = { details: { cr: 0 } };
  if (a.hp != null) {
    system.attributes = { ac: { calc: "flat", flat: a.ac ?? 10 }, hp: { value: a.hp, max: a.hp } };
    system.traits = { di: { value: a.immunities ?? [] } };
  }
  return Actor.create({
    name: def.name,
    type: "npc",
    img: `${BASE}/${def.states[0].src}`,
    folder: folder.id,
    system,
    prototypeToken: {
      name: def.name,
      width: def.size.w,
      height: def.size.h,
      actorLink: false,
      lockRotation: true,
      disposition: CONST.TOKEN_DISPOSITIONS.NEUTRAL,
      displayBars: CONST.TOKEN_DISPLAY_MODES.OWNER_HOVER,
      displayName: CONST.TOKEN_DISPLAY_MODES.HOVER,
      ...(a.hp != null ? { bar1: { attribute: "attributes.hp" } } : { displayBars: CONST.TOKEN_DISPLAY_MODES.NONE }),
      sight: { enabled: false },
      texture: { src: `${BASE}/${def.states[0].src}` },
      ...(def.states.some(s => s.light) ? { light: lightFor(def.states[0]) } : {}),
      flags: stateFlags(assetId, def)
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
  const flags = stateFlags(assetId, def);

  if (def.actor) {
    const actor = await getBaseActor(assetId, def);
    const tokenData = await actor.getTokenDocument({ ...pos, flags });
    const [token] = await canvas.scene.createEmbeddedDocuments("Token", [tokenData.toObject()]);
    return token;
  }

  const [tile] = await canvas.scene.createEmbeddedDocuments("Tile", [{
    ...pos, width, height,
    texture: { src: `${BASE}/${def.states[0].src}` },
    flags
  }]);
  return tile;
}

/** Atualiza Tokens/Tiles já colocados quando o assets.json muda, mantendo o estado atual (pelo id). */
async function refreshPlaced(assetId, def) {
  const fresh = stateFlags(assetId, def)[MODULE_ID].data;
  for (const scene of game.scenes) {
    for (const collection of ["tokens", "tiles"]) {
      const updates = [];
      for (const doc of scene[collection]) {
        const data = getData(doc);
        if (data?.asset !== assetId) continue;
        const index = Math.max(0, fresh.states.findIndex(s => s.id === currentState(data)?.id));
        const next = { ...fresh, index };
        if (JSON.stringify(next) !== JSON.stringify(data)) updates.push({ _id: doc.id, [`flags.${MODULE_ID}.data`]: next });
      }
      if (updates.length) await scene.updateEmbeddedDocuments(collection === "tokens" ? "Token" : "Tile", updates);
    }
  }
}

/* ---------- Fogo ---------- */

/** Atores que acabaram de levar dano do tipo que incendeia (preenchido no cálculo de dano do dnd5e). */
const recentFire = new Map();

Hooks.on("dnd5e.calculateDamage", (actor, damages) => {
  const types = new Set(damages.filter(d => d.value > 0).map(d => d.type));
  if (types.size) recentFire.set(actor.uuid, { types, at: Date.now() });
});

function tookDamageType(actor, type) {
  const hit = recentFire.get(actor.uuid);
  recentFire.delete(actor.uuid);
  return !!hit && Date.now() - hit.at < 3000 && hit.types.has(type);
}

function burningTokens(scene) {
  return scene?.tokens.filter(t => {
    const data = getData(t);
    return data?.burn && currentState(data)?.burning && t.actor;
  }) ?? [];
}

async function burnTick(token) {
  const tick = getData(token).burn.tick ?? { damage: 2, type: "fire" };
  await token.actor.applyDamage([{ value: tick.damage, type: tick.type, properties: new Set() }]);
}

/** Em combate: dano a cada nova rodada, nos assets queimando da cena do combate. */
Hooks.on("updateCombat", async (combat, changes, options) => {
  if (!isResponsibleGM() || !("round" in changes) || options?.direction < 0 || !combat.started) return;
  for (const token of burningTokens(combat.scene ?? canvas.scene)) await burnTick(token);
});

/** Fora de combate: dano a cada N segundos (relógio real), pausado quando o jogo está pausado. */
let burnTimer = null;
function startBurnTimer() {
  if (burnTimer) return;
  const seconds = Math.min(...Object.values(REGISTRY).map(d => d.burn?.tick?.seconds ?? Infinity));
  if (!Number.isFinite(seconds)) return;
  burnTimer = setInterval(async () => {
    if (!isResponsibleGM() || game.paused) return;
    for (const scene of game.scenes) {
      if (game.combats.some(c => c.started && c.scene?.id === scene.id)) continue;
      for (const token of burningTokens(scene)) await burnTick(token);
    }
  }, seconds * 1000);
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
    const version = game.modules.get(MODULE_ID).version;
    REGISTRY = await (await fetch(`${BASE}/assets.json?v=${version}`, { cache: "no-cache" })).json();
    console.log(`${MODULE_ID} | ${Object.keys(REGISTRY).length} asset(s) carregado(s)`);
    if (isResponsibleGM()) {
      // Garante um ator por asset na pasta "Interactive Assets", pronto para arrastar para a cena.
      for (const [id, def] of Object.entries(REGISTRY)) {
        if (def.actor) await getBaseActor(id, def);
        await refreshPlaced(id, def);
      }
      startBurnTimer();
    }
  } catch (err) {
    console.error(`${MODULE_ID} | falha ao carregar assets.json`, err);
  }
});

function say(token, text) {
  return ChatMessage.create({ content: `<p><strong>${token.name}</strong> ${text}</p>`, speaker: ChatMessage.getSpeaker({ token }) });
}

/**
 * Regras de estado pela vida:
 * - 0 PV: queimando (ou atingido por fogo) → queimada; senão → quebrada.
 * - Dano de fogo com PV > 0 → começa a pegar fogo.
 * - Curado acima de 0 estando quebrada/queimada → inteira.
 */
Hooks.on("updateActor", async (actor, changes, options) => {
  if (!isResponsibleGM() || options?.[MODULE_ID]?.fromState) return;
  if (foundry.utils.getProperty(changes, "system.attributes.hp.value") === undefined) return;
  const hp = actor.system.attributes.hp.value;
  for (const token of tokensForActor(actor)) {
    const data = getData(token);
    if (!data?.states?.length || !isDamageable(data)) continue;
    const state = currentState(data);
    const fire = data.burn ? tookDamageType(actor, data.burn.damageType ?? "fire") : false;
    const burnt = stateIndex(data, "burnt");

    if (hp <= 0) {
      if (state?.broken) continue;
      if (data.burn && burnt !== -1 && (state?.burning || fire)) {
        await setState(token, burnt, { syncHP: false });
        await say(token, "queima até virar carvão!");
      } else {
        await setState(token, brokenIndex(data), { syncHP: false });
        await say(token, "se despedaça!");
      }
    } else if (state?.broken) {
      await setState(token, 0, { syncHP: false });
    } else if (fire && !state?.burning && stateIndex(data, "burning") !== -1) {
      await setState(token, stateIndex(data, "burning"), { syncHP: false });
      await say(token, "começa a pegar fogo!");
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
    const data = getData(token);
    if (!data || !isDamageable(data) || !actor?.system?.attributes?.hp) continue;
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

/** Som acompanha o token: ao criar, mover, mudar de tamanho ou de estado; e some quando o token é apagado. */
Hooks.on("createToken", token => {
  if (isResponsibleGM() && getData(token)) syncSound(token);
});
Hooks.on("updateToken", (token, changes) => {
  if (!isResponsibleGM() || !getData(token)) return;
  if (["x", "y", "width", "height"].some(k => k in changes) || foundry.utils.hasProperty(changes, `flags.${MODULE_ID}`)) syncSound(token);
});
Hooks.on("deleteToken", token => {
  if (isResponsibleGM()) linkedSound(token)?.delete();
});
