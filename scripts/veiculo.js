/**
 * Veículos (carroça, barco): assets com "vehicle" no assets.json.
 * - Quem está em cima (centro do token dentro do veículo) anda junto quando o veículo se move: criaturas e objetos.
 * - "vehicle.terreno": "agua" só navega em água livre (presa no gelo); "terra" não entra na água (mas passa sobre o gelo).
 * - Estados com "travado": true não deixam os jogadores mover o veículo (roda quebrada, afundado...).
 * O GM pode mover para qualquer lugar.
 */
import { rectOf, vehicleUnder, waterCells, waterStateAt } from "./agua.js";

const MODULE_ID = "interactive-assets";
let C = null;

/** Última posição conhecida de cada token (o GM precisa dela para saber de onde o veículo saiu). */
const lastPos = new Map();
/** Tokens movidos agora há pouco por conta própria (arrastados junto com o veículo, por exemplo). */
const movedAt = new Map();

export function init(ctx) {
  C = ctx;
  if (!C.isResponsibleGM()) return;
  for (const scene of game.scenes) for (const t of scene.tokens) lastPos.set(t.uuid, { ...pos(t) });
}

const vehicleOf = t => C.getData(t)?.vehicle ?? null;
/** Posição salva (no v13, token.x/y é a posição animada). */
const pos = t => ({ x: t._source?.x ?? t.x, y: t._source?.y ?? t.y });
const inside = (p, r) => p.x > r.x && p.x < r.x + r.w && p.y > r.y && p.y < r.y + r.h;
const centerAt = (t, pos) => {
  const g = t.parent.grid.size;
  return { x: pos.x + (t.width * g) / 2, y: pos.y + (t.height * g) / 2 };
};

/** Por que o veículo não pode ir para pos (ou null se pode). */
function blocked(token, pos) {
  const v = vehicleOf(token);
  const scene = token.parent;
  const g = scene.grid.size;
  const r = rectOf(token, pos);
  const cells = waterCells(scene);
  const states = [];
  // Cada quadrado coberto pelo veículo (com uma folga, para não contar o vizinho por arredondamento).
  for (let y = Math.floor((r.y + 1) / g); y <= Math.floor((r.y + r.h - 1) / g); y++)
    for (let x = Math.floor((r.x + 1) / g); x <= Math.floor((r.x + r.w - 1) / g); x++)
      states.push(waterStateAt(scene, (x + .5) * g, (y + .5) * g, cells));
  if (v.terreno === "agua") {
    if (states.some(s => s?.gelo)) return `${token.name} está preso no gelo.`;
    if (states.some(s => !s?.wet)) return `${token.name} só navega na água.`;
  } else if (v.terreno === "terra") {
    if (states.some(s => s?.wet)) return `${token.name} não entra na água (só passa por cima do gelo).`;
  }
  return null;
}

/** Jogadores: veículo travado não anda, e cada veículo fica no seu terreno. */
Hooks.on("preUpdateToken", (token, changes) => {
  if (!C || game.user.isGM || !vehicleOf(token) || !("x" in changes || "y" in changes)) return;
  const state = C.currentState(C.getData(token));
  if (state?.travado) {
    ui.notifications.warn(`${token.name}: ${state.name.toLowerCase()}, não dá para mover.`);
    return false;
  }
  const why = blocked(token, { x: changes.x ?? pos(token).x, y: changes.y ?? pos(token).y });
  if (why) {
    ui.notifications.warn(why);
    return false;
  }
});

/** Quem estava em cima do veículo na posição antiga (e não se moveu sozinho agora). */
function passengersAt(vehicle, from) {
  const r = rectOf(vehicle, from);
  const now = Date.now();
  return vehicle.parent.tokens.filter(t => t.id !== vehicle.id && !t.getFlag(MODULE_ID, "cell") && !vehicleOf(t)
    && now - (movedAt.get(t.uuid) ?? 0) > 1000 && inside(C.tokenCenter(t), r));
}

Hooks.on("updateToken", async (token, changes, options) => {
  if (!C?.isResponsibleGM() || !("x" in changes || "y" in changes)) return;
  const from = lastPos.get(token.uuid);
  const to = pos(token);
  lastPos.set(token.uuid, to);
  if (options?.[MODULE_ID]?.carried) return;
  movedAt.set(token.uuid, Date.now());

  if (vehicleOf(token)) {
    if (!from) return;
    const dx = to.x - from.x, dy = to.y - from.y;
    if (!dx && !dy) return;
    movedAt.delete(token.uuid);
    // Espera os outros tokens do mesmo arrasto chegarem (se o jogador arrastou o veículo junto com alguém).
    await new Promise(r => setTimeout(r, 50));
    const riders = passengersAt(token, from);
    if (!riders.length) return;
    const moves = riders.map(t => ({ _id: t.id, x: pos(t).x + dx, y: pos(t).y + dy }));
    riders.forEach((t, i) => lastPos.set(t.uuid, { x: moves[i].x, y: moves[i].y }));
    await token.parent.updateEmbeddedDocuments("Token", moves,
      { [MODULE_ID]: { carried: true } });
    return;
  }

  // Criatura subindo ou descendo de um veículo: avisa no chat.
  if (!from || C.getData(token)) return;
  const before = token.parent.tokens.find(v => vehicleOf(v) && !C.currentState(C.getData(v))?.broken
    && inside(centerAt(token, from), rectOf(v)));
  const after = vehicleUnder(token);
  if (before?.id === after?.id) return;
  if (after) await C.say(token, `sobe em ${after.name}.`);
  else {
    const p = C.tokenCenter(token);
    const wet = waterStateAt(token.parent, p.x, p.y)?.wet;
    await C.say(token, wet ? `pula de ${before.name} na água.` : `desce de ${before.name}.`);
  }
});

Hooks.on("createToken", token => {
  if (C?.isResponsibleGM()) lastPos.set(token.uuid, pos(token));
});
Hooks.on("deleteToken", token => {
  lastPos.delete(token.uuid);
  movedAt.delete(token.uuid);
});
