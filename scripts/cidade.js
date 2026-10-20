/**
 * Cidades: vários mapas ligados por saídas (portões, portas de prédios, escadas).
 *
 * mapas/<cidade>/cidade.json = { "name": "Candlekeep", "mapas": ["candlekeep_portao", ...] }
 * Cada mapa.json pode ter "saidas" (em quadrados):
 *   { "id": "porta_hearth", "x", "y", "w", "h", "pouso": { "x", "y", "w", "h" }, "para": "candlekeep_hearth", "chegada": "rua" }
 * O retângulo é a saída: uma Region com o comportamento "Teleport Token" do Foundry, que leva ao "pouso" da saída
 * "chegada" do mapa "para". "pouso" é onde chega quem vem do outro lado (fica fora da saída, para não voltar na hora).
 * "para" pode ser o próprio mapa (escadas entre andares desenhados lado a lado).
 * Uma saída na porta de um prédio só funciona com a porta aberta (a porta fechada bloqueia o movimento).
 *
 * "notas": [{ "x", "y", "titulo", "texto" }] viram páginas de um diário (só o mestre vê) com alfinetes no mapa.
 * "playlist" no cidade.json: [{ "nome", "path", "repetir"? }] vira uma playlist com o nome da cidade (as músicas de cada
 * lugar, a de combate e as canções), para o mestre tocar à mão. Cada mapa já toca a própria música ("musica" no mapa.json).
 */
const MODULE_ID = "interactive-assets";

const rect = (r, g) => ({ type: "rectangle", x: r.x * g, y: r.y * g, width: (r.w ?? 1) * g, height: (r.h ?? 1) * g, rotation: 0, hole: false });

/** Regiões de saída (ainda sem destino) e de chegada da cena. */
export async function criaSaidas(scene, saidas = []) {
  if (!saidas.length) return;
  const g = scene.grid.size;
  const docs = [];
  for (const s of saidas) {
    docs.push({
      name: `Saída: ${s.nome ?? s.para}`, color: "#3a7bd5", shapes: [rect(s, g)],
      flags: { [MODULE_ID]: { saida: s.id } }
    });
    if (s.pouso) docs.push({
      name: `Chegada: ${s.nome ?? s.para}`, color: "#3ad57b", shapes: [rect(s.pouso, g)],
      flags: { [MODULE_ID]: { pouso: s.id } }
    });
  }
  await scene.createEmbeddedDocuments("Region", docs);
}

/**
 * Liga as saídas às chegadas. cenas: Map(mapId → Scene). Saídas para mapas fora da lista ficam sem destino
 * (o mapa montado sozinho continua funcionando, só a porta não leva a lugar nenhum).
 */
export async function ligaSaidas(cenas) {
  let ligadas = 0;
  const faltando = [];
  for (const scene of cenas.values()) {
    const saidas = scene.getFlag(MODULE_ID, "map")?.saidas ?? [];
    for (const s of saidas) {
      const region = scene.regions.find(r => r.getFlag(MODULE_ID, "saida") === s.id);
      const destino = cenas.get(s.para)?.regions.find(r => r.getFlag(MODULE_ID, "pouso") === s.chegada);
      if (!region) continue;
      if (!destino) {
        if (cenas.size > 1) faltando.push(`${scene.name} → ${s.para}/${s.chegada}`);
        continue;
      }
      const behavior = { name: "Teleportar", type: "teleportToken", system: { destination: destino.uuid, choice: !!s.perguntar } };
      const atual = region.behaviors.find(b => b.type === "teleportToken");
      if (atual) await atual.update({ system: behavior.system });
      else await region.createEmbeddedDocuments("RegionBehavior", [behavior]);
      ligadas++;
    }
  }
  if (faltando.length) ui.notifications.warn(`Saídas sem destino: ${faltando.join(", ")}`);
  return ligadas;
}

