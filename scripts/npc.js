/**
 * NPCs: nomeados (um ator por NPC) e plebeus aleatórios (um ator por ofício, cada token com nome, espécie,
 * imagem e mania próprios). Tudo vem de assets/npcs.json:
 * - "nomeados": { id: { nome, titulo, especie, base, img?, bio, cidade, unico?, disposicao?, ajustes? } }
 *   ("ajustes": campos do ator trocados depois da cópia, ex.: { "system.abilities.int.value": 19 })
 * - "oficios": { id: { nome, base, especies: { especie: peso }, imgs: [{ src, especie }] } }
 * - "especies": { id: { nome, m: [...], f: [...], sobrenomes?: [...] } }, "manias": [...]
 * "base" é o nome do bloco de estatísticas no compêndio do sistema (SRD do dnd5e), em inglês ou traduzido;
 * o ator é copiado de lá. Sem o compêndio, usa os números de FALLBACK.
 *
 * No mapa.json: "npcs": [{ "npc", "x", "y" }] (pixels, centro) e
 * "multidao": [{ "area": [x, y, w, h] (quadrados), "n", "oficios": [...] }].
 */
let ctx;
let NPCS = { nomeados: {}, oficios: {}, especies: {}, manias: [] };
const key = (x, y) => `${x},${y}`;

/** Números mínimos se o compêndio não tiver o bloco (CA, PV, ND). */
const FALLBACK = {
  commoner: [10, 4, 0], acolyte: [10, 9, 0.25], priest: [13, 27, 2], guard: [16, 11, 0.125], veteran: [17, 58, 3],
  mage: [12, 40, 6], archmage: [12, 99, 12], noble: [15, 9, 0.125], scout: [13, 16, 0.5], "stone golem": [17, 178, 10],
  ogre: [11, 59, 2], bard: [15, 44, 2], horse: [10, 13, 0.25], "riding horse": [10, 13, 0.25], pony: [10, 11, 0.125],
  mule: [10, 11, 0.125], hippogriff: [11, 19, 1], griffon: [12, 59, 2], wyvern: [13, 110, 6], cat: [12, 2, 0]
};

export function init(c) {
  ctx = c;
}

export async function load(base, version) {
  try {
    NPCS = await (await fetch(`${base}/npcs.json?v=${version}`, { cache: "no-cache" })).json();
  } catch (e) {
    console.warn(`${ctx.MODULE_ID} | sem npcs.json`, e);
  }
}

export const data = () => NPCS;

/* ---------- Atores ---------- */

const lista = base => (Array.isArray(base) ? base : [base]).map(n => n.toLowerCase());

/** Procura o bloco de estatísticas nos compêndios de atores (os do sistema primeiro). Aceita nome original (Babele). */
async function doCompendio(base) {
  const want = lista(base);
  const packs = game.packs.filter(p => p.documentName === "Actor")
    .sort((a, b) => (b.metadata.packageName === game.system.id) - (a.metadata.packageName === game.system.id));
  for (const pack of packs) {
    const index = await pack.getIndex({ fields: ["flags.babele.originalName"] });
    const hit = index.find(e => [e.name, e.originalName, e.flags?.babele?.originalName]
      .some(n => n && want.includes(n.toLowerCase())));
    if (hit) return pack.getDocument(hit._id);
  }
  return null;
}

async function pasta(chave, nome) {
  const root = await ctx.rootFolder();
  const npcs = await ctx.childFolder(root, "npcs", "NPCs");
  return chave ? ctx.childFolder(npcs, `npcs/${chave}`, nome) : npcs;
}

const imgPath = src => src ? `${ctx.base()}/${src}` : null;
const DISP = { amigavel: 1, neutro: 0, hostil: -1 };

/** Cria o ator a partir do compêndio (ou do FALLBACK) com nome, imagem, biografia e flags. */
async function criaAtor({ nome, base, img, bio, folder, linked, disposicao = "neutro", ajustes = {}, flags }) {
  const src = await doCompendio(base);
  let data;
  if (src) {
    data = src.toObject();
    delete data._id;
    delete data.folder;
    delete data.sort;
    delete data.ownership;
  } else {
    const [ac, hp, cr] = FALLBACK[lista(base)[0]] ?? FALLBACK.commoner;
    console.warn(`${ctx.MODULE_ID} | "${lista(base)[0]}" não está nos compêndios, NPC "${nome}" criado com CA ${ac} e ${hp} PV`);
    data = { type: "npc", system: { attributes: { ac: { calc: "flat", flat: ac }, hp: { value: hp, max: hp } }, details: { cr } }, prototypeToken: {} };
  }
  const image = imgPath(img) ?? data.img ?? "icons/svg/mystery-man.svg";
  data.name = nome;
  data.img = image;
  data.folder = folder.id;
  foundry.utils.setProperty(data, "system.details.biography.value", bio ?? "");
  for (const [k, v] of Object.entries(ajustes)) foundry.utils.setProperty(data, k, v);
  data.prototypeToken = {
    ...data.prototypeToken, name: nome, actorLink: linked, disposition: DISP[disposicao] ?? 0,
    displayName: CONST.TOKEN_DISPLAY_MODES.HOVER, texture: { ...(data.prototypeToken?.texture ?? {}), src: image }
  };
  data.flags = { ...(data.flags ?? {}), [ctx.MODULE_ID]: flags };
  return Actor.create(data);
}

