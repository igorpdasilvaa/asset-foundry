const MODULE_ID = "interactive-assets";
const BASE = `modules/${MODULE_ID}/assets`;
let REGISTRY = {};

/**
 * Estados guardados no documento (Tile ou Token):
 * flags.interactive-assets.data = { asset, states: [{id,name,src,broken?}], index }
 * Assets com "actor" no assets.json viram Tokens; com "hp" eles têm PV/CA (dnd5e) e quebram ao chegar a 0 PV.
 * Cada estado pode trazer "light" (luz do token) e "sound" (som ambiente que acompanha o token).
 * "reactions": regras por tipo de dano (troca de estado, perda de PV máximo, empurrão).
 * "onZero": qual estado quebrado usar quando a vida chega a 0 (pelo estado atual ou pelo tipo do golpe).
 * Estados com "dot" causam dano a cada "tique" (nova rodada em combate, ou a cada tickSeconds fora dele);
 * "ticks" limita a duração e "then" diz para qual estado voltar ao fim.
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
  const i = data.states.findIndex(s => s.broken);
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
    [`flags.${MODULE_ID}.data.index`]: i,
    [`flags.${MODULE_ID}.data.ticksLeft`]: data.states[i].ticks ?? null
  };
  if (doc.documentName === "Token" && data.states.some(s => s.light)) update.light = lightFor(data.states[i]);
  await doc.update(update);
  // Trocar o estado manualmente num Token também ajusta a vida: quebrada = 0 PV, inteira = PV cheio.
  const hp = doc.actor?.system?.attributes?.hp;
  // Pegando fogo mantém a vida atual (ou enche, se estava em 0).
  if (syncHP && hp && isDamageable(data)) {
    const s = data.states[i];
    const value = s.broken ? 0 : (i !== 0 && hp.value > 0 ? hp.value : hp.max);
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
  const data = { asset: assetId, states, index: 0, ticksLeft: null, damageable: def.actor?.hp != null };
  for (const key of ["reactions", "onZero", "tickSeconds"]) if (def[key] != null) data[key] = def[key];
  return { [MODULE_ID]: { data } };
}

/** Imagem do ator na barra lateral: vídeo (.webm) não aparece lá, então usa o .png de mesmo nome. */
function thumbnail(def) {
  return `${BASE}/${def.states[0].src.replace(/\.webm$/, ".png")}`;
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
      update["prototypeToken.texture.src"] = `${BASE}/${def.states[0].src}`;
      await actor.update(update);
    }
    // Imunidades/resistências em dia com o assets.json.
    if (def.actor.hp != null) {
      const same = (set, list) => JSON.stringify([...(set ?? [])].sort()) === JSON.stringify([...(list ?? [])].sort());
      const t = actor.system.traits;
      if (!same(t.di?.value, def.actor.immunities) || !same(t.dr?.value, def.actor.resistances)) {
        await actor.update({ "system.traits.di.value": def.actor.immunities ?? [], "system.traits.dr.value": def.actor.resistances ?? [] });
      }
    }
    return actor;
  }
  let folder = game.folders.find(f => f.type === "Actor" && f.getFlag(MODULE_ID, "root"));
  folder ??= await Folder.create({ name: "Interactive Assets", type: "Actor", flags: { [MODULE_ID]: { root: true } } });
  const a = def.actor;
  const system = { details: { cr: 0 } };
  if (a.hp != null) {
    system.attributes = { ac: { calc: "flat", flat: a.ac ?? 10 }, hp: { value: a.hp, max: a.hp } };
    system.traits = { di: { value: a.immunities ?? [] }, dr: { value: a.resistances ?? [] } };
  }
  return Actor.create({
    name: def.name,
    type: "npc",
    img: thumbnail(def),
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
        const next = { ...fresh, index, ticksLeft: data.ticksLeft ?? null };
        if (JSON.stringify(next) === JSON.stringify(data)) continue;
        const update = { _id: doc.id, [`flags.${MODULE_ID}.data`]: next };
        // Se a imagem do estado atual mudou (ex.: PNG virou animação), troca também no que já está na cena.
        if (doc.texture.src === currentState(data)?.src) update["texture.src"] = next.states[index].src;
        updates.push(update);
      }
      if (updates.length) await scene.updateEmbeddedDocuments(collection === "tokens" ? "Token" : "Tile", updates);
    }
  }
}

