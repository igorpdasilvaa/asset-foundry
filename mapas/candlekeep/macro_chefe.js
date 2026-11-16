// Macro (tipo Script): alterna a música de fundo de um lugar entre a de sempre e a do chefe final.
// 1º clique: a música do lugar vira a trilha do chefe. 2º clique: volta a de sempre.
// Troca o som de ambiente marcado como música do mapa (o mesmo para todos os jogadores na cena); os outros sons
// (vento, cântico) continuam. Para usar em outro lugar, mude MAPA (pasta do mapa em mapas/, ex.: "candlekeep_interno").
const MAPA = "candlekeep_patio";
const MUSICA = "mapas/candlekeep/musica/chefe.ogg";

const M = "interactive-assets";
if (!game.user.isGM) return ui.notifications.warn("Só o mestre troca a música.");
const cena = game.scenes.find(s => s.getFlag(M, "mapId") === MAPA);
if (!cena) return ui.notifications.error(`Não achei a cena do mapa "${MAPA}".`);
const som = cena.sounds.find(s => s.getFlag(M, "musica"));
if (!som) return ui.notifications.error(`${cena.name}: a cena não tem música de fundo.`);

const normal = som.getFlag(M, "musicaNormal");
if (normal) {
  await som.update({ path: normal, [`flags.${M}.-=musicaNormal`]: null });
  ui.notifications.info(`${cena.name}: de volta à música de sempre.`);
} else {
  // Modo desenvolvimento: último commit do GitHub; sem ele, o pacote instalado (traz os mapas desde a 0.12.0).
  const root = game.modules.get(M)?.api?.root ?? `modules/${M}`;
  await som.update({ path: `${root}/${MUSICA}`, [`flags.${M}.musicaNormal`]: som.path });
  ui.notifications.info(`${cena.name}: música do chefe final.`);
}
