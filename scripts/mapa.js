/**
 * Mapas com construção quebrável.
 *
 * A cena guarda o layout em flags.interactive-assets.map = { cols, rows, fixed: ["x,y", ...] }
 * ("fixed" = quadrados que bloqueiam e nunca quebram, como a lareira). Paredes, portas e pilares
 * quebráveis são Tokens de asset com flags.interactive-assets.cell = { x, y, kind, dir }
 * (kind: "wall" | "door" | "pillar"; dir da porta: "h" se a parede corre na horizontal, "v" na vertical).
 *
 * As paredes do Foundry são recalculadas a partir do que está de pé: um bloco de parede quebrado
 * (estado com "broken") vira chão, e as paredes do Foundry se fecham em volta do buraco.
 * Estados de porta com "door": "open" | "closed" seguem a porta do Foundry (e vice-versa).
 * Estados com "sfx" tocam um som ao entrar neles.
 */
import { groundFn } from "./relevo.js";

const MODULE_ID = "interactive-assets";
/** Quanto a parede do Foundry fica recuada para dentro do bloco (fração do quadrado).
 * Assim o centro do token de parede fica visível para os jogadores e eles conseguem mirar nele. */
const INSET = 0.3;
const PILLAR_R = 0.3;

const key = (x, y) => `${x},${y}`;
const getData = doc => doc?.getFlag(MODULE_ID, "data") ?? null;
const stateOf = doc => {
  const d = getData(doc);
  return d?.states?.[d.index ?? 0] ?? null;
};
const isResponsibleGM = () => game.user.isGM && (game.users.activeGM ? game.users.activeGM.isSelf : true);

/**
 * Calcula as paredes (em quadrados) para o que está de pé. Função pura, sem Foundry.
 * solid: Set de "x,y" que bloqueiam; doors: [{x,y,dir,key}]; pillars: [{x,y}].
 * Devolve [{ c: [x1,y1,x2,y2], door?: "x,y" }].
 */
export function computeWalls({ cols, rows, solid, doors = [], pillars = [] }) {
  const d = INSET;
  const S = (x, y) => x >= 0 && y >= 0 && x < cols && y < rows && solid.has(key(x, y));
  const h = [], v = []; // faces horizontais [y, x1, x2] e verticais [x, y1, y2]
  for (let y = 0; y < rows; y++) for (let x = 0; x < cols; x++) {
    if (!S(x, y)) continue;
    const N = !S(x, y - 1), Sx = !S(x, y + 1), W = !S(x - 1, y), E = !S(x + 1, y);
    // Ponta de cada face: canto convexo recua, canto côncavo avança até encontrar a face vizinha.
    const end = (open, diag, base, sign) => open ? base + sign * d : diag ? base - sign * d : base;
    if (N) h.push([y + d, end(W, S(x - 1, y - 1), x, 1), end(E, S(x + 1, y - 1), x + 1, -1)]);
    if (Sx) h.push([y + 1 - d, end(W, S(x - 1, y + 1), x, 1), end(E, S(x + 1, y + 1), x + 1, -1)]);
    if (W) v.push([x + d, end(N, S(x - 1, y - 1), y, 1), end(Sx, S(x - 1, y + 1), y + 1, -1)]);
    if (E) v.push([x + 1 - d, end(N, S(x + 1, y - 1), y, 1), end(Sx, S(x + 1, y + 1), y + 1, -1)]);
  }
  const merge = list => {
    const out = [];
    const by = new Map();
    for (const [line, a, b] of list) (by.get(line) ?? by.set(line, []).get(line)).push([a, b]);
    for (const [line, segs] of by) {
      segs.sort((p, q) => p[0] - q[0]);
      let [a, b] = segs[0];
      for (const [s, e] of segs.slice(1)) {
        if (Math.abs(s - b) < 1e-6) b = Math.max(b, e);
        else { out.push([line, a, b]); [a, b] = [s, e]; }
      }
      out.push([line, a, b]);
    }
    return out;
  };
  const walls = [
    ...merge(h).map(([y, a, b]) => ({ c: [a, y, b, y] })),
    ...merge(v).map(([x, a, b]) => ({ c: [x, a, x, b] }))
  ];
  for (const dr of doors) {
    const { x, y } = dr;
    // A porta vai de batente a batente: entra no bloco vizinho só se ele estiver de pé.
    if (dr.dir === "v") walls.push({ c: [x + .5, S(x, y - 1) ? y - d : y, x + .5, S(x, y + 1) ? y + 1 + d : y + 1], door: key(x, y) });
    else walls.push({ c: [S(x - 1, y) ? x - d : x, y + .5, S(x + 1, y) ? x + 1 + d : x + 1, y + .5], door: key(x, y) });
  }
  for (const { x, y } of pillars) {
    const pts = Array.from({ length: 8 }, (_, i) => {
      const a = Math.PI / 8 + i * Math.PI / 4;
      return [x + .5 + PILLAR_R * Math.cos(a), y + .5 + PILLAR_R * Math.sin(a)];
    });
    pts.forEach((p, i) => walls.push({ c: [...p, ...pts[(i + 1) % 8]] }));
  }
  return walls;
}

