/**
 * Proteções de um lugar (Candlekeep): flags.interactive-assets.protecoes da cena =
 * { ativas, alarme, resposta: [{ npc, n }], dano, tocado }.
 * - Fogo abafado: com as proteções ativas, nenhum asset entra num estado de fogo (burning, dot de fogo ou "chama",
 *   como a tocha acesa). Fica chamuscado/apagado ou no estado em que estava. Assets com "fogoPermitido" (lareira,
 *   forja) continuam queimando. Regras de "onZero" só de fogo/raio (virar cinzas) são puladas.
 * - Ordens de Concordância: dano em asset com "conhecimento" (estante, livros) ou em NPC (nomeado ou plebeu)
 *   soma em "dano" e avisa no chat. Ao chegar em "alarme", toca o alarme uma vez: aparecem os NPCs de "resposta"
 *   perto de quem foi atingido.
 * O mestre liga e desliga pelo botão "Proteções" nas ferramentas de token (só nas cenas que têm proteções)
 * ou por api.protecoes(cena, ligar). api.resetAlarme(cena) zera a contagem.
 */
import * as npc from "./npc.js";

let ctx;
const FIRE_ONLY = new Set(["fire", "lightning"]);

export function init(c) {
  ctx = c;
}

const cfg = scene => scene?.getFlag(ctx.MODULE_ID, "protecoes") ?? null;
export const ativas = scene => !!cfg(scene)?.ativas;

const def = token => ctx.registry()[ctx.getData(token)?.asset];
export const isFogo = s => !!(s && (s.burning || s.chama || s.dot?.type === "fire"));
const protegido = token => ativas(token.parent) && !def(token)?.fogoPermitido;

/** Estado no lugar de um estado de fogo: chamuscado, apagado ou o atual (se ele mesmo não for fogo). */
function semFogo(data, atual) {
  const alt = ["chamuscada", "chamuscado", "apagada", "apagado"].map(id => ctx.indexOfId(data, id)).find(i => i !== -1);
  if (alt != null) return alt;
  return isFogo(data.states[atual]) ? 0 : atual;
}

/**
 * Chamado pelo core antes de trocar o estado por uma reação: devolve o índice permitido
 * (o mesmo, se não houver proteção) e se a chama foi abafada.
 */
export function filtra(token, target) {
  const data = ctx.getData(token);
  if (!protegido(token) || !isFogo(data.states[target])) return { index: target, abafado: false };
  return { index: semFogo(data, data.index ?? 0), abafado: true };
}

/** Regra de "onZero" vale aqui? As que só existem para fogo/raio (virar cinzas) não valem com proteção. */
export function regraZero(token, rule) {
  if (!rule.types || !protegido(token)) return true;
  return !rule.types.every(t => FIRE_ONLY.has(t));
}

export const ABAFADO = "tem a chama sufocada pelas proteções do lugar.";

/** Token criado (tocha trazida de fora, teleporte) ou trocado de estado pelo HUD: apaga se for fogo. */
async function apagaSeFogo(token) {
  const data = ctx.getData(token);
  if (!data || !protegido(token) || !isFogo(ctx.currentState(data))) return;
  await ctx.setState(token, semFogo(data, data.index ?? 0), { syncHP: false });
  await ctx.say(token, ABAFADO);
}

Hooks.on("createToken", token => {
  if (ctx && ctx.isResponsibleGM()) apagaSeFogo(token);
});
Hooks.on("updateToken", (token, changes) => {
  if (ctx && ctx.isResponsibleGM() && foundry.utils.hasProperty(changes, `flags.${ctx.MODULE_ID}.data.index`)) apagaSeFogo(token);
});

/** Liga/desliga as proteções da cena. Ligar apaga tudo o que estiver pegando fogo. */
export async function protecoes(scene = canvas.scene, ligar = !ativas(scene)) {
  const atual = cfg(scene) ?? { alarme: 1, dano: 0, tocado: false };
  await scene.setFlag(ctx.MODULE_ID, "protecoes", { ...atual, ativas: ligar });
  if (ligar) for (const t of scene.tokens) await apagaSeFogo(t);
  ChatMessage.create({
    content: ligar
      ? `<p><strong>${scene.name}</strong>: as proteções estão ativas. Nenhuma chama maior que uma vela se mantém acesa.</p>`
      : `<p><strong>${scene.name}</strong>: as proteções caíram! O fogo volta a se espalhar normalmente.</p>`
  });
  ui.controls?.render?.();
}

