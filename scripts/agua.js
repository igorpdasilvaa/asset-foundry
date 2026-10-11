/**
 * Água: cada quadrado de lago é um Token do asset "agua" com flags.interactive-assets.cell = { x, y, kind: "water" }
 * (montado pelo mapa, como as paredes). A água não tem vida: reage só ao tipo do golpe (scripts/core.js).
 *
 * Campos extras no assets.json:
 * - nas regras de "reactions": "spread": quantos quadrados a mudança se espalha pela água ligada ("all" = o lago todo);
 *   "zap": true faz quem está nos quadrados atingidos levar o mesmo dano de raio do golpe.
 * - nos estados: "wet" (água líquida: apaga o que entra pegando fogo e o barco navega), "gelo" (dá para andar por cima,
 *   o barco fica preso), "areaDot" (dano por tique em quem está dentro), "oculto" (o token não é desenhado:
 *   a água calma já está pintada no fundo do mapa, e 75 imagens a mais no canvas pesam no FPS).
 */
const MODULE_ID = "interactive-assets";
let C = null;

export function init(ctx) {
  C = ctx;
}

const key = (x, y) => `${x},${y}`;
const isCell = t => !!t.getFlag(MODULE_ID, "cell");
const isWater = t => t.getFlag(MODULE_ID, "cell")?.kind === "water";

/** Estado "oculto": esconde a imagem do token (ele continua lá para as regras e para o GM clicar). */
Hooks.on("refreshToken", token => {
  if (!C || !isWater(token.document) || !token.mesh) return;
  const data = C.getData(token.document);
  const state = C.currentState(data);
  // Lê também o assets.json atual: o token pode ter sido criado antes do campo existir.
  const live = C.registry()[data.asset]?.states?.find(s => s.id === state?.id);
  token.mesh.visible = token.visible && token.renderable && !(live ?? state)?.oculto;
  // Ícones de status (ex.: "Bloodied" do dnd5e) não fazem sentido na água e pesam no canvas.
  if (token.effects) token.effects.visible = false;
});
Hooks.on("updateToken", token => {
  if (isWater(token)) token.object?.renderFlags.set({ refreshVisibility: true });
});

/** Quadrados de água da cena: "x,y" → token. */
export function waterCells(scene) {
  const cells = new Map();
  for (const t of scene.tokens) {
    const c = t.getFlag(MODULE_ID, "cell");
    if (c?.kind === "water") cells.set(key(c.x, c.y), t);
  }
  return cells;
}

/** Estado da água no ponto (pixels da cena), ou null se não houver água ali. */
export function waterStateAt(scene, px, py, cells = waterCells(scene)) {
  const g = scene.grid.size;
  const t = cells.get(key(Math.floor(px / g), Math.floor(py / g)));
  return t ? C.currentState(C.getData(t)) : null;
}

/** Retângulo do token em pixels. */
export function rectOf(token, pos = token._source ?? token) {
  const g = token.parent.grid.size;
  return { x: pos.x, y: pos.y, w: token.width * g, h: token.height * g };
}

const inside = (p, r) => p.x > r.x && p.x < r.x + r.w && p.y > r.y && p.y < r.y + r.h;

/** Veículo (carroça, barco) de pé com o centro do token em cima dele. */
export function vehicleUnder(token) {
  const p = C.tokenCenter(token);
  return token.parent.tokens.find(v => {
    if (v.id === token.id) return false;
    const d = C.getData(v);
    return d?.vehicle && !C.currentState(d)?.broken && inside(p, rectOf(v));
  }) ?? null;
}

/** Criaturas (e objetos com vida) dentro dos quadrados dados, sem contar quem está a bordo de um veículo. */
function occupants(scene, cellKeys) {
  const g = scene.grid.size;
  return scene.tokens.filter(t => {
    if (isCell(t) || C.getData(t)?.vehicle || !t.actor?.system?.attributes?.hp) return false;
    const p = C.tokenCenter(t);
    return cellKeys.has(key(Math.floor(p.x / g), Math.floor(p.y / g))) && !vehicleUnder(t);
  });
}