/** O que está de pé agora na cena. */
function standing(scene) {
  const map = scene.getFlag(MODULE_ID, "map");
  if (!map) return null;
  const solid = new Set(map.fixed ?? []);
  const doors = [], pillars = [];
  for (const t of scene.tokens) {
    const cell = t.getFlag(MODULE_ID, "cell");
    if (!cell || stateOf(t)?.broken) continue;
    if (cell.kind === "wall") solid.add(key(cell.x, cell.y));
    else if (cell.kind === "door") doors.push(cell);
    else if (cell.kind === "pillar") pillars.push(cell);
  }
  return { cols: map.cols, rows: map.rows, solid, doors, pillars };
}

const wallKey = w => `${w.c.map(Math.round).join(",")}|${w.door ?? ""}`;

/** Refaz as paredes do Foundry da cena: só cria/apaga o que mudou e mantém portas abertas abertas. */
const queues = new Map();
export function rebuildWalls(scene) {
  // Uma reconstrução por vez em cada cena (uma bola de fogo pode derrubar vários blocos de uma vez).
  const next = (queues.get(scene.id) ?? Promise.resolve()).then(() => doRebuild(scene)).catch(e => console.error(`${MODULE_ID} | paredes`, e));
  queues.set(scene.id, next);
  return next;
}

async function doRebuild(scene) {
  const st = standing(scene);
  if (!st) return;
  const g = scene.grid.size;
  const want = computeWalls(st).map(w => ({ ...w, c: w.c.map(n => Math.round(n * g)) }));
  const existing = scene.walls.filter(w => w.getFlag(MODULE_ID, "generated"));
  const have = new Map(existing.map(w => [wallKey({ c: w.c, door: w.getFlag(MODULE_ID, "door") }), w]));
  const doorState = new Map(existing.filter(w => w.door).map(w => [w.getFlag(MODULE_ID, "door"), w.ds]));
  const wantKeys = new Set(want.map(wallKey));
  const remove = existing.filter(w => !wantKeys.has(wallKey({ c: w.c, door: w.getFlag(MODULE_ID, "door") }))).map(w => w.id);
  const create = want.filter(w => !have.has(wallKey(w))).map(w => ({
    c: w.c,
    ...(w.door ? { door: CONST.WALL_DOOR_TYPES.DOOR, ds: doorState.get(w.door) ?? doorStateFromToken(scene, w.door), doorSound: "woodBasic" } : {}),
    flags: { [MODULE_ID]: { generated: true, ...(w.door ? { door: w.door } : {}) } }
  }));
  if (remove.length) await scene.deleteEmbeddedDocuments("Wall", remove);
  if (create.length) await scene.createEmbeddedDocuments("Wall", create);
}

