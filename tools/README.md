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

