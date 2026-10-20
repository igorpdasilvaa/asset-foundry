/**
 * Efeitos ao entrar num estado (campos do estado no assets.json):
 * - "npc": "<id do npcs.json>": o asset vira aquele NPC (a gárgula desperta e vira golem de pedra).
 * - "colapso": { dc, damage, type }: o lugar desaba; o chat pede o teste de Destreza e mostra o dano (amplificador do Hearth).
 * - "alarme": true: dispara o alarme do lugar, se a cena tiver proteções (o sino tocando).
 */
import * as npc from "./npc.js";
import * as protecoes from "./protecoes.js";

let ctx;
export function init(c) {
  ctx = c;
}

Hooks.on("preUpdateToken", (token, changes, options) => {
  if (ctx && foundry.utils.hasProperty(changes, `flags.${ctx.MODULE_ID}.data.index`)) options[`${ctx.MODULE_ID}EstadoAntes`] = ctx.getData(token)?.index ?? 0;
});

Hooks.on("updateToken", async (token, changes, options) => {
  if (!ctx?.isResponsibleGM() || !foundry.utils.hasProperty(changes, `flags.${ctx.MODULE_ID}.data.index`)) return;
  const data = ctx.getData(token);
  if (!data || options?.[`${ctx.MODULE_ID}EstadoAntes`] === (data.index ?? 0)) return;
  const state = ctx.currentState(data);
  if (state?.npc) await vira(token, state.npc);
  else if (state?.colapso) await colapso(token, state.colapso);
  else if (state?.alarme) {
    const scene = token.parent;
    if (scene.getFlag(ctx.MODULE_ID, "protecoes") && !scene.getFlag(ctx.MODULE_ID, "protecoes").tocado) await protecoes.alarme(scene, token);
    else await ctx.say(token, "toca alto: dá para ouvir em todo o lugar.");
  }
});

/** Troca o token do asset pelo NPC, no mesmo lugar. */
async function vira(token, id) {
  const scene = token.parent;
  const g = scene.grid.size;
  const { x, y } = ctx.tokenCenter(token);
  const [td] = await npc.tokensNomeados(scene, [{ npc: id, x, y }]);
  if (!td) return;
  td.elevation = token.elevation;
  await scene.createEmbeddedDocuments("Token", [td]);
  await ctx.say(token, "desperta!");
  await token.delete();
}

async function colapso(token, { dc = 15, damage = "2d6", type = "bludgeoning" }) {
  await ChatMessage.create({
    content: `<h3>${token.name} se estilhaça!</h3><p>O espaço extradimensional começa a desabar. Todos aqui dentro:
      [[/save dex ${dc}]] ou [[/damage ${damage} ${type}]] (metade se passar). Depois, todos são jogados para fora.</p>`,
    speaker: ChatMessage.getSpeaker({ token })
  });
}