/* ---------- Reações por tipo de dano ---------- */

/** Tipos (e valores) de dano que cada ator acabou de levar, preenchido no cálculo de dano do dnd5e. */
const recentDamage = new Map();
/** Quem atacou cada ator por último (para empurrar na direção certa). */
const recentAttacker = new Map();

Hooks.on("dnd5e.calculateDamage", (actor, damages) => {
  const types = new Map();
  for (const d of damages) if (d.value > 0) types.set(d.type, (types.get(d.type) ?? 0) + d.value);
  if (types.size) recentDamage.set(actor.uuid, { types, at: Date.now() });
});

function takeRecent(map, actor) {
  const hit = map.get(actor.uuid);
  map.delete(actor.uuid);
  return hit && Date.now() - hit.at < 3000 ? hit : null;
}

/** A regra vale para o estado atual? Estados "sticky" (fogo, gelo) só mudam por regras que os citam em "from". */
function ruleAllows(rule, data) {
  const state = currentState(data);
  if (rule.from) return rule.from.includes(state?.id);
  if (state?.sticky || state?.broken) return false;
  return !rule.except?.includes(state?.id);
}

const matchesTypes = (rule, types) => !rule.types || rule.types.some(t => types.has(t));
const indexOfId = (data, id) => data.states.findIndex(s => s.id === id);

async function pushAway(token, attacker, squares) {
  const g = token.parent.grid.size;
  const a = tokenCenter(attacker), b = tokenCenter(token);
  const ang = Math.atan2(b.y - a.y, b.x - a.x);
  const dx = Math.round(Math.cos(ang)), dy = Math.round(Math.sin(ang));
  if (!dx && !dy) return;
  const clamp = (v, lo, hi) => Math.min(Math.max(v, lo), hi);
  const x = clamp(token.x + dx * g * squares, 0, token.parent.dimensions.width - token.width * g);
  const y = clamp(token.y + dy * g * squares, 0, token.parent.dimensions.height - token.height * g);
  await token.update({ x, y });
}

async function applyEffect(rule, token, actor, types, attacker) {
  if (rule.effect === "maxHpLoss") {
    const loss = rule.types.reduce((n, t) => n + (types.get(t) ?? 0), 0);
    const hp = actor.system.attributes.hp;
    await actor.update({ "system.attributes.hp.tempmax": (hp.tempmax ?? 0) - loss }, { [MODULE_ID]: { fromState: true } });
    await say(token, `perde ${loss} de PV máximo.`);
  } else if (rule.effect === "push" && attacker) {
    await pushAway(token, attacker, rule.squares ?? 1);
  }
}

/* ---------- Tiques: dano contínuo e duração dos estados ---------- */

function tickingTokens(scene) {
  return scene?.tokens.filter(t => {
    const data = getData(t);
    const state = data && currentState(data);
    return state && (state.dot || state.ticks) && t.actor && data.ticksLeft !== 0;
  }) ?? [];
}

/** Atores levando dano do próprio estado (ácido, fogo): esse dano não dispara reações de novo. */
const tickingNow = new Set();

async function tick(token) {
  const data = getData(token);
  const state = currentState(data);
  if (data.ticksLeft === 0) return;
  if (state.dot) {
    tickingNow.add(token.actor.uuid);
    try {
      await token.actor.applyDamage([{ value: state.dot.damage, type: state.dot.type, properties: new Set() }]);
    } finally {
      tickingNow.delete(token.actor.uuid);
    }
  }
  // O dano pode ter trocado o estado (ex.: queimou até 0); só conta a duração se ainda estiver nele.
  const now = getData(token);
  if (currentState(now)?.id !== state.id || now.ticksLeft == null) return;
  const left = now.ticksLeft - 1;
  if (left <= 0 && state.then) await setState(token, indexOfId(now, state.then), { syncHP: false });
  else await token.update({ [`flags.${MODULE_ID}.data.ticksLeft`]: Math.max(left, 0) });
}

