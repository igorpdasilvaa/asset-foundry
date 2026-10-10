# Mapas

Mapas montados só com peças feitas neste repositório.

## Testar no Foundry
1. Junte este código na `main` (os arquivos são lidos do GitHub, não precisa atualizar o módulo).
2. Crie uma macro do tipo **Script**, cole o conteúdo de [`macro.js`](macro.js) e execute.
3. A macro cria a cena **Taverna (teste)** com fundo, paredes, portas, lareira acesa, som de
   taverna e de fogo, e coloca 3 mesas e 3 tochas do módulo Interactive Assets.

Cada execução cria uma cena nova. Para outro mapa, troque `MAPA` na macro.

## Como um mapa é feito
- `mapas/pecas/`: as peças. Pisos (`piso_madeira`, `piso_pedra`), `grama`, `terra` e `parede`
  são materiais que cobrem áreas inteiras sem emenda; `pilar`, `porta` e `lareira` são peças de
  1 quadrado. Gerar: `python3 tools/gen_pecas_mapa.py && NODE_PATH=$(npm root -g) node tools/render.js mapas/pecas/*.svg`
- `mapas/<nome>/layout.txt`: o desenho do mapa, um caractere por quadrado. A legenda fica em
  `mapa.json` (na taverna: `.` madeira, `,` pedra, `"` grama, `_` terra, `#` parede,
  `F` lareira, `P` pilar, `D` porta).
- `mapas/<nome>/mapa.json`: nome da cena, escuridão, legenda, objetos interativos
  (`asset`, `x`, `y` no centro, em pixels da cena com grade de 100), luzes e sons.
- `python3 tools/gen_mapa.py <nome>` gera `<nome>.webp` (fundo, 200 px por quadrado),
  `cena.json` (cena do Foundry) e `previa.jpg` (fundo com paredes em vermelho, portas em amarelo
  e objetos em azul).

As paredes do Foundry saem sozinhas do layout: toda borda entre parede e chão vira parede que
bloqueia visão e movimento, cada `D` vira uma porta que abre e fecha, e cada pilar ganha um
octógono de paredes em volta.
