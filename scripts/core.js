import { buildMap, rebuildWalls } from "./mapa.js";
import * as agua from "./agua.js";
import * as veiculo from "./veiculo.js";
import * as template from "./template.js";

const MODULE_ID = "interactive-assets";
/** Pasta dos assets: local (modules/...) ou, no modo desenvolvimento, o commit mais recente no GitHub. */
let BASE = `modules/${MODULE_ID}/assets`;
let REGISTRY = {};
let started = false;

/**
 * Estados guardados no documento (Tile ou Token):
 * flags.interactive-assets.data = { asset, states: [{id,name,src,broken?}], index }
 * Assets com "actor" no assets.json viram Tokens; com "hp" eles têm PV/CA (dnd5e) e quebram ao chegar a 0 PV.
 * Cada estado pode trazer "light" (luz do token) e "sound" (som ambiente que acompanha o token).
 * "reactions": regras por tipo de dano (troca de estado, perda de PV máximo, empurrão).
 * "onZero": qual estado quebrado usar quando a vida chega a 0 (pelo estado atual ou pelo tipo do golpe).
 * Estados com "dot" causam dano a cada "tique" (nova rodada em combate, ou a cada tickSeconds fora dele);
 * "ticks" limita a duração e "then" diz para qual estado voltar ao fim.
 * "player": o que jogadores podem fazer. "move" deixa mover o token; "toggle" lista os estados
 * que eles alternam pelo HUD (ex.: acender/apagar a tocha). O resto (vida, imagem, estados) é só do GM ou do dano.
 * "tipo" (movel | imovel) e "interacao" (jogador | mestre | armadilha) escolhem a pasta do ator no Foundry.
 * Água (scripts/agua.js) e veículos (scripts/veiculo.js) usam o mesmo esquema, com campos próprios.
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

/** Campos que mudam ao entrar no estado i (imagem, índice, duração e luz). */
function stateUpdate(doc, i) {
  const data = getData(doc);
  const update = {
    "texture.src": data.states[i].src,
    [`flags.${MODULE_ID}.data.index`]: i,
    [`flags.${MODULE_ID}.data.ticksLeft`]: data.states[i].ticks ?? null
  };
  if (doc.documentName === "Token" && data.states.some(s => s.light)) update.light = lightFor(data.states[i]);
  return update;
}

