# Ferramentas

- `render.js`: converte SVG em PNG transparente (Playwright/Chromium).
  `NODE_PATH=$(npm root -g) node tools/render.js arquivo.svg`
  Sem o Chromium do Playwright, `CHROME_PATH=/usr/bin/google-chrome` usa o Chrome instalado (o `NODE_PATH` também vale para os geradores).
- Animações (ex.: `mesa_queimando.webm`) são montadas a partir de quadros PNG com
  `ffmpeg -framerate 12 -i f%02d.png -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -b:v 0 -crf 32 saida.webm`
  (WebM VP9 com transparência, que o Foundry anima em tokens e tiles).
- `gen_estruturas.py`: parede, porta, pilar, barril e caixa (SVG) em `assets/<nome>/`.
- `gen_agua_veiculos.py`: água (1 quadrado, emenda com os vizinhos), carroça e barco, e a animação da água eletrificada.
- `gen_pecas_mapa.py` e `gen_mapa.py`: peças e montagem dos mapas (ver `mapas/README.md`).
  `paredes.mjs` calcula as paredes com o mesmo código do módulo para as prévias. `extras.py` leva saídas, NPCs,
  multidão, notas e proteções do `mapa.json` para a cena e para a prévia.
- `gen_tokens.py`: transforma um retrato gerado no `ia-orc` (SDXL) em token redondo com moldura de bronze e registra
  no `assets/npcs.json` (`--npc <id>` ou `--oficio <id> --especie <id> --genero m|f`). Os prompts e os jobs da fila ficam
  em `tokens_npcs.json`: o assunto vem antes de `estilo`, com `negativo` e o tamanho de `tamanho`.
- `foundry-login.mjs`: login no Foundry num Chrome dedicado (perfil `~/.config/foundry-chrome`, porta de debug só em localhost).
  Quem roda é o usuário. Primeira vez: `node tools/foundry-login.mjs --save` (pede URL, usuário e senha oculta e guarda
  no chaveiro do sistema ou em `~/.config/foundry-chrome/login.json` com permissão 600, nunca no repositório).
  Depois: `node tools/foundry-login.mjs`, sem digitar nada.
  Depois do login, a sessão fica viva nesse Chrome e pode ser usada via CDP (`http://127.0.0.1:9222`).
- `gen_construcao.py`, `gen_biblioteca.py`, `gen_oficios.py`: assets de Candlekeep (SVG em `assets/<id>/` e definições em
  `fragmentos/<grupo>.json`; `juntar_fragmentos.py` leva para o `assets.json`). `gen_pecas_mapa.py` também tem os materiais de Candlekeep (paralelepípedo, mármore, tapete,
  rocha vulcânica, telhados, muralha, vazio, azulejo, madeira escura) e a peça `escada`.
- `sons.json` + `gen_sons.py`: efeitos, ambiências, músicas e canções gerados no `ia-orc` (prompts no `sons.json`).
  `python3 tools/gen_sons.py <arquivo gerado> <nome>` corta o silêncio dos efeitos, emenda o fim no começo das ambiências e
  músicas (loop sem corte), normaliza o volume e salva em OGG (`assets/audio/` ou `mapas/candlekeep/musica/`).
  O `"estados"` do `sons.json` diz qual efeito cada estado toca; `juntar_fragmentos.py` aplica no `assets.json`.

## Arte pintada (ia-orc / SDXL), desde a 0.12.0
- `ia_assets.py` + `ia_assets.json` + `ia_receitas/<grupo>.json`: a arte de todos os assets (menos as árvores, que são fotos CC0).
  Cada receita aponta a imagem-base gerada no ia-orc (job + variação) e os estados são feitos a partir dela (fogo animado em
  WebM, carvão, cacos com a textura do objeto, gelo, água, ácido...). `python3 tools/ia_assets.py [asset ...]` regenera e
  atualiza o `src` dos estados no `assets.json` (com `--so-imagens` só gera as imagens). As imagens do ia-orc ficam em
  `~/Downloads/ia-orc/<job>/`; para refazer do zero, gere de novo com o prompt da receita.
- `gen_texturas.py` + `mapas/pecas/texturas/escolhas.json`: texturas pintadas e emendáveis dos materiais dos mapas
  (pisos, paredes, telhados, grama, água, vazio...). O `gen_mapa.py` usa a textura no lugar do SVG quando ela existe.
- `gen_jardim.py`: o jardim do Pátio do Ar (pintura do chão, poço e estátua de Alaundo).
- Legado: `gen_estruturas.py`, `gen_agua_veiculos.py`, `gen_armadilhas.py`, `gen_mesa_variantes.py`, `gen_construcao.py`,
  `gen_biblioteca.py` e `gen_oficios.py` desenhavam a arte antiga em SVG. Os fragmentos (`fragmentos/*.json`) continuam sendo
  a fonte das definições (estados, reações), mas não rode esses geradores de novo: eles voltariam o `src` para a arte antiga.
  As peças `pilar`, `porta`, `lareira` e `escada` de `mapas/pecas/` ainda são SVG.

