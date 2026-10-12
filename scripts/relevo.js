/**
 * Relevo: mapas com altura. A cena guarda flags.interactive-assets.map.relevo = { step, height, climbDC }:
 * "height" é uma linha de texto por fileira de quadrados, um dígito por quadrado (vezes "step" pés).
 *
 * - Quem para num quadrado fica na altura do chão dele (elevation do token), a não ser que esteja voando.
 * - Subir custa movimento (a régua mostra): encosta +5 pés a cada 5 pés subidos (na trilha não);
 *   penhasco é escalada, +2 pés por pé de altura, subindo ou descendo (15 pés: 10 do passo escalando + 30 = 40).
 *   Voando, nada muda.
 * - Penhasco: dois quadrados vizinhos com 10 pés ou mais de diferença. Andando, jogadores não passam;
 *   com a ação Escalar passam e o chat pede um teste de Atletismo; pulando para baixo (ação Pular), caem e
 *   levam 1d6 de dano por 10 pés, e ficam caídos. O GM move para qualquer lugar.
 * - Armadilhas: assets com "trap" no assets.json, escondidos na cena. Criatura que passa por cima para ali e
 *   dispara (os hostis, que armaram, passam sem disparar). Estados com "armed" estão armados; "altura" muda o
 *   chão do quadrado (fosso aberto = -10 pés); "trap.roll" faz o pedregulho ligado (flag "link") rolar.
 * - Pedregulho: ao entrar num estado com "rolls", rola até o quadrado da flag "roll" e atinge quem está no caminho.
 */
const MODULE_ID = "interactive-assets";
let C = null;

export function init(ctx) {
  C = ctx;
  patchMovementCost();
}

const relevo = scene => scene?.getFlag(MODULE_ID, "map")?.relevo ?? null;
const key = (x, y) => `${x},${y}`;
const isCell = t => !!t.getFlag(MODULE_ID, "cell");
/** Criatura: token com ator que não é asset (personagens, monstros). */
const isCreature = t => !!t.actor && !C.getData(t);
const armedTrap = t => {
  const data = C.getData(t);
  return data?.trap && C.currentState(data)?.armed ? data : null;
};

/** Quadrados cobertos por um token numa posição (canto de cima à esquerda, em pixels). */
function cellsAt(token, pos, g) {
  const x0 = Math.round(pos.x / g), y0 = Math.round(pos.y / g);
  const out = [];
  for (let dy = 0; dy < Math.max(1, Math.round(token.height)); dy++)
    for (let dx = 0; dx < Math.max(1, Math.round(token.width)); dx++) out.push(key(x0 + dx, y0 + dy));
  return out;
}

/** Função de altura do chão (pés) por quadrado, com os fossos abertos e afins ("altura" do estado). */
export function groundFn(scene) {
  const r = relevo(scene);
  const g = scene.grid.size;
  const extra = new Map();
  for (const t of scene.tokens) {
    const data = C.getData(t);
    const alt = data && C.currentState(data)?.altura;
    if (alt == null) continue;
    for (const k of cellsAt(t, C.posOf(t), g)) extra.set(k, (extra.get(k) ?? 0) + alt);
  }
  return (x, y) => {
    const base = r ? Number(r.height[y]?.[x] ?? 0) * r.step : 0;
    return base + (extra.get(key(x, y)) ?? 0);
  };
}

/** Altura do chão sob o centro do token. */
function groundUnder(token, ground = groundFn(token.parent)) {
  const g = token.parent.grid.size;
  const p = C.posOf(token);
  return ground(Math.floor((p.x + token.width * g / 2) / g), Math.floor((p.y + token.height * g / 2) / g));
}

/**
 * Quadrados (do centro do token) por onde o movimento passa, com a ação de cada passo.
 * points: origem + waypoints (posições do canto do token, em pixels).
 */
function pathSteps(token, points) {
  const scene = token.parent;
  const g = scene.grid.size;
  const half = { x: token.width * g / 2, y: token.height * g / 2 };
  const steps = [];
  for (let k = 1; k < points.length; k++) {
    const a = points[k - 1], b = points[k];
    const cells = scene.grid.getDirectPath([{ x: a.x + half.x, y: a.y + half.y }, { x: b.x + half.x, y: b.y + half.y }]);
    for (let n = 1; n < cells.length; n++) {
      steps.push({
        from: cells[n - 1], to: cells[n], action: b.action, waypoint: k,
        // canto do token quando o centro está neste quadrado
        pos: { x: cells[n].j * g + g / 2 - half.x, y: cells[n].i * g + g / 2 - half.y }
      });
    }
  }
  return steps;
}

