# Ferramentas

- `render.js`: converte SVG em PNG transparente (Playwright/Chromium).
  `NODE_PATH=$(npm root -g) node tools/render.js arquivo.svg`
- Animações (ex.: `mesa_queimando.webm`) são montadas a partir de quadros PNG com
  `ffmpeg -framerate 12 -i f%02d.png -c:v libvpx-vp9 -pix_fmt yuva420p -auto-alt-ref 0 -b:v 0 -crf 32 saida.webm`
  (WebM VP9 com transparência, que o Foundry anima em tokens e tiles).
