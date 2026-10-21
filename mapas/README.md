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
`"lobisomens"` monta **Caminho do Leão: a caçada (lobisomens)**: 300 pés de estrada serpenteando entre dois morros,
no crepúsculo. O alto só se alcança escalando os penhascos ou subindo as três encostas (não há trilhas), e as encostas,
as margens da estrada e o alto estão cheios de armadilhas (19) e pedregulhos (7). As árvores são interativas, e o
chão, as pedras e o mato são feitos com fotos CC0. A trilha de combate `cacada_loop.ogg` toca em loop no mapa inteiro.
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
- `"fotos"` no `mapa.json` troca as texturas desenhadas por fotos CC0 de `mapas/pecas/fotos/` (créditos em
  [`CREDITOS.md`](CREDITOS.md)): cada material (`grama`, `estrada`, `rocha`, `cascalho`, `alto`) é uma lista de fotos
  misturadas em manchas. Arbustos, pedras e o tronco caído passam a ser feitos com as fotos de `tools/fontes/`.
- Na legenda, `arvore_grande` e `arvore_pequena` viram árvores interativas (tokens do módulo) centradas no quadrado.
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

### Cidades, saídas, NPCs e proteções (`tools/extras.py`, nos dois geradores)
- `mapas/<cidade>/cidade.json`: `{ "name", "mapas": [...], "inicio"? }`. A macro com `MAPA = "<cidade>"` monta tudo.
- `"saidas"` (em quadrados): `{ "id", "nome", "x", "y", "w", "h", "pouso": { "x", "y", "w", "h" }, "para", "chegada", "perguntar"? }`.
  O retângulo leva ao `pouso` da saída `chegada` do mapa `para` (pode ser o próprio mapa, para escadas). O `pouso` fica fora
  da saída. Montado sozinho, o mapa cria as regiões, mas a saída para outro mapa fica sem destino.
- `"npcs"`: `{ "npc", "x", "y" }` (pixels, centro), com os ids de `assets/npcs.json`.
- `"multidao"`: `{ "area": [x, y, w, h], "n", "oficios": [...] }`: plebeus sorteados nos quadrados livres da área
  (sem paredes, objetos, água, saídas nem chegadas).
- `"notas"`: `{ "x", "y", "titulo", "texto" }` viram páginas de um diário só do mestre, com alfinetes no mapa.
- `"protecoes"`: `true` ou `{ "alarme": 1, "resposta": [{ "npc": "avowed_mago", "n": 4 }] }` (fogo abafado e alarme).
- `"px"`: pixels por quadrado no fundo (padrão 200); mapas grandes usam menos.
- A prévia desenha as saídas (azul), as chegadas (verde), os NPCs nomeados (círculo com a inicial), a multidão (laranja)
  e as notas.

### Legenda com propriedades e mapas grandes
- Na legenda, um caractere pode apontar para um objeto em vez de um nome:
  `{ "nome", "chao"?, "peca"?, "rot"?, "asset"?, "kind"?, "solido"? }`. `chao` é o material desenhado (padrão: o nome),
  `peca` uma peça de `mapas/pecas/` por cima (ex.: `escada`, girada `rot` graus), `asset` + `kind` faz o quadrado virar token
  de estrutura (ex.: `{"nome": "portao", "chao": "muralha", "asset": "portao", "kind": "door"}`) e `solido` bloqueia sem token
  (ex.: `{"nome": "muralha_fixa", "chao": "muralha", "solido": true}` para trechos de muralha que ninguém alcança).
- Já são sólidos sem token: `telhado_ardosia`, `telhado_telha` (prédios vistos de fora), `vazio` (em volta de andares e
  demiplanos) e `lareira`. A `muralha` vira token de parede como `parede`.
- Paredes encostadas no `vazio` ficam fixas (`"vazio_fixo": false` desliga), para não encher a cena de tokens que não levam a lugar nenhum.
- Mapas com mais de 2000 quadrados desenham cada material só no retângulo onde ele aparece (`"recorte"` força ligado ou desligado):
  o Chrome não aguenta os filtros de textura no tamanho do mapa inteiro.
- Portas lado a lado (o portão de 4 quadrados) contam umas às outras como batente.

### Candlekeep
`MAPA = "candlekeep"` monta os 10 mapas da cidade e o Caminho do Leão (lobisomens), começando pelo Portão:
`candlekeep_portao` → `candlekeep_patio` (Pátio do Ar) → Hearth, Casa do Repouso, Banhos, Casa do Encadernador, Pilares da
Pedagogia (3 torres), Templo de Oghma, Erudite Outfitters e Ferraria e Estábulos. Lore, NPCs e decisões em
[`candlekeep/PLANO.md`](candlekeep/PLANO.md). Todos os mapas têm proteções (fogo abafado e alarme com 1 arquimago e 4 magos).
- `"pinturas"`: `[{ "img", "x", "y", "w", "h", "borda"? }]` aplica uma imagem pronta sobre o chão de uma área (em quadrados),
  com a borda esfumada. O jardim do Pátio do Ar é uma pintura gerada no ia-orc (`tools/gen_jardim.py`).