/** Penhascos atravessados: passos com 10 pés ou mais de diferença. */
function cliffs(scene, steps, ground) {
  const r = relevo(scene);
  if (!r) return [];
  return steps.map(s => ({ ...s, dh: ground(s.to.j, s.to.i) - ground(s.from.j, s.from.i) }))
    .filter(s => Math.abs(s.dh) >= 2 * r.step);
}

const FREE = new Set(["fly", "blink", "displace"]);

/** Quadrados de trilha ("x,y"): sobem sem custo extra. */
function trailCells(r) {
  const out = new Set();
  (r.trail ?? []).forEach((row, y) => [...row].forEach((c, x) => { if (c === "1") out.add(key(x, y)); }));
  return out;
}

/**
 * Custo de movimento com a altura do chão, usado pela régua, pelo caminho automático e pelo movimento:
 * conta só o deslocamento no plano (a mudança de elevation que o módulo põe nos pontos não soma de novo)
 * e acrescenta a subida: encosta +1 pé por pé subido, penhasco +2 por pé (escalar, subindo ou descendo;
 * pular para baixo não custa). Voar, teleportar e empurrar não mudam.
 */
function patchMovementCost() {
  const proto = CONFIG.Token.objectClass?.prototype;
  if (!proto?._getMovementCostFunction || proto[`${MODULE_ID}Relevo`]) return;
  const original = proto._getMovementCostFunction;
  proto._getMovementCostFunction = function (options) {
    const cost = original.call(this, options);
    const doc = this.document;
    const scene = doc?.parent;
    const r = relevo(scene);
    if (!r || !C || isCell(doc)) return cost;
    const ground = groundFn(scene);
    const trail = trailCells(r);
    const ox = Math.floor(doc.width / 2), oy = Math.floor(doc.height / 2);
    const unit = scene.grid.distance;
    return (from, to, distance, segment) => {
      if (FREE.has(segment.action)) return cost(from, to, distance, segment);
      if (from.i === to.i && from.j === to.j) return 0; // só subiu/desceu no mesmo quadrado
      const flat = from.k === to.k ? distance : unit;
      const c = cost(from, { ...to, k: from.k }, flat, segment);
      const dh = ground(to.j + ox, to.i + oy) - ground(from.j + ox, from.i + oy);
      if (Math.abs(dh) >= 2 * r.step) return c + (dh > 0 || segment.action === "climb" ? 2 * Math.abs(dh) : 0);
      if (dh > 0 && !trail.has(key(to.j + ox, to.i + oy))) return c + dh;
      return c;
    };
  };
  proto[`${MODULE_ID}Relevo`] = true;
}

/** Armadilhas armadas da cena: "x,y" → token. */
function armedCells(scene) {
  const g = scene.grid.size;
  const out = new Map();
  for (const t of scene.tokens) if (armedTrap(t)) for (const k of cellsAt(t, C.posOf(t), g)) out.set(k, t);
  return out;
}

const triggers = token => isCreature(token) && token.disposition !== CONST.TOKEN_DISPOSITIONS.HOSTILE;

const WP_FIELDS = ["x", "y", "elevation", "width", "height", "shape", "action", "snapped", "explicit", "checkpoint"];
const copyWaypoint = w => Object.fromEntries(WP_FIELDS.filter(k => w[k] !== undefined).map(k => [k, w[k]]));

/**
 * Antes de mover (no cliente de quem move):
 * - jogador não anda por penhasco (precisa Escalar, Pular para baixo ou voar);
 * - quem pisa numa armadilha para nela;
 * - cada ponto do caminho fica na altura do chão (menos voando).
 * Os waypoints não podem ser alterados aqui, então o movimento é recusado e refeito já corrigido.
 */