const bioNomeado = n => `<p><strong>${n.titulo ?? ""}</strong>${n.especie ? ` · ${NPCS.especies[n.especie]?.nome ?? n.especie}` : ""}</p><p>${n.bio ?? ""}</p>`;

/** Ator do NPC nomeado (cria se faltar; mantém imagem e biografia em dia com o npcs.json). */
export async function npcActor(id) {
  const n = NPCS.nomeados[id];
  if (!n) return null;
  let actor = game.actors.find(a => a.getFlag(ctx.MODULE_ID, "npc") === id);
  if (actor) {
    const img = imgPath(n.img);
    const bio = bioNomeado(n);
    if (img && actor.img !== img) await actor.update({ img, "prototypeToken.texture.src": img });
    if (actor.system?.details?.biography?.value !== bio) await actor.update({ "system.details.biography.value": bio });
    return actor;
  }
  const folder = await pasta(n.cidade ?? "geral", n.cidade ?? "Geral");
  return criaAtor({
    nome: n.nome, base: n.base, img: n.img, bio: bioNomeado(n), folder, linked: n.unico !== false,
    disposicao: n.disposicao, ajustes: n.ajustes, flags: { npc: id }
  });
}

/** Ator-modelo de um ofício de plebeu (os tokens não ficam ligados a ele: cada um tem a própria vida). */
async function oficioActor(id) {
  const o = NPCS.oficios[id];
  if (!o) return null;
  const found = game.actors.find(a => a.getFlag(ctx.MODULE_ID, "oficio") === id);
  if (found) return found;
  const folder = await pasta("plebeus", "Plebeus");
  return criaAtor({ nome: o.nome, base: o.base, img: o.imgs?.[0]?.src, bio: `<p>${o.descricao ?? ""}</p>`, folder, linked: false, flags: { oficio: id } });
}

/* ---------- Plebeus ---------- */

const pick = list => list[Math.floor(Math.random() * list.length)];
function pickPeso(pesos) {
  const total = Object.values(pesos).reduce((a, b) => a + b, 0);
  let r = Math.random() * total;
  for (const [k, w] of Object.entries(pesos)) if ((r -= w) < 0) return k;
  return Object.keys(pesos)[0];
}

/** Sorteia quem é o plebeu: nome, espécie, gênero, mania e imagem (da espécie, se houver). */
export function sorteiaPlebeu(oficioId) {
  const o = NPCS.oficios[oficioId];
  const especie = pickPeso(o.especies ?? { humano: 1 });
  const e = NPCS.especies[especie] ?? NPCS.especies.humano;
  const genero = Math.random() < .5 ? "m" : "f";
  const proprio = pick(e[genero] ?? e.m);
  const nome = e.sobrenomes?.length ? `${proprio} ${pick(e.sobrenomes)}` : proprio;
  const imgs = o.imgs ?? [];
  const daEspecie = imgs.filter(i => i.especie === especie && (!i.genero || i.genero === genero));
  const img = (daEspecie.length ? pick(daEspecie) : imgs.length ? pick(imgs) : null)?.src ?? null;
  return { nome, especie, genero, oficio: oficioId, mania: NPCS.manias?.length ? pick(NPCS.manias) : "", img };
}

/** Quadrados ocupados: blocos fixos, tokens (estruturas, objetos, água, árvores, gente), saídas e chegadas. */
function ocupados(scene) {
  const g = scene.grid.size;
  const map = scene.getFlag(ctx.MODULE_ID, "map") ?? {};
  const occ = new Set(map.fixed ?? []);
  for (const t of scene.tokens) {
    const x0 = Math.round(t.x / g), y0 = Math.round(t.y / g);
    for (let dx = 0; dx < Math.max(1, Math.round(t.width)); dx++)
      for (let dy = 0; dy < Math.max(1, Math.round(t.height)); dy++) occ.add(key(x0 + dx, y0 + dy));
  }
  // Ninguém fica parado na saída nem no lugar onde chega quem vem de outra cena.
  for (const r of (map.saidas ?? []).flatMap(s => [s, s.pouso].filter(Boolean)))
    for (let dx = 0; dx < (r.w ?? 1); dx++) for (let dy = 0; dy < (r.h ?? 1); dy++) occ.add(key(r.x + dx, r.y + dy));
  return occ;
}