async function setState(doc, index, { syncHP = true, interact = false } = {}) {
  const data = getData(doc);
  if (!data?.states?.length) return;
  const i = ((index % data.states.length) + data.states.length) % data.states.length;
  await doc.update(stateUpdate(doc, i), interact ? { [MODULE_ID]: { interact: true } } : {});
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
  for (const key of ["reactions", "onZero", "tickSeconds", "player", "vehicle"]) if (def[key] != null) data[key] = def[key];
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

/** Posição salva do token. No Foundry v13, token.x/y anda junto com a animação; _source já tem o destino. */
const posOf = token => token._source ?? token;

function tokenCenter(token) {
  const g = token.parent.grid.size;
  const { x, y } = posOf(token);
  return { x: x + (token.width * g) / 2, y: y + (token.height * g) / 2 };
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

/* ---------- Pastas ---------- */

/**
 * Pastas de atores no Foundry: Interactive Assets / Móveis|Imóveis / Jogador|Mestre|Armadilhas.
 * Cada asset diz a sua em "tipo" (movel | imovel) e "interacao" (jogador | mestre | armadilha).
 */
const FOLDER_TIPOS = { movel: "Móveis", imovel: "Imóveis" };
const FOLDER_INTERACOES = { jogador: "Jogador", mestre: "Mestre", armadilha: "Armadilhas" };

async function rootFolder() {
  let folder = game.folders.find(f => f.type === "Actor" && f.getFlag(MODULE_ID, "root"));
  folder ??= await Folder.create({ name: "Interactive Assets", type: "Actor", flags: { [MODULE_ID]: { root: true } } });
  return folder;
}

/** Subpasta marcada com a flag "folder" (= key) dentro de parent; cria se não existir. */
async function childFolder(parent, key, name) {
  let folder = game.folders.find(f => f.type === "Actor" && f.getFlag(MODULE_ID, "folder") === key);
  folder ??= await Folder.create({ name, type: "Actor", folder: parent.id, sorting: "a", flags: { [MODULE_ID]: { folder: key } } });
  return folder;
}

/** Cria a árvore inteira (mesmo pastas ainda vazias), para a estrutura ficar visível. */
async function ensureFolders() {
  const root = await rootFolder();
  for (const [tipo, tipoName] of Object.entries(FOLDER_TIPOS)) {
    const parent = await childFolder(root, tipo, tipoName);
    for (const [interacao, name] of Object.entries(FOLDER_INTERACOES)) await childFolder(parent, `${tipo}/${interacao}`, name);
  }
}

/** Pasta do asset pelo "tipo"/"interacao" do assets.json (sem eles, fica na raiz). */
async function assetFolder(def) {
  const root = await rootFolder();
  if (!FOLDER_TIPOS[def.tipo]) return root;
  const parent = await childFolder(root, def.tipo, FOLDER_TIPOS[def.tipo]);
  if (!FOLDER_INTERACOES[def.interacao]) return parent;
  return childFolder(parent, `${def.tipo}/${def.interacao}`, FOLDER_INTERACOES[def.interacao]);
}

/**
 * No dnd5e 5.x (Foundry v13), todo NPC conta como criatura e bloqueia o movimento de quem não é do mesmo lado.
 * Os assets ganham este status (incluído em CONFIG.DND5E.neverBlockStatuses): não bloqueiam ninguém e
 * também não são bloqueados (o barco entra na água, o personagem sobe na carroça).
 */
const OBJECT_STATUS = "interactiveAssetObject";
const objectEffect = () => ({
  name: "Objeto (não bloqueia movimento)",
  // Sem imagem: o Foundry não desenha o ícone no token (com 75 quadrados de água, os ícones derrubavam o FPS).
  img: null,
  statuses: [OBJECT_STATUS],
  flags: { [MODULE_ID]: { object: true } }
});

/**
 * Assets não mostram a dica de altitude do token. Cada dica é uma textura de texto separada, o que quebra o
 * desenho em lotes do canvas: num mapa com dezenas de assets isso dobrava o número de desenhos por frame.
 */
Hooks.on("refreshToken", token => {
  if (token.tooltip && getData(token.document)) token.tooltip.visible = false;
});

/** Asset sem vida (água, tocha) não fica "Bloodied": o dnd5e lê 0 de 0 PV como metade da vida. */
Hooks.on("preCreateActiveEffect", effect => {
  const actor = effect.parent;
  if (!(actor instanceof Actor) || !effect.statuses?.has("bloodied")) return;
  const data = getData(actor.token) ?? getData(actor.prototypeToken);
  if (data && !isDamageable(data)) return false;
});

const playerOwnership = def => def.player?.move || def.player?.toggle?.length
  ? CONST.DOCUMENT_OWNERSHIP_LEVELS.OWNER
  : CONST.DOCUMENT_OWNERSHIP_LEVELS.NONE;

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
    const objEffect = actor.effects.find(e => e.statuses?.has(OBJECT_STATUS));
    if (!objEffect) await actor.createEmbeddedDocuments("ActiveEffect", [objectEffect()]);
    else if (objEffect.img) await objEffect.update({ img: null });
    // Jogadores donos do ator podem mover o token (o resto é bloqueado em preUpdate*).
    const ownership = playerOwnership(def);
    if (actor.ownership.default !== ownership) await actor.update({ "ownership.default": ownership });
    // Asset mudou de categoria no assets.json → muda de pasta.
    const folder = await assetFolder(def);
    if (actor.folder?.id !== folder.id) await actor.update({ folder: folder.id });
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
  const folder = await assetFolder(def);
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
    ownership: { default: playerOwnership(def) },
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
    effects: [objectEffect()],
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

/* ---------- NPC de teste ---------- */

const DAMAGE_TYPES = {
  acid: "Ácido", bludgeoning: "Concussão", cold: "Gelo", fire: "Fogo", force: "Força", lightning: "Raio",
  necrotic: "Necrótico", piercing: "Perfurante", poison: "Veneno", psychic: "Psíquico", radiant: "Radiante",
  slashing: "Cortante", thunder: "Trovão"
};

function testAttack(type, label) {
  const id = foundry.utils.randomID(16);
  return {
    name: `${label} (1)`,
    type: "feat",
    img: "icons/svg/explosion.svg",
    system: {
      type: { value: "monster" },
      description: { value: `<p>Causa 1 de dano ${label.toLowerCase()}. Para testar os assets interativos.</p>` },
      activities: {
        [id]: {
          _id: id,
          type: "attack",
          activation: { type: "action" },
          attack: { ability: "none", bonus: "100", flat: true, type: { value: "ranged", classification: "spell" } },
          range: { value: "120", units: "ft" },
          target: { affects: { count: "1", type: "creature" } },
          damage: { includeBase: false, parts: [{ custom: { enabled: true, formula: "1" }, types: [type] }] }
        }
      }
    },
    flags: { [MODULE_ID]: { testDamage: type } }
  };
}

/** Cria (ou completa) o NPC "Testador de Dano": um ataque à distância que sempre acerta, de 1 de dano por tipo. */
async function ensureTestActor() {
  if (game.system.id !== "dnd5e" || !game.settings.get(MODULE_ID, "testActor")) return;
  const folder = await rootFolder();
  let actor = game.actors.find(a => a.getFlag(MODULE_ID, "testActor"));
  actor ??= await Actor.create({
    name: "Testador de Dano",
    type: "npc",
    img: "icons/svg/mystery-man.svg",
    folder: folder.id,
    system: { attributes: { hp: { value: 100, max: 100 } }, details: { cr: 0 } },
    prototypeToken: { name: "Testador de Dano", disposition: CONST.TOKEN_DISPOSITIONS.FRIENDLY },
    flags: { [MODULE_ID]: { testActor: true } }
  });
  const have = new Set(actor.items.map(i => i.getFlag(MODULE_ID, "testDamage")).filter(Boolean));
  const missing = Object.entries(DAMAGE_TYPES).filter(([t]) => !have.has(t)).map(([t, l]) => testAttack(t, l));
  if (missing.length) await actor.createEmbeddedDocuments("Item", missing);
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
  const x = clamp(posOf(token).x + dx * g * squares, 0, token.parent.dimensions.width - token.width * g);
  const y = clamp(posOf(token).y + dy * g * squares, 0, token.parent.dimensions.height - token.height * g);
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
    return state && (state.dot || state.areaDot || state.ticks) && t.actor && data.ticksLeft !== 0;
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
  // "areaDot": o dano é em quem está dentro (ex.: água envenenada), não no próprio asset.
  if (state.areaDot) await agua.damageOccupants(token, state.areaDot.damage, state.areaDot.type);
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

/**
 * Chamado pelo carregador (scripts/main.js) no "ready", depois de importar este arquivo
 * da pasta do módulo ou do GitHub. Registra configurações, a API e prepara os atores.
 */
export async function start({ base, version }) {
  BASE = base;
  game.settings.register(MODULE_ID, "autoDamage", {
    name: "Aplicar dano automaticamente em assets",
    hint: "Quando uma rolagem de dano do dnd5e tem um asset como alvo, o dano é aplicado sozinho (sem clicar em aplicar no chat).",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });
  game.settings.register(MODULE_ID, "testActor", {
    name: "Criar NPC de teste",
    hint: "Cria o NPC \"Testador de Dano\" (pasta Interactive Assets), com um ataque de 1 de dano para cada tipo.",
    scope: "world",
    config: true,
    type: Boolean,
    default: true
  });
  CONFIG.DND5E?.neverBlockStatuses?.add?.(OBJECT_STATUS);
  const ctx = { registry: () => REGISTRY, getData, posOf, currentState, ruleAllows, matchesTypes, indexOfId, stateUpdate, setState, say, tokenCenter, isResponsibleGM, MODULE_ID };
  agua.init(ctx);
  veiculo.init(ctx);
  template.init();
  game.modules.get(MODULE_ID).api = {
    placeAsset, nextState, setState, buildMap, rebuildWalls,
    /** De onde o código veio: commit do GitHub (modo desenvolvimento) ou a pasta instalada. A macro dos mapas usa isso. */
    root: base.replace(/\/assets$/, ""),
    get assets() { return REGISTRY; }
  };

  try {
    REGISTRY = await (await fetch(`${BASE}/assets.json?v=${version}`, { cache: "no-cache" })).json();
    console.log(`${MODULE_ID} | ${Object.keys(REGISTRY).length} asset(s) carregado(s)`);
    // O canvas pode ter sido desenhado antes do assets.json chegar (estado "oculto" da água).
    for (const t of canvas.tokens?.placeables ?? []) if (getData(t.document)) t.renderFlags.set({ refreshVisibility: true });
    if (isResponsibleGM()) {
      await ensureFolders();
      // Garante um ator por asset na pasta da sua categoria, pronto para arrastar para a cena.
      for (const [id, def] of Object.entries(REGISTRY)) {
        if (def.actor) await getBaseActor(id, def);
        await refreshPlaced(id, def);
      }
      startTickTimer();
      await ensureTestActor().catch(err => console.error(`${MODULE_ID} | falha ao criar o NPC de teste`, err));
    }
  } catch (err) {
    console.error(`${MODULE_ID} | falha ao carregar assets.json`, err);
  }
  started = true;
}

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
  if (!started || !isResponsibleGM() || options?.[MODULE_ID]?.fromState) return;
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
    if (types.size) await react(token, actor, types, attacker);
  }
});