Hooks.on("preMoveToken", (token, move, options) => {
  if (!C || isCell(token)) return;
  const flags = options?.[MODULE_ID] ?? {};
  const scene = token.parent;
  const r = relevo(scene);
  const g = scene.grid.size;
  const ground = groundFn(scene);
  const steps = pathSteps(token, [move.origin, ...move.passed.waypoints]);

  if (!game.user.isGM) {
    for (const s of cliffs(scene, steps, ground)) {
      if (FREE.has(s.action) || s.action === "climb" || (s.action === "jump" && s.dh < 0)) continue;
      ui.notifications.warn(s.dh > 0
        ? `Penhasco de ${s.dh} pés: para subir, clique com o botão direito no token, clique no ícone de movimento (o bonequinho andando) e escolha Escalar. Custa o dobro e pede Atletismo.`
        : `Queda de ${-s.dh} pés: clique com o botão direito no token, clique no ícone de movimento (o bonequinho andando) e escolha Escalar para descer com cuidado, ou Pular para pular (cai e leva dano).`);
      return false;
    }
  }

  // Armadilha no caminho: o movimento vai só até ela.
  let list = null;
  if (!flags.trapStop && triggers(token)) {
    const traps = armedCells(scene);
    const start = new Set(cellsAt(token, move.origin, g));
    const hit = traps.size ? steps.findIndex(s => !FREE.has(s.action)
      && cellsAt(token, s.pos, g).some(k => traps.has(k) && !start.has(k))) : -1;
    if (hit !== -1 && (hit < steps.length - 1 || move.pending.waypoints.length)) {
      const s = steps[hit];
      list = [...move.passed.waypoints.slice(0, s.waypoint - 1).map(copyWaypoint), { x: s.pos.x, y: s.pos.y, action: s.action }];
    }
  }

  // Altura do chão em cada ponto do caminho.
  const truncated = !!list;
  let changed = truncated;
  if (r && !flags.ground) {
    list ??= [...move.passed.waypoints, ...move.pending.waypoints].map(copyWaypoint);
    for (const w of list) {
      if (FREE.has(w.action)) continue;
      const cx = Math.floor((w.x + (w.width ?? token.width) * g / 2) / g);
      const cy = Math.floor((w.y + (w.height ?? token.height) * g / 2) / g);
      const z = ground(cx, cy);
      if (w.elevation !== z) {
        w.elevation = z;
        changed = true;
      }
    }
  }
  if (!changed) return;
  const keep = options.animation ? { animation: options.animation } : {};
  setTimeout(() => token.move(list, { ...keep, method: move.method,
    [MODULE_ID]: { ...flags, trapStop: flags.trapStop || truncated, ground: true } }), 0);
  return false;
});

/** Depois de mover (GM): armadilhas, quedas e escalada. */
Hooks.on("moveToken", async (token, movement) => {
  if (!C?.isResponsibleGM() || isCell(token)) return;
  const scene = token.parent;
  const steps = pathSteps(token, [movement.origin, ...movement.passed.waypoints]);

  // Armadilha embaixo de quem parou.
  if (!movement.pending?.waypoints?.length && triggers(token)) {
    const traps = armedCells(scene);
    const g = scene.grid.size;
    const here = [...new Set(cellsAt(token, C.posOf(token), g).map(k => traps.get(k)).filter(Boolean))];
    for (const trap of here) await spring(trap, token);
  }

  const crossed = cliffs(scene, steps, groundFn(scene));
  const climbed = crossed.filter(s => s.action === "climb");
  if (climbed.length) {
    const h = Math.max(...climbed.map(s => Math.abs(s.dh)));
    const dc = relevo(scene).climbDC ?? 12;
    await C.say(token, `escala ${h} pés de penhasco. Teste de [[/skill athletics ${dc}]]; se falhar, cai: `
      + `[[/damage ${Math.max(1, Math.floor(h / 10))}d6 bludgeoning]] e fica caído.`);
  }
  const fell = crossed.filter(s => s.action === "jump" && s.dh < 0).reduce((n, s) => n - s.dh, 0);
  if (fell >= 10 && token.actor) await fall(token, fell);
});

/** Fosso aberto (ou outro chão que mudou): quem está em cima vai para a nova altura. */
async function settle(scene, cells) {
  const ground = groundFn(scene);
  const g = scene.grid.size;
  for (const t of scene.tokens) {
    if (isCell(t) || t.id === undefined || !cellsAt(t, C.posOf(t), g).some(k => cells.has(k))) continue;
    const z = groundUnder(t, ground);
    if (t.elevation !== z) await t.update({ elevation: z }, { [MODULE_ID]: { ground: true } });
  }
}

/** Queda: 1d6 de concussão a cada 10 pés (até 20d6), e fica caído. */
async function fall(token, feet) {
  const n = Math.min(20, Math.floor(feet / 10));
  const roll = await new Roll(`${n}d6`).evaluate();
  await roll.toMessage({ speaker: ChatMessage.getSpeaker({ token }), flavor: `${token.name} cai ${feet} pés e fica caído.` });
  await token.actor.applyDamage([{ value: roll.total, type: "bludgeoning", properties: new Set() }]);
  await token.actor.toggleStatusEffect?.("prone", { active: true });
}

