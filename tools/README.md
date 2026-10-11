# Ferramentas

- `render.js`: converte SVG em PNG transparente (Playwright/Chromium).
  `NODE_PATH=$(npm root -g) node tools/render.js arquivo.svg`
- Animações (ex.: `mesa_queimando.webm`) são montadas a partir de quadros PNG com
  `ffmpeg -framerate 12 -i f%02d.png -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -b:v 0 -crf 32 saida.webm`
  (WebM VP9 com transparência, que o Foundry anima em tokens e tiles).
- `gen_estruturas.py`: parede, porta, pilar, barril e caixa (SVG) em `assets/<nome>/`.
- `gen_agua_veiculos.py`: água (1 quadrado, emenda com os vizinhos), carroça e barco, e a animação da água eletrificada.
- `gen_pecas_mapa.py` e `gen_mapa.py`: peças e montagem dos mapas (ver `mapas/README.md`).
  `paredes.mjs` calcula as paredes com o mesmo código do módulo para as prévias.