function cellToken(scene, cellKey, kind) {
  return scene.tokens.find(t => {
    const c = t.getFlag(MODULE_ID, "cell");
    return c && c.kind === kind && key(c.x, c.y) === cellKey;
  });
}

function doorStateFromToken(scene, cellKey) {
  const t = cellToken(scene, cellKey, "door");
  return stateOf(t)?.door === "open" ? CONST.WALL_DOOR_STATES.OPEN : CONST.WALL_DOOR_STATES.CLOSED;
}

/** Caminho completo de um som do assets.json, usando a mesma pasta das imagens do asset. */
function assetPath(token, rel) {
  const data = getData(token);
  const def = game.modules.get(MODULE_ID).api?.assets?.[data?.asset];
  const abs = data?.states?.[0]?.src, local = def?.states?.[0]?.src;
  if (!abs || !local || !abs.endsWith(local)) return rel;
  return abs.slice(0, abs.length - local.length) + rel;
}

/* ---------- Ganchos ---------- */

/** Guarda o estado anterior para saber, depois, se ele mudou de verdade. */
Hooks.on("preUpdateToken", (token, changes, options) => {
  if (foundry.utils.hasProperty(changes, `flags.${MODULE_ID}.data.index`)) options[`${MODULE_ID}Prev`] = getData(token)?.index ?? 0;
});

Hooks.on("updateToken", async (token, changes, options) => {
  if (!isResponsibleGM() || !foundry.utils.hasProperty(changes, `flags.${MODULE_ID}.data.index`)) return;
  if (options?.[`${MODULE_ID}Prev`] === (getData(token)?.index ?? 0)) return; // estado não mudou
  const state = stateOf(token);
  if (state?.sfx) {
    const AH = foundry.audio?.AudioHelper ?? AudioHelper;
    AH.play({ src: assetPath(token, state.sfx), volume: 0.8, autoplay: true, loop: false }, true);
  }
  const cell = token.getFlag(MODULE_ID, "cell");
  if (!cell) return;
  await rebuildWalls(token.parent);
  // Porta trocada pelo HUD (aberta/fechada) → abre/fecha a porta do Foundry.
  if (cell.kind === "door" && state?.door) {
    const wall = token.parent.walls.find(w => w.getFlag(MODULE_ID, "door") === key(cell.x, cell.y));
    const ds = state.door === "open" ? CONST.WALL_DOOR_STATES.OPEN : CONST.WALL_DOOR_STATES.CLOSED;
    if (wall && wall.ds !== ds && wall.ds !== CONST.WALL_DOOR_STATES.LOCKED) await wall.update({ ds });
  }
});

Hooks.on("deleteToken", token => {
  if (isResponsibleGM() && token.getFlag(MODULE_ID, "cell") && token.parent) rebuildWalls(token.parent);
});

/** Abriram/fecharam a porta do Foundry → troca a imagem do token da porta. */
Hooks.on("updateWall", async (wall, changes) => {
  if (!isResponsibleGM() || !("ds" in changes)) return;
  const cellKey = wall.getFlag(MODULE_ID, "door");
  if (!cellKey) return;
  const token = cellToken(wall.parent, cellKey, "door");
  const data = getData(token);
  if (!data || stateOf(token)?.door == null) return; // quebrada ou pegando fogo: a imagem não muda
  const want = changes.ds === CONST.WALL_DOOR_STATES.OPEN ? "open" : "closed";
  if (stateOf(token).door === want) return;
  const i = data.states.findIndex(s => s.door === want);
  if (i !== -1) await game.modules.get(MODULE_ID).api.setState(token, i, { syncHP: false });
});

/* ---------- Montar uma cena ---------- */