/**
 * Aplica as "reactions" do asset para os tipos de dano recebidos.
 * "below": a regra só vale com a vida nessa fração ou menos (ex.: 0.5 = metade).
 * Depois da troca, água e veículos podem completar (espalhar pelo lago, choque em quem está na água).
 */
async function react(token, actor, types, attacker) {
  const data = getData(token);
  const rules = data.reactions ?? [];
  const hp = actor?.system?.attributes?.hp;
  const frac = hp?.max ? hp.value / hp.max : 1;
  const change = rules.find(r => r.to && matchesTypes(r, types) && ruleAllows(r, data) && (r.below == null || frac <= r.below));
  if (change) {
    const target = indexOfId(data, change.to);
    if (target !== -1) {
      // Ir para um estado quebrado (ex.: gelo estilhaçado) zera a vida.
      await setState(token, target, { syncHP: !!data.states[target].broken });
      if (change.say) await say(token, change.say);
      await agua.afterReaction(token, change, types);
    }
  }
  if (actor?.system?.attributes?.hp) {
    for (const r of rules.filter(r => r.effect && matchesTypes(r, types))) await applyEffect(r, token, actor, types, attacker);
  }
}

/** Rolagem de dano do dnd5e com um asset como alvo → aplica o dano nele. */
Hooks.on("createChatMessage", async message => {
  if (!started || !isResponsibleGM() || !game.settings.get(MODULE_ID, "autoDamage")) return;
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
    if (!data) continue;
    // Sem vida (água, tocha): não leva dano, só reage ao tipo do golpe.
    if (!isDamageable(data)) {
      const types = new Map();
      for (const d of damages) if (d.value > 0 && d.type) types.set(d.type, (types.get(d.type) ?? 0) + d.value);
      if (types.size && data.reactions) await react(token, actor, types, attacker);
      continue;
    }
    if (!actor?.system?.attributes?.hp) continue;
    if (attacker) recentAttacker.set(actor.uuid, { token: attacker, at: Date.now() });
    await actor.applyDamage(damages);
  }
});

