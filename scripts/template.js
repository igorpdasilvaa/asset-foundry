/**
 * Seleciona os tokens dentro de um template (área de magia).
 * - Ao colocar um template, os tokens dentro dele viram alvos (configurável por usuário).
 * - Botão "Selecionar tokens no template" nas ferramentas de template, e Alt+T com o mouse sobre o template:
 *   seleciona (controla) e marca como alvo todos os tokens dentro, prontos para aplicar o dano.
 * Conta como dentro o token com qualquer quadrado destacado pelo template (regra do D&D).
 * Quadrados de água entram nos alvos (para reagirem ao dano), mas não são selecionados (não andam junto).
 */
const MODULE_ID = "interactive-assets";

/** Templates colocados ou mexidos por este usuário, esperando o desenho para calcular a área. */
const pending = new Set();

export function init() {
  game.settings.register(MODULE_ID, "autoTarget", {
    name: "Alvos automáticos nos templates",
    hint: "Ao colocar um template (bola de fogo, cone...), os tokens dentro dele viram seus alvos. Alt+T com o mouse sobre um template seleciona todos eles.",
    scope: "client",
    config: true,
    type: Boolean,
    default: true
  });
  // As ferramentas já foram desenhadas antes do módulo carregar: redesenha com o botão novo.
  ui.controls?.render({ reset: true });
}

const key = o => `${o.i},${o.j}`;

/** Tokens visíveis para este usuário dentro do template. */
export function tokensIn(template) {
  if (!template?.shape) return [];
  const grid = canvas.grid;
  const tokens = canvas.tokens.placeables.filter(t => t.visible);
  if (grid.isGridless) {
    const { x, y } = template.document;
    return tokens.filter(t => template.shape.contains(t.center.x - x, t.center.y - y));
  }
  const cells = new Set(template._getGridHighlightPositions()
    .map(p => key(grid.getOffset({ x: p.x + grid.sizeX / 2, y: p.y + grid.sizeY / 2 }))));
  return tokens.filter(t => t.document.getOccupiedGridSpaceOffsets().some(o => cells.has(key(o))));
}

const isCell = t => !!t.document.getFlag(MODULE_ID, "cell");

/** Marca como alvo; com control, também seleciona (o que o usuário pode controlar, sem quadrados de água). */
export function selectIn(templates, { control = true } = {}) {
  const inside = [...new Set(templates.flatMap(tokensIn))];
  if (control) {
    canvas.tokens.activate();
    canvas.tokens.releaseAll();
    for (const t of inside) if (!isCell(t) && t.can(game.user, "control")) t.control({ releaseOthers: false });
  }
  canvas.tokens.setTargets(inside.map(t => t.id));
  return inside;
}

/** Templates escolhidos para o botão: os selecionados, senão o último que este usuário colocou na cena. */
function chosenTemplates() {
  if (canvas.templates.controlled.length) return canvas.templates.controlled;
  const mine = canvas.templates.placeables.filter(t => t.document.author?.id === game.user.id);
  const last = mine.at(-1) ?? canvas.templates.placeables.at(-1);
  return last ? [last] : [];
}

function announce(inside) {
  ui.notifications.info(inside.length
    ? `${inside.length} token(s) no template: ${inside.map(t => t.name).filter((n, i, a) => a.indexOf(n) === i).join(", ")}.`
    : "Nenhum token dentro do template.");
}

Hooks.on("getSceneControlButtons", controls => {
  const tool = {
    name: "iaSelectInTemplate",
    title: "Selecionar tokens no template (Alt+T)",
    icon: "fa-solid fa-object-group",
    button: true,
    order: 100
  };
  const run = () => {
    const templates = chosenTemplates();
    if (!templates.length) return ui.notifications.warn("Coloque um template na cena primeiro.");
    announce(selectIn(templates));
  };
  if (Array.isArray(controls)) { // v12
    controls.find(c => c.name === "measure")?.tools.push({ ...tool, onClick: run });
  } else if (controls.templates) { // v13
    controls.templates.tools[tool.name] = { ...tool, onChange: run };
  }
});

/** Alt+T: templates sob o mouse (em qualquer camada). */
window.addEventListener("keydown", event => {
  if (event.code !== "KeyT" || !event.altKey || event.ctrlKey || event.metaKey || event.repeat) return;
  if (!canvas?.ready || event.target.closest?.("input, textarea, [contenteditable]")) return;
  const { x, y } = canvas.mousePosition;
  const templates = canvas.templates.placeables.filter(t => t.shape?.contains(x - t.document.x, y - t.document.y));
  if (!templates.length) return;
  event.preventDefault();
  announce(selectIn(templates));
});

/** Alvos automáticos: quando o template que este usuário colocou ou mexeu termina de desenhar. */
const track = (doc, userId) => {
  if (userId === game.user.id && game.settings.get(MODULE_ID, "autoTarget")) pending.add(doc.id);
};
Hooks.on("createMeasuredTemplate", (doc, options, userId) => track(doc, userId));
Hooks.on("updateMeasuredTemplate", (doc, changes, options, userId) => {
  if (["x", "y", "distance", "direction", "angle", "width", "t"].some(k => k in changes)) track(doc, userId);
});
Hooks.on("refreshMeasuredTemplate", template => {
  if (!pending.has(template.id) || !template.shape) return;
  pending.delete(template.id);
  selectIn([template], { control: false });
});
