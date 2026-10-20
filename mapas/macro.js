// Macro (tipo Script) que monta um mapa deste repositório como cena nova no Foundry:
// fundo, luzes e sons, paredes/portas/pilares quebráveis e os objetos interativos (mesa, tocha, barril...).
// Se MAPA for uma cidade (pasta com cidade.json, ex.: "vila_teste"), monta todos os mapas dela numa pasta de cenas,
// com as saídas ligando um mapa ao outro. Precisa do módulo Interactive Assets ativo. Cada execução cria cenas novas.
const MAPA = "taverna";
const REF = "main"; // branch do GitHub de onde vem o mapa
const REPO = "igorpdasilvaa/asset-foundry";

const api = game.modules.get("interactive-assets")?.api;
if (!api?.buildMap) return ui.notifications.error("Interactive Assets desatualizado: atualize o módulo para a versão 0.7.0 ou mais nova (ou ligue o Modo desenvolvimento) e recarregue a página.");

// Com o modo desenvolvimento, usa o mesmo commit que o módulo carregou (sem gastar consulta ao GitHub).
let root = REF === "main" && api.root?.startsWith("http") ? api.root : null;
if (!root) {
  // O GitHub libera 60 consultas por hora; se passar disso (erro 403), lê os arquivos direto do repositório.
  const r = await fetch(`https://api.github.com/repos/${REPO}/commits/${encodeURIComponent(REF)}`, {
    headers: { Accept: "application/vnd.github.sha" }
  }).catch(() => null);
  root = r?.ok
    ? `https://cdn.jsdelivr.net/gh/${REPO}@${(await r.text()).trim()}`
    : `https://raw.githubusercontent.com/${REPO}/${REF}`;
}
const miniatura = async scene => {
  try {
    const { thumb } = await scene.createThumbnail();
    await scene.update({ thumb });
  } catch (e) { console.warn("Mapa: sem miniatura", e); }
};
const cidade = await fetch(`${root}/mapas/${MAPA}/cidade.json`).then(r => r.ok ? r.json() : null).catch(() => null);
if (cidade) {
  if (!api.buildCity) return ui.notifications.error("Interactive Assets desatualizado: atualize o módulo para a versão 0.11.0 ou mais nova (ou ligue o Modo desenvolvimento).");
  const inicio = await api.buildCity(MAPA, root);
  if (inicio) for (const s of game.scenes.filter(s => s.getFlag("interactive-assets", "cidade") === MAPA)) await miniatura(s);
  return;
}
const data = await (await fetch(`${root}/mapas/${MAPA}/cena.json`)).json();

const scene = await api.buildMap(data, root);
await miniatura(scene);
ui.notifications.info(`Cena "${scene.name}" criada.`);