export async function resetAlarme(scene = canvas.scene) {
  if (cfg(scene)) await scene.setFlag(ctx.MODULE_ID, "protecoes", { ...cfg(scene), dano: 0, tocado: false });
}

/* ---------- Ordens de Concordância ---------- */

const contaComo = token => def(token)?.conhecimento ? "conhecimento"
  : (token.getFlag(ctx.MODULE_ID, "plebeu") || token.actor?.getFlag(ctx.MODULE_ID, "npc")) ? "pessoa" : null;

Hooks.on("preUpdateActor", (actor, changes, options) => {
  if (foundry.utils.hasProperty(changes, "system.attributes.hp.value")) options[`${ctx?.MODULE_ID}HpAntes`] = actor.system.attributes.hp.value;
});

Hooks.on("updateActor", async (actor, changes, options) => {
  if (!ctx?.isResponsibleGM()) return;
  const antes = options?.[`${ctx.MODULE_ID}HpAntes`];
  const depois = foundry.utils.getProperty(changes, "system.attributes.hp.value");
  if (antes == null || depois == null || depois >= antes) return;
  const tokens = actor.isToken ? [actor.token] : actor.getActiveTokens(false, true);
  for (const token of tokens) {
    const scene = token.parent;
    const tipo = contaComo(token);
    if (!tipo || !ativas(scene)) continue;
    const c = cfg(scene);
    const dano = (c.dano ?? 0) + 1;
    await scene.setFlag(ctx.MODULE_ID, "protecoes", { ...c, dano });
    await ctx.say(token, tipo === "conhecimento"
      ? "sofre dano. <em>Quem destrói o conhecimento, com tinta, fogo ou espada, será destruído.</em>"
      : "sofre um ataque. As Ordens de Concordância proíbem brigas dentro das muralhas.");
    if (dano >= (c.alarme ?? 1) && !c.tocado) await alarme(scene, token);
  }
});

/** Toca o alarme: avisa e traz a resposta (ex.: 1 arquimago e 4 magos) para perto do token. */
export async function alarme(scene, perto) {
  await scene.setFlag(ctx.MODULE_ID, "protecoes", { ...cfg(scene), tocado: true });
  const resposta = cfg(scene).resposta ?? [];
  ChatMessage.create({ content: `<h3>Alarme!</h3><p>Os sinos tocam em <strong>${scene.name}</strong>.${resposta.length ? " Os guardiões chegam num piscar de olhos." : ""}</p>` });
  if (!resposta.length || !perto) return;
  const g = scene.grid.size;
  const cx = Math.round(perto.x / g), cy = Math.round(perto.y / g);
  const occ = new Set(scene.tokens.map(t => `${Math.round(t.x / g)},${Math.round(t.y / g)}`));
  for (const f of scene.getFlag(ctx.MODULE_ID, "map")?.fixed ?? []) occ.add(f);
  const cells = [];
  for (let r = 2; r <= 6 && cells.length < 12; r++)
    for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
      if (Math.max(Math.abs(dx), Math.abs(dy)) !== r) continue;
      const k = `${cx + dx},${cy + dy}`;
      if (cx + dx < 0 || cy + dy < 0 || occ.has(k)) continue;
      occ.add(k);
      cells.push([cx + dx, cy + dy]);
    }
  const lista = resposta.flatMap(r => Array(r.n ?? 1).fill(r.npc));
  const npcs = lista.map((id, i) => cells[i] && { npc: id, x: (cells[i][0] + .5) * g, y: (cells[i][1] + .5) * g }).filter(Boolean);
  const tokens = await npc.tokensNomeados(scene, npcs);
  if (tokens.length) await scene.createEmbeddedDocuments("Token", tokens);
}

/* ---------- Botão nas ferramentas de token ---------- */

Hooks.on("getSceneControlButtons", controls => {
  if (!ctx || !game.user.isGM || !cfg(canvas?.scene)) return;
  const tool = {
    name: "iaProtecoes",
    title: "Proteções do lugar (fogo abafado e alarme)",
    icon: "fa-solid fa-shield-halved",
    toggle: true,
    active: ativas(canvas.scene),
    order: 101
  };
  if (Array.isArray(controls)) { // v12
    controls.find(c => c.name === "token")?.tools.push({ ...tool, onClick: on => protecoes(canvas.scene, on) });
  } else if (controls.tokens) { // v13
    controls.tokens.tools[tool.name] = { ...tool, onChange: (event, on) => protecoes(canvas.scene, on) };
  }
});
Hooks.on("canvasReady", () => ui.controls?.render?.({ reset: true }));
