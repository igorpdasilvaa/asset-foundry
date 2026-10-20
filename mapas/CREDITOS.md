# Créditos das fotos dos mapas e das árvores

Todos os arquivos abaixo são **CC0 / domínio público**: podem ser usados, alterados e redistribuídos
(inclusive comercialmente) sem pedir permissão. O crédito não é obrigatório, mas fica registrado aqui.
Foram baixados pelo espelho [Tiddybub/2d-assets](https://github.com/Tiddybub/2d-assets), que guarda a página
de origem e a licença de cada pacote.

## Fotos de chão (`mapas/pecas/fotos/`)

Usadas pelos mapas com `"fotos"` no `mapa.json` (por enquanto, `lobisomens`).

| Arquivo | Origem | Licença |
|---|---|---|
| `grama_1.jpg` | [Ground Textures: gras364.jpg](https://opengameart.org/content/ground-textures-gras364jpg) | CC0 |
| `grama_seca.jpg` | [Ground Textures: halfdrygrass536.jpg](https://opengameart.org/content/ground-textures-halfdrygrass536jpg) | CC0 |
| `grama_pedras.jpg` | [Ground Textures: stonygrass.jpg](https://opengameart.org/content/ground-textures-stonygrassjpg) | CC0 |
| `grama_2.jpg`, `grama_3.jpg`, `trevo.jpg`, `terra.jpg`, `rocha.jpg`, `rocha_2.jpg`, `pedras.jpg` | `grass1`, `grass2`, `clover 1`, `dirt 1`, `rock 3`, `rock 4` e `stone 2` de [Wall, grass, rock, stone, wood and dirt (480)](https://opengameart.org/content/wall-grass-rock-stone-wood-and-dirt-480) | CC0 |

## Fontes das árvores (`tools/fontes/`)

`tools/gen_arvores.py` monta as árvores vistas de cima (`assets/arvore_grande/`, `assets/arvore_pequena/`)
com estas fotos. Os arbustos, pedras e o tronco caído dos mapas com fotos também saem delas.

| Arquivo | Origem | Autor | Licença |
|---|---|---|---|
| `galho.png` | [Leafy tree/plant branch](https://opengameart.org/content/leafy-treeplant-branch) (reduzido à metade) | OpenGameArt | CC0 |
| `casca.jpg` | `orig-brown-1024` de [Tree bark (close and far, 1024 and 2048)](https://opengameart.org/content/tree-bark-close-and-far-1024-and-2048) | OpenGameArt | CC0 |
| `fire_01.png`, `flame_02.png`, `flame_05.png`, `smoke_02.png`, `scorch_01.png` | [Particle Pack](https://kenney.nl/assets/particle-pack) | Kenney | CC0 |

## Sons, músicas e retratos gerados localmente
Os efeitos (`assets/audio/`, exceto `madeira_quebrando.ogg`), as ambiências, as músicas e canções de Candlekeep
(`mapas/candlekeep/musica/`) foram gerados neste projeto com Stable Audio 3 e ACE-Step 1.5. Os retratos dos NPCs
(`assets/npcs/`) foram gerados com SDXL. Tudo rodou no orquestrador local `ia-orc`, e os prompts estão em `tools/sons.json`
e `tools/tokens_npcs.json`. Antes de distribuir o módulo, confira a licença de cada modelo (o Stable Audio 3 segue a
licença comunitária da Stability AI).

