// Macro (tipo Script) que monta um mapa deste repositório como cena nova no Foundry:
// fundo, luzes e sons, paredes/portas/pilares quebráveis e os objetos interativos (mesa, tocha, barril...).
// Precisa do módulo Interactive Assets ativo. Cada execução cria uma cena nova.
const MAPA = "taverna";
const REF = "main"; // branch do GitHub de onde vem o mapa
const REPO = "igorpdasilvaa/asset-foundry";

const api = game.modules.get("interactive-assets")?.api;
if (!api?.buildMap) return ui.notifications.error("Interactive Assets desatualizado: atualize o módulo para a versão 0.7.0 ou mais nova (ou ligue o Modo desenvolvimento) e recarregue a página.");

const r = await fetch(`https://api.github.com/repos/${REPO}/commits/${encodeURIComponent(REF)}`, {
  headers: { Accept: "application/vnd.github.sha" }
});
if (!r.ok) return ui.notifications.error(`Não consegui ler o GitHub (${r.status}).`);
const root = `https://cdn.jsdelivr.net/gh/${REPO}@${(await r.text()).trim()}`;
const data = await (await fetch(`${root}/mapas/${MAPA}/cena.json`)).json();

const scene = await api.buildMap(data, root);
try {
  const { thumb } = await scene.createThumbnail();
  await scene.update({ thumb });
} catch (e) { console.warn("Mapa: sem miniatura", e); }
ui.notifications.info(`Cena "${scene.name}" criada.`);
