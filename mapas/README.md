# Mapas

Mapas montados só com peças feitas neste repositório.

## Testar no Foundry
1. Junte este código na `main` (os arquivos são lidos do GitHub, não precisa atualizar o módulo).
2. Crie uma macro do tipo **Script**, cole o conteúdo de [`macro.js`](macro.js) e execute.
3. A macro cria a cena **Taverna (teste)** com fundo, lareira acesa, som de taverna e de fogo,
   paredes, portas e pilares quebráveis, e coloca mesas, tochas, barris e caixas do módulo.
   Com o modo desenvolvimento ligado, recarregue a página (F5) antes, para o módulo pegar a versão com mapas.

Cada execução cria uma cena nova. Para outro mapa, troque `MAPA` na macro.

## Como um mapa é feito
- `mapas/pecas/`: as peças. Pisos (`piso_madeira`, `piso_pedra`), `grama`, `terra` e `parede`
  são materiais que cobrem áreas inteiras sem emenda; `pilar`, `porta` e `lareira` são peças de
  1 quadrado. Gerar: `python3 tools/gen_pecas_mapa.py && NODE_PATH=$(npm root -g) node tools/render.js mapas/pecas/*.svg`
- `mapas/<nome>/layout.txt`: o desenho do mapa, um caractere por quadrado. A legenda fica em
  `mapa.json` (na taverna: `.` madeira, `,` pedra, `"` grama, `_` terra, `#` parede,
  `F` lareira, `P` pilar, `D` porta).
- `mapas/<nome>/mapa.json`: nome da cena, escuridão, legenda, objetos interativos soltos
  (`asset`, `x`, `y` no centro, em pixels da cena com grade de 100), luzes e sons.
- `python3 tools/gen_mapa.py <nome>` gera `<nome>.webp` (fundo, 200 px por quadrado),
  `cena.json` (cena do Foundry) e `previa.jpg` (a cena com os tokens, paredes do Foundry em vermelho
  e portas em amarelo).

Cada `#` vira um token "Parede de pedra", cada `D` uma "Porta de madeira" e cada `P` um
"Pilar de pedra", todos com vida. As paredes do Foundry não ficam no `cena.json`: o módulo
(`scripts/mapa.js`) calcula a partir do que está de pé, um pouco recuadas para dentro do bloco
(assim os jogadores conseguem mirar nele). Quando um bloco quebra, o buraco abre na hora.
`previa_quebrada.jpg` mostra o mapa com os blocos de `preview_broken` (no `mapa.json`) quebrados.