/**
 * Botão de troca de estado no HUD (Tile e Token). Funciona em v12 (jQuery) e v13 (HTMLElement).
 * GM: passa por todos os estados. Jogador: só alterna entre os estados de "player.toggle".
 */
function addHudButton(hud, html) {
  const doc = hud.object?.document;
  const data = getData(doc);
  if (!data?.states?.length) return;
  const current = currentState(data);
  let nextIndex;
  if (game.user.isGM) nextIndex = ((data.index ?? 0) + 1) % data.states.length;
  else {
    const toggle = data.player?.toggle ?? [];
    const at = toggle.indexOf(current?.id);
    if (at === -1) return;
    nextIndex = indexOfId(data, toggle[(at + 1) % toggle.length]);
    if (nextIndex === -1) return;
  }
  const root = html instanceof HTMLElement ? html : html[0];
  const col = root.querySelector(".col.right") ?? root;
  const next = data.states[nextIndex];

  const btn = document.createElement("div");
  btn.className = "control-icon ia-state";
  btn.dataset.tooltip = `Mudar para: ${next.name}`;
  btn.innerHTML = `<i class="fas fa-repeat"></i><span class="ia-label">${current.name}</span>`;
  btn.addEventListener("click", async ev => {
    ev.preventDefault();
    if (game.user.isGM) await nextState(doc);
    else await setState(doc, nextIndex, { syncHP: false, interact: true });
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

/* ---------- O que jogadores podem mudar ---------- */

/** Jogador acabou de aplicar dano neste ator (cálculo do dnd5e no próprio cliente)? */
const legitDamage = actor => {
  const hit = recentDamage.get(actor.uuid);
  return hit && Date.now() - hit.at < 3000;
};

/** Ator de asset: o base (flag "asset") ou o sintético de um token de asset. */
const isAssetActor = actor => actor?.getFlag(MODULE_ID, "asset") || getData(actor?.token);

Hooks.on("preUpdateActor", (actor, changes) => {
  if (game.user.isGM || !isAssetActor(actor) || legitDamage(actor)) return;
  ui.notifications.warn(`${actor.name}: só o GM ou dano em combate podem mudar este asset.`);
  return false;
});
Hooks.on("preDeleteActor", actor => {
  if (game.user.isGM || !isAssetActor(actor)) return;
  ui.notifications.warn(`${actor.name}: só o GM pode apagar este asset.`);
  return false;
});
Hooks.on("preUpdateToken", (token, changes, options) => {
  if (game.user.isGM || !getData(token)) return;
  const state = "texture" in changes || "light" in changes || foundry.utils.hasProperty(changes, `flags.${MODULE_ID}`);
  if (state && !options[MODULE_ID]?.interact) {
    ui.notifications.warn(`${token.name}: jogadores só podem mover este asset.`);
    return false;
  }
  if (!getData(token).player?.move && ["x", "y", "rotation"].some(k => k in changes)) {
    ui.notifications.warn(`${token.name}: jogadores não podem mover este asset.`);
    return false;
  }
  if ("delta" in changes && !(token.actor && legitDamage(token.actor))) {
    ui.notifications.warn(`${token.name}: só o GM ou dano em combate podem mudar este asset.`);
    return false;
  }
});