async function hurt(tokens, value, type) {
  for (const t of tokens) await t.actor.applyDamage([{ value, type, properties: new Set() }]);
}

const LABEL = { lightning: "elétrico", poison: "de veneno", acid: "de ácido", fire: "de fogo", cold: "de frio" };

/** Dano em quem está no quadrado de água (usado pelos tiques de "areaDot"). */
export async function damageOccupants(cellToken, value, type) {
  const c = cellToken.getFlag(MODULE_ID, "cell");
  if (!c) return;
  const who = occupants(cellToken.parent, new Set([key(c.x, c.y)]));
  if (!who.length) return;
  await hurt(who, value, type);
  await C.say(cellToken, `causa ${value} de dano ${LABEL[type] ?? type} em ${who.map(t => t.name).join(", ")}.`);
}

/**
 * Espalha o estado de "rule.to" pela água ligada (4 vizinhos), até "rule.spread" quadrados de distância,
 * só por onde a regra vale (ex.: o raio não passa pelo gelo). Devolve os tokens que mudaram, com a origem.
 */
async function spread(origin, rule) {
  const scene = origin.parent;
  const start = origin.getFlag(MODULE_ID, "cell");
  const max = rule.spread === "all" ? Infinity : Number(rule.spread ?? 0);
  const cells = waterCells(scene);
  const seen = new Set([key(start.x, start.y)]);
  const queue = [[start.x, start.y, 0]];
  const changed = [origin];
  const updates = [];
  while (queue.length) {
    const [x, y, d] = queue.shift();
    if (d >= max) continue;
    for (const [dx, dy] of [[0, -1], [1, 0], [0, 1], [-1, 0]]) {
      const k = key(x + dx, y + dy);
      if (seen.has(k)) continue;
      seen.add(k);
      const t = cells.get(k);
      const data = t && C.getData(t);
      if (!data || !C.ruleAllows(rule, data)) continue;
      const i = C.indexOfId(data, rule.to);
      if (i === -1) continue;
      updates.push({ _id: t.id, ...C.stateUpdate(t, i) });
      changed.push(t);
      queue.push([x + dx, y + dy, d + 1]);
    }
  }
  if (updates.length) await scene.updateEmbeddedDocuments("Token", updates);
  return changed;
}

/** Chamado pelo core depois que uma regra trocou o estado de um asset. */
export async function afterReaction(token, rule, types) {
  if (!isWater(token) || !(rule.spread || rule.zap)) return;
  const changed = rule.spread ? await spread(token, rule) : [token];
  if (!rule.zap) return;
  const value = types.get("lightning") ?? [...types.values()].reduce((a, b) => a + b, 0);
  const keys = new Set(changed.map(t => {
    const c = t.getFlag(MODULE_ID, "cell");
    return key(c.x, c.y);
  }));
  const who = occupants(token.parent, keys);
  if (!who.length) return;
  await hurt(who, value, "lightning");
  await C.say(token, `dá um choque de ${value} em quem está na água: ${who.map(t => t.name).join(", ")}.`);
}

/**
 * Asset pegando fogo que entra na água apaga sozinho: usa a regra de gelo ("cold") do próprio asset
 * que sai do estado atual (a mesma que apaga o fogo com Raio de Gelo). Veículos e o que vai a bordo não contam.
 */
Hooks.on("updateToken", async (token, changes) => {
  if (!C?.isResponsibleGM() || !("x" in changes || "y" in changes) || isCell(token)) return;
  const data = C.getData(token);
  if (!data?.reactions || data.vehicle || vehicleUnder(token)) return;
  const state = C.currentState(data);
  const rule = data.reactions.find(r => r.to && r.types?.includes("cold") && r.from?.includes(state?.id));
  if (!rule) return;
  const p = C.tokenCenter(token);
  if (!waterStateAt(token.parent, p.x, p.y)?.wet) return;
  const i = C.indexOfId(data, rule.to);
  if (i === -1 || data.states[i].broken) return;
  await C.setState(token, i, { syncHP: false });
  await C.say(token, "cai na água e se apaga.");
});