/** Quadrados livres dentro da área [x, y, w, h], embaralhados. */
function livres(scene, [ax, ay, aw, ah], occ) {
  const map = scene.getFlag(ctx.MODULE_ID, "map") ?? {};
  const cells = [];
  for (let y = ay; y < ay + ah; y++) for (let x = ax; x < ax + aw; x++) {
    if (x < 0 || y < 0 || (map.cols && x >= map.cols) || (map.rows && y >= map.rows) || occ.has(key(x, y))) continue;
    cells.push([x, y]);
  }
  for (let i = cells.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [cells[i], cells[j]] = [cells[j], cells[i]];
  }
  return cells;
}

/** Dados dos tokens de plebeus para as áreas de multidão (sem criar ainda). */
export async function tokensMultidao(scene, multidao = [], ground = () => 0) {
  const g = scene.grid.size;
  const occ = ocupados(scene);
  const out = [];
  for (const m of multidao) {
    const oficios = (m.oficios ?? Object.keys(NPCS.oficios)).filter(o => NPCS.oficios[o]);
    if (!oficios.length) continue;
    const cells = livres(scene, m.area, occ).slice(0, m.n ?? 1);
    for (const [x, y] of cells) {
      occ.add(key(x, y));
      const quem = sorteiaPlebeu(pick(oficios));
      const actor = await oficioActor(quem.oficio);
      if (!actor) continue;
      const td = await actor.getTokenDocument({
        x: x * g, y: y * g, elevation: ground(x, y), name: quem.nome,
        ...(quem.img ? { texture: { src: imgPath(quem.img) } } : {}),
        flags: { [ctx.MODULE_ID]: { plebeu: quem } }
      });
      out.push(td.toObject());
    }
  }
  return out;
}

/** Dados dos tokens dos NPCs nomeados (x, y em pixels, no centro do quadrado). */
export async function tokensNomeados(scene, npcs = [], ground = () => 0) {
  const g = scene.grid.size;
  const out = [];
  for (const n of npcs) {
    const actor = await npcActor(n.npc);
    if (!actor) {
      ui.notifications.warn(`NPC "${n.npc}" não está no npcs.json.`);
      continue;
    }
    const w = actor.prototypeToken.width ?? 1, h = actor.prototypeToken.height ?? 1;
    const td = await actor.getTokenDocument({
      x: Math.round(n.x - w * g / 2), y: Math.round(n.y - h * g / 2), elevation: ground(Math.floor(n.x / g), Math.floor(n.y / g)),
      ...(n.hidden ? { hidden: true } : {})
    });
    out.push(td.toObject());
  }
  return out;
}

/** Macro: coloca n plebeus na cena atual, na área [x, y, w, h] em quadrados (padrão: o que está na tela). */
export async function gerarPlebeus(n = 5, { oficios, area, scene = canvas.scene } = {}) {
  if (!area) {
    const g = scene.grid.size, r = canvas.dimensions.rect, v = canvas.app.renderer.screen, s = canvas.stage.scale.x;
    const p = canvas.stage.pivot;
    const w = v.width / s, h = v.height / s;
    area = [Math.floor(Math.max(r.x, p.x - w / 2) / g), Math.floor(Math.max(r.y, p.y - h / 2) / g), Math.ceil(w / g), Math.ceil(h / g)];
  }
  const tokens = await tokensMultidao(scene, [{ area, n, oficios }]);
  if (tokens.length < n) ui.notifications.warn(`Só coube(ram) ${tokens.length} plebeu(s) na área.`);
  return tokens.length ? scene.createEmbeddedDocuments("Token", tokens) : [];
}

/* ---------- HUD: quem é? ---------- */

function ficha(doc) {
  const p = doc.getFlag(ctx.MODULE_ID, "plebeu");
  if (p) {
    const o = NPCS.oficios[p.oficio];
    return `<p><strong>${doc.name}</strong>: ${o?.nome ?? p.oficio}, ${NPCS.especies[p.especie]?.nome ?? p.especie}.</p>${p.mania ? `<p><em>${p.mania}</em></p>` : ""}`;
  }
  const id = doc.actor?.getFlag(ctx.MODULE_ID, "npc");
  const n = id && NPCS.nomeados[id];
  return n ? `<p><strong>${n.nome}</strong>, ${n.titulo ?? ""}.</p><p>${n.bio ?? ""}</p>` : null;
}

Hooks.on("renderTokenHUD", (hud, html) => {
  if (!game.user.isGM || !ctx) return;
  const doc = hud.object?.document;
  const texto = doc && ficha(doc);
  if (!texto) return;
  const root = html instanceof HTMLElement ? html : html[0];
  const col = root.querySelector(".col.left") ?? root;
  const btn = document.createElement("div");
  btn.className = "control-icon ia-npc";
  btn.dataset.tooltip = "Quem é? (sussurra para o mestre)";
  btn.innerHTML = `<i class="fas fa-id-card"></i>`;
  btn.addEventListener("click", ev => {
    ev.preventDefault();
    ChatMessage.create({ content: texto, whisper: ChatMessage.getWhisperRecipients("GM").map(u => u.id), speaker: ChatMessage.getSpeaker({ token: doc }) });
  });
  col.appendChild(btn);
});