/** Dispara a armadilha: aparece, troca de estado, avisa no chat e, se tiver, solta o pedregulho ligado. */
async function spring(trapToken, victim) {
  const data = C.getData(trapToken);
  const i = C.indexOfId(data, data.trap.to);
  await trapToken.update({ hidden: false, ...(i === -1 ? {} : C.stateUpdate(trapToken, i)) });
  if (data.trap.say) await C.say(victim, data.trap.say);
  if (data.trap.roll) {
    const link = trapToken.getFlag(MODULE_ID, "link");
    const scene = trapToken.parent;
    const g = scene.grid.size;
    const boulder = link && scene.tokens.find(t => C.getData(t)?.boulder && cellsAt(t, C.posOf(t), g).includes(key(link.x, link.y)));
    const bd = boulder && C.getData(boulder);
    const to = bd && bd.states.findIndex(s => s.rolls);
    if (boulder && to !== -1) await C.setState(boulder, to, { syncHP: false });
  }
}

/** Troca de estado (GM): chão que mudou de altura (fosso) e pedregulho que começa a rolar. */
Hooks.on("preUpdateToken", (token, changes, options) => {
  if (foundry.utils.hasProperty(changes, `flags.${MODULE_ID}.data.index`)) options[`${MODULE_ID}PrevState`] = C?.getData(token)?.index ?? 0;
});
Hooks.on("updateToken", async (token, changes, options) => {
  if (!C?.isResponsibleGM() || !foundry.utils.hasProperty(changes, `flags.${MODULE_ID}.data.index`)) return;
  const data = C.getData(token);
  const prev = options[`${MODULE_ID}PrevState`];
  if (prev === data.index) return;
  const g = token.parent.grid.size;
  if (data.states[prev]?.altura != null || C.currentState(data)?.altura != null) {
    await settle(token.parent, new Set(cellsAt(token, C.posOf(token), g)));
  }
  if (data.boulder && C.currentState(data)?.rolls) await roll(token, data);
});

/** O pedregulho rola até a flag "roll" (quadrado): deixa um rastro e avisa quem estava no caminho. */
async function roll(token, data) {
  const to = token.getFlag(MODULE_ID, "roll");
  if (!to) return;
  const scene = token.parent;
  const g = scene.grid.size;
  const p = C.posOf(token);
  const from = { x: Math.floor((p.x + g / 2) / g), y: Math.floor((p.y + g / 2) / g) };
  const cells = scene.grid.getDirectPath([{ i: from.y, j: from.x }, { i: to.y, j: to.x }]).map(c => key(c.j, c.i));
  const line = new Set(cells.slice(1));
  const hit = scene.tokens.filter(t => t.id !== token.id && isCreature(t) && cellsAt(t, C.posOf(t), g).some(k => line.has(k)));

  // Rastro do pedregulho (modelo de linha), para todos verem o caminho; os atingidos viram alvo do GM.
  const a = { x: p.x + g / 2, y: p.y + g / 2 }, b = { x: to.x * g + g / 2, y: to.y * g + g / 2 };
  await scene.createEmbeddedDocuments("MeasuredTemplate", [{
    t: "ray", x: a.x, y: a.y, distance: Math.hypot(b.x - a.x, b.y - a.y) / g * scene.grid.distance, width: scene.grid.distance,
    direction: Math.toDegrees(Math.atan2(b.y - a.y, b.x - a.x)), fillColor: "#8a6f4d", borderColor: "#3b2a18",
    flags: { [MODULE_ID]: { rockfall: token.id } }
  }]);
  await token.update({ x: to.x * g, y: to.y * g }, { animation: { duration: 1400 } });
  const { dc = 14, damage = "3d10" } = data.boulder;
  const names = hit.map(t => t.name).filter((n, i, all) => all.indexOf(n) === i);
  await C.say(token, names.length
    ? `rola encosta abaixo! No caminho: ${names.join(", ")}. [[/save dex ${dc}]]; se falhar: [[/damage ${damage} bludgeoning]] e fica caído.`
    : "rola encosta abaixo, mas não pega ninguém.");
  if (canvas.scene?.id === scene.id && hit.length) canvas.tokens.setTargets(hit.map(t => t.id));
}