/** Em combate: um tique a cada nova rodada, nos assets da cena do combate. */
Hooks.on("updateCombat", async (combat, changes, options) => {
  if (!isResponsibleGM() || !("round" in changes) || options?.direction < 0 || !combat.started) return;
  for (const token of tickingTokens(combat.scene ?? canvas.scene)) await tick(token);
});

/** Fora de combate: um tique a cada tickSeconds (relógio real), parado quando o jogo está pausado. */
let tickTimer = null;
function startTickTimer() {
  if (tickTimer) return;
  const seconds = Math.min(6, ...Object.values(REGISTRY).map(d => d.tickSeconds ?? 6));
  tickTimer = setInterval(async () => {
    if (!isResponsibleGM() || game.paused) return;
    for (const scene of game.scenes) {
      if (game.combats.some(c => c.started && c.scene?.id === scene.id)) continue;
      for (const token of tickingTokens(scene)) await tick(token);
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
      startTickTimer();
    }
  } catch (err) {
    console.error(`${MODULE_ID} | falha ao carregar assets.json`, err);
  }
});

function say(token, text) {
  return ChatMessage.create({ content: `<p><strong>${token.name}</strong> ${text}</p>`, speaker: ChatMessage.getSpeaker({ token }) });
}

/**
 * Regras de estado pela vida e pelo tipo de dano (definidas no assets.json):
 * - 0 PV: primeira regra de "onZero" que bate (estado atual ou tipo do golpe).
 * - PV > 0: primeira regra de "reactions" com "to" que bate troca o estado; regras com "effect" sempre rodam.
 * - Curada acima de 0 estando quebrada → inteira.
 */
Hooks.on("updateActor", async (actor, changes, options) => {
  if (!isResponsibleGM() || options?.[MODULE_ID]?.fromState) return;
  if (foundry.utils.getProperty(changes, "system.attributes.hp.value") === undefined) return;
  const hp = actor.system.attributes.hp.value;
  const hit = takeRecent(recentDamage, actor);
  const types = tickingNow.has(actor.uuid) ? new Map() : (hit?.types ?? new Map());
  const zeroTypes = hit?.types ?? new Map();
  const attacker = takeRecent(recentAttacker, actor)?.token;
  for (const token of tokensForActor(actor)) {
    const data = getData(token);
    if (!data?.states?.length || !isDamageable(data)) continue;
    const state = currentState(data);

    if (hp <= 0) {
      if (state?.broken) continue;
      const rule = (data.onZero ?? [{ to: data.states[brokenIndex(data)].id, say: "se despedaça!" }])
        .find(r => (!r.state || r.state === state?.id) && matchesTypes(r, zeroTypes));
      const target = rule ? indexOfId(data, rule.to) : brokenIndex(data);
      await setState(token, target === -1 ? brokenIndex(data) : target, { syncHP: false });
      if (rule?.say) await say(token, rule.say);
      continue;
    }
    if (state?.broken) {
      await setState(token, 0, { syncHP: false });
      continue;
    }
    if (!types.size) continue;
    const rules = data.reactions ?? [];
    const change = rules.find(r => r.to && matchesTypes(r, types) && ruleAllows(r, data));
    if (change) {
      const target = indexOfId(data, change.to);
      if (target !== -1) {
        // Ir para um estado quebrado (ex.: gelo estilhaçado) zera a vida.
        await setState(token, target, { syncHP: !!data.states[target].broken });
        if (change.say) await say(token, change.say);
      }
    }
    for (const r of rules.filter(r => r.effect && matchesTypes(r, types))) await applyEffect(r, token, actor, types, attacker);
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
  const speaker = message.speaker;
  const attacker = speaker?.token ? game.scenes.get(speaker.scene)?.tokens.get(speaker.token) : null;
  for (const t of targets) {
    const actor = fromUuidSync(t.uuid);
    const token = actor?.token ?? actor?.getActiveTokens(false, true)[0];
    const data = getData(token);
    if (!data || !isDamageable(data) || !actor?.system?.attributes?.hp) continue;
    if (attacker) recentAttacker.set(actor.uuid, { token: attacker, at: Date.now() });
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
