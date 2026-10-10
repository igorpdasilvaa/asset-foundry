// Macro (tipo Script) que monta um mapa deste repositório como cena nova no Foundry:
// fundo, paredes, portas, luzes e sons, e depois coloca os assets interativos (mesa, tocha...).
// Precisa do módulo Interactive Assets ativo. Cada execução cria uma cena nova.
const MAPA = "taverna";
const REF = "main"; // branch do GitHub de onde vem o mapa
const REPO = "igorpdasilvaa/asset-foundry";

const r = await fetch(`https://api.github.com/repos/${REPO}/commits/${encodeURIComponent(REF)}`, {
  headers: { Accept: "application/vnd.github.sha" }
});
if (!r.ok) return ui.notifications.error(`Não consegui ler o GitHub (${r.status}).`);
const root = `https://cdn.jsdelivr.net/gh/${REPO}@${(await r.text()).trim()}`;
const data = await (await fetch(`${root}/mapas/${MAPA}/cena.json`)).json();

const objects = data.flags?.["interactive-assets"]?.objects ?? [];
data.background.src = `${root}/${data.background.src}`;
for (const s of data.sounds ?? []) s.path = `${root}/${s.path}`;

const scene = await Scene.create(data);
await scene.view();
if (canvas.scene?.id !== scene.id) await new Promise(res => Hooks.once("canvasReady", res));

const api = game.modules.get("interactive-assets")?.api;
if (!api) ui.notifications.warn("Módulo Interactive Assets não está ativo: a cena foi criada sem mesa e tocha.");
else for (const o of objects) await api.placeAsset(o.asset, { x: o.x, y: o.y });

try {
  const { thumb } = await scene.createThumbnail();
  await scene.update({ thumb });
} catch (e) { console.warn("Mapa: sem miniatura", e); }
ui.notifications.info(`Cena "${scene.name}" criada.`);