/**
 * Cria a cena de um mapa (cena.json gerado por tools/gen_mapa.py) com as estruturas e objetos.
 * root: endereço base dos arquivos do mapa (fundo e sons).
 */
export async function buildMap(data, root) {
  const api = game.modules.get(MODULE_ID).api;
  const map = data.flags?.[MODULE_ID]?.map;
  const sceneData = foundry.utils.deepClone(data);
  sceneData.background.src = `${root}/${data.background.src}`;
  for (const s of sceneData.sounds ?? []) s.path = `${root}/${s.path}`;
  delete sceneData.flags[MODULE_ID].map.structures;
  delete sceneData.flags[MODULE_ID].map.objects;
  delete sceneData.regions; // criadas depois, com o comportamento de terreno difícil que o sistema tiver
  const scene = await Scene.create(sceneData);
  const g = scene.grid.size;

  const actorFor = asset => game.actors.find(a => a.getFlag(MODULE_ID, "asset") === asset);
  const missing = new Set();
  const tokens = [];
  for (const s of map.structures ?? []) {
    const actor = actorFor(s.asset);
    if (!actor) { missing.add(s.asset); continue; }
    const td = await actor.getTokenDocument({
      x: s.x * g, y: s.y * g, rotation: s.rotation ?? 0, locked: true,
      displayName: CONST.TOKEN_DISPLAY_MODES.OWNER_HOVER,
      flags: { [MODULE_ID]: { cell: { x: s.x, y: s.y, kind: s.kind, ...(s.dir ? { dir: s.dir } : {}) } } }
    });
    tokens.push(td.toObject());
  }
  // Objetos: "hidden" (armadilhas escondidas), "flags" extras (ligações de armadilha, destino do pedregulho)
  // e a altura do chão onde ficam (mapas com relevo).
  const ground = groundFn(scene);
  for (const o of map.objects ?? []) {
    const actor = actorFor(o.asset);
    const def = api.assets[o.asset];
    if (!actor || !def) { missing.add(o.asset); continue; }
    const td = await actor.getTokenDocument({
      x: Math.round(o.x - def.size.w * g / 2), y: Math.round(o.y - def.size.h * g / 2),
      elevation: ground(Math.floor(o.x / g), Math.floor(o.y / g)),
      ...(o.hidden ? { hidden: true } : {}),
      ...(o.flags ? { flags: { [MODULE_ID]: o.flags } } : {})
    });
    tokens.push(td.toObject());
  }
  if (tokens.length) await scene.createEmbeddedDocuments("Token", tokens);
  await createRegions(scene, data.regions ?? []);
  await rebuildWalls(scene);
  if (missing.size) ui.notifications.warn(`Assets não encontrados: ${[...missing].join(", ")}. Recarregue a página (F5) e rode de novo.`);
  await scene.view();
  return scene;
}

/**
 * Regiões de terreno difícil (flags.interactive-assets.terreno = tipo do dnd5e: "slope", "plants", "rocks"...).
 * Usa o terreno difícil do dnd5e; sem ele, o custo de movimento dobrado do próprio Foundry.
 */
async function createRegions(scene, regions) {
  if (!regions.length) return;
  const dnd = CONFIG.RegionBehavior?.dataModels?.["dnd5e.difficultTerrain"];
  const behavior = type => dnd
    ? { type: "dnd5e.difficultTerrain", system: { types: type ? [type] : [] } }
    : { type: "modifyMovementCost", system: { difficulties: { walk: 2, swim: 2, burrow: 2, fly: 1 } } };
  const docs = regions.map(r => ({ ...r, behaviors: [behavior(r.flags?.[MODULE_ID]?.terreno)] }));
  try {
    await scene.createEmbeddedDocuments("Region", docs);
  } catch (e) {
    console.error(`${MODULE_ID} | regiões de terreno difícil`, e);
    ui.notifications.warn("Mapa: não deu para criar as regiões de terreno difícil (veja o console).");
  }
}