/** Diário do mapa (ou da cidade) com uma página por nota, e os alfinetes na cena. */
export async function criaNotas(scene, notas = [], diario) {
  if (!notas.length) return;
  const g = scene.grid.size;
  diario ??= await JournalEntry.create({
    name: `Guia: ${scene.name}`,
    folder: scene.folder?.id ? await pastaDiario(scene.folder.name) : null,
    ownership: { default: CONST.DOCUMENT_OWNERSHIP_LEVELS.NONE }
  });
  const pages = await diario.createEmbeddedDocuments("JournalEntryPage", notas.map(n => ({
    name: n.titulo, type: "text", text: { content: n.texto ?? "" }
  })));
  await scene.createEmbeddedDocuments("Note", notas.map((n, i) => ({
    entryId: diario.id, pageId: pages[i].id, x: (n.x + .5) * g, y: (n.y + .5) * g,
    text: n.titulo, iconSize: 48, texture: { src: n.icone ?? "icons/svg/book.svg" }
  })));
  return diario;
}

async function pastaDiario(nome) {
  let f = game.folders.find(f => f.type === "JournalEntry" && f.getFlag(MODULE_ID, "cidade") === nome);
  f ??= await Folder.create({ name: nome, type: "JournalEntry", flags: { [MODULE_ID]: { cidade: nome } } });
  return f.id;
}

async function confirmar(title, content) {
  const D2 = foundry.applications?.api?.DialogV2;
  if (D2?.confirm) return D2.confirm({ window: { title }, content: `<p>${content}</p>` });
  return Dialog.confirm({ title, content: `<p>${content}</p>` });
}

/**
 * Monta todos os mapas de uma cidade numa pasta de cenas e liga as saídas.
 * Rodar de novo pergunta se substitui as cenas já montadas (as fichas dos personagens não são apagadas,
 * só os tokens que estavam nessas cenas).
 */
export async function buildCity(cidadeId, root, buildMap) {
  const cfg = await (await fetch(`${root}/mapas/${cidadeId}/cidade.json`)).json();
  let pasta = game.folders.find(f => f.type === "Scene" && f.getFlag(MODULE_ID, "cidade") === cidadeId);
  const antigas = game.scenes.filter(s => s.getFlag(MODULE_ID, "cidade") === cidadeId);
  if (antigas.length) {
    const ok = await confirmar(cfg.name, `Já existem ${antigas.length} cena(s) de ${cfg.name}. Substituir? Os tokens dessas cenas serão apagados.`);
    if (!ok) return null;
    await Scene.deleteDocuments(antigas.map(s => s.id));
    const diario = game.journal.find(j => j.getFlag(MODULE_ID, "cidade") === cidadeId);
    await diario?.delete();
    await game.playlists.find(p => p.getFlag(MODULE_ID, "cidade") === cidadeId)?.delete();
  }
  pasta ??= await Folder.create({ name: cfg.name, type: "Scene", sorting: "m", flags: { [MODULE_ID]: { cidade: cidadeId } } });
  const diario = await JournalEntry.create({
    name: `Guia de ${cfg.name}`, folder: await pastaDiario(cfg.name),
    ownership: { default: CONST.DOCUMENT_OWNERSHIP_LEVELS.NONE }, flags: { [MODULE_ID]: { cidade: cidadeId } }
  });
  const cenas = new Map();
  for (const [i, mapId] of cfg.mapas.entries()) {
    ui.notifications.info(`${cfg.name}: montando ${i + 1} de ${cfg.mapas.length} (${mapId})...`);
    const data = await (await fetch(`${root}/mapas/${mapId}/cena.json`)).json();
    const scene = await buildMap(data, root, { folder: pasta.id, sort: i, view: false, cidade: cidadeId, mapId, diario, ligar: false });
    cenas.set(mapId, scene);
  }
  const n = await ligaSaidas(cenas);
  if (cfg.playlist?.length && !game.playlists.find(p => p.getFlag(MODULE_ID, "cidade") === cidadeId)) {
    await Playlist.create({
      name: cfg.name, mode: CONST.PLAYLIST_MODES.DISABLED, flags: { [MODULE_ID]: { cidade: cidadeId } },
      sounds: cfg.playlist.map(m => ({ name: m.nome, path: `${root}/${m.path}`, repeat: m.repetir !== false, volume: 0.5 }))
    });
  }
  ui.notifications.info(`${cfg.name}: ${cenas.size} cena(s) montadas, ${n} saída(s) ligadas.`);
  const inicio = cenas.get(cfg.inicio ?? cfg.mapas[0]);
  await inicio?.view();
  return inicio;
}
