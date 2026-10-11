# Mapas

Mapas montados só com peças feitas neste repositório.

## Testar no Foundry
1. Junte este código na `main` (os arquivos são lidos do GitHub, não precisa atualizar o módulo).
2. Crie uma macro do tipo **Script**, cole o conteúdo de [`macro.js`](macro.js) e execute.
3. A macro cria a cena **Taverna (teste)** com fundo, lareira acesa, som de taverna e de fogo,
   paredes, portas e pilares quebráveis, e coloca mesas, tochas, barris e caixas do módulo.
   Com o modo desenvolvimento ligado, recarregue a página (F5) antes, para o módulo pegar a versão com mapas.

Cada execução cria uma cena nova. Para outro mapa, troque `MAPA` na macro: `"lago"` monta o
**Lago (teste)**, com água que congela, eletrifica e envenena, píer, barco a remo e uma carroça carregada.
`"emboscada"` monta a **Emboscada na estrada (teste)**: uma carroça parada por um tronco caído na estrada,
entre dois morros com penhascos. Para chegar no alto é preciso escalar, subir encosta e mato (terreno difícil)
ou ir pelas trilhas, que têm armadilhas escondidas. Lá em cima há pedregulhos prontos para rolar na estrada.
`previa_mestre.jpg` mostra as alturas, o terreno difícil, os penhascos (vermelho), as armadilhas e para onde
cada pedregulho rola.

## Como um mapa é feito
- `mapas/pecas/`: as peças. Pisos (`piso_madeira`, `piso_pedra`), `grama`, `terra` e `parede`
  são materiais que cobrem áreas inteiras sem emenda; `pilar`, `porta` e `lareira` são peças de
  1 quadrado. Gerar: `python3 tools/gen_pecas_mapa.py && NODE_PATH=$(npm root -g) node tools/render.js mapas/pecas/*.svg`
- `mapas/<nome>/layout.txt`: o desenho do mapa, um caractere por quadrado. A legenda fica em
  `mapa.json` (na taverna: `.` madeira, `,` pedra, `"` grama, `_` terra, `#` parede,
  `F` lareira, `P` pilar, `D` porta; no lago também `~` água e `=` píer).
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
Cada `~` vira um token "Água". `preview_states` gera prévias com estados trocados (ex.: lago congelado).

### Mapas com relevo (`tools/gen_relevo.py`)
- `mapas/<nome>/altura.txt`: um dígito por quadrado, do mesmo tamanho do `layout.txt`; cada ponto vale
  `step` pés (5 no `mapa.json`). Vizinhos com 1 ponto de diferença são encosta (subir custa mais
  movimento, menos na trilha); com 2 ou mais, penhasco (só escalando).
- Legenda do layout: `"` grama, `_` estrada, `t` trilha, `%` cascalho, `:` mato, `^` borda rochosa,
  `T` árvore, `R` pedra, `=` tronco caído. Árvores e pedras bloqueiam movimento (paredes do Foundry,
  mas sem bloquear visão).
- `mapa.json`: `difficult` diz o tipo de terreno difícil de cada categoria (`plants`, `rocks`...),
  `climbDC` a CD de escalar. Objetos aceitam `"hidden": true` (armadilhas) e `"flags"`: `link` liga o fio
  ao pedregulho (quadrado `{x, y}`), `roll` é onde o pedregulho para.
- `python3 tools/gen_relevo.py <nome>` gera o fundo (sombreado, curvas de nível, penhascos, árvores),
  `cena.json` com a altura e as regiões de terreno difícil, `previa.jpg` e `previa_mestre.jpg`.
