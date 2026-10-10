# Interactive Assets (POC)

Assets com mais de um estado (ex.: mesa inteira / quebrada) para Foundry VTT v12–v13.

## Instalar
Copie a pasta `interactive-assets` para `Data/modules/` do Foundry
(no Mac: `~/Library/Application Support/FoundryVTT/Data/modules/`),
reinicie o Foundry e ative o módulo no mundo (Manage Modules).

## Usar
1. Crie uma macro do tipo **Script** com:
   ```js
   game.modules.get("interactive-assets").api.placeAsset("mesa");
   ```
   Executar a macro coloca a mesa no centro da tela.
2. A mesa entra como **Token** com CA 0 e 10 PV (ator "Mesa de madeira", pasta
   *Interactive Assets*). Cada mesa colocada tem a própria vida. Depois que o
   ator existe, também dá pra simplesmente arrastá-lo da barra de Atores para a cena.
3. Mire na mesa e ataque normalmente pelo dnd5e. O dano é aplicado sozinho
   (configurável em *Configure Settings*) e, ao chegar a 0 PV, a imagem troca
   para **Quebrada**. Curar acima de 0 volta para **Inteira**.
4. O GM também pode trocar o estado pelo botão 🔁 no HUD do token
   (quebrada = 0 PV, inteira = PV cheio).

Assets sem `actor` no `assets.json` continuam virando Tile, com o mesmo botão no HUD.

Também dá pra trocar por macro: `api.nextState(tile)` / `api.setState(tile, 1)`.

## Modo desenvolvimento (testar sem atualizar o módulo)

Em **Configurar Configurações → Interactive Assets**, ligue **Modo desenvolvimento (GitHub)**.
Com ele ligado, cada recarregamento da página (F5) busca o código e as imagens do último commit
da branch `main` no GitHub (via jsDelivr), sem precisar apertar Atualizar no setup.

- Mudanças no `module.json` (nome, versão, novos arquivos de estilo) ainda pedem atualização normal.
- O GitHub permite 60 consultas por hora por IP; se passar disso ou o GitHub cair, o módulo usa a versão instalada e avisa.
- Desligar o modo volta para os arquivos instalados; tokens já na cena trocam as imagens sozinhos.

## O que jogadores podem fazer

Cada asset diz no `assets.json`, em `"player"`, o que os jogadores podem fazer:

- `"move": true` deixa o jogador mover o token (ele vira dono do ator, sem visão).
- `"toggle": ["acesa", "apagada"]` mostra no HUD do jogador um botão que alterna só entre esses estados.

Todo o resto (vida, imagem, estados, apagar o ator) fica com o GM ou com o dano de combate.
Hoje a mesa só pode ser movida, e a tocha pode ser movida e acesa/apagada.

## Mesa: reações por tipo de dano
CA 0, 10 PV, imune a veneno e psíquico, resistente a perfurante.

| Dano | Efeito |
|---|---|
| Fogo / Raio | Pega fogo: 2 de fogo por rodada (ou a cada 6 s fora de combate). Congelada, descongela. |
| Gelo | Congela. Se estiver pegando fogo, apaga (fica chamuscada). |
| Concussão / Trovão / Força em mesa congelada | Estilhaça na hora. |
| Ácido | Corroída: 1 de ácido por rodada, por 3 rodadas. |
| Necrótico | Apodrece e perde PV máximo igual ao dano. |
| Radiante | Brilha (luz) por 10 rodadas / 1 minuto e depois volta ao normal. |
| Perfurante | Fica com flechas cravadas (e leva metade do dano). |
| Trovão / Força | Empurra a mesa 1 quadrado para longe de quem atacou. |

Chegando a 0 PV: queimando ou fogo → queimada; congelada ou gelo → estilhaçada;
cortante → cortada ao meio; outros → quebrada. O botão 🔁 do HUD passa por todos os estados.

Tudo isso está em `assets.json` (`reactions`, `onZero`, e `dot`/`ticks`/`then`/`sticky` nos estados),
então outros objetos podem ter regras próprias sem mexer no código.

## NPC de teste
Ao abrir o mundo, o GM ganha o NPC **Testador de Dano** (pasta *Interactive Assets*), com um ataque
para cada tipo de dano (Ácido, Concussão, Gelo, Fogo, Força, Raio, Necrótico, Perfurante, Veneno,
Psíquico, Radiante, Cortante, Trovão). Cada ataque sempre acerta e causa 1 de dano.
Coloque o NPC na cena, mire na mesa e use o ataque do tipo que quer testar.
Dá para desligar em *Configure Settings* → "Criar NPC de teste".

## Tocha (luz + som)
Arraste o ator **Tocha** (pasta *Interactive Assets*) para a cena. Acesa, ela ilumina
(20 ft de luz forte, 40 ft de penumbra, com animação de chama) e toca um som de fogo
em loop num raio de 30 ft. Ao mover o token, luz e som vão junto. O botão 🔁 no HUD
apaga/acende (desliga luz e som).

## Adicionar novos assets
Tudo fica neste mesmo módulo: coloque os arquivos em `assets/<nome>/` e registre
o asset em `assets/assets.json`. Cada estado aceita:

- `src`: imagem do estado (todas com o mesmo tamanho)
- `light`: luz do token naquele estado (mesmos campos da aba Light do token)
- `sound`: `{ "src", "radius", "volume" }` som ambiente que segue o token
- `broken: true`: estado usado quando a vida chega a 0

Com `"actor": {}` o asset vira um token (arrastável da barra de Atores). Com
`"actor": { "ac", "hp" }` ele também tem vida e quebra com dano. Sem `actor`, vira Tile.
Ao abrir o mundo, o GM cria/atualiza sozinho o ator de cada asset.

## Instalar pelo Foundry (Manifest URL)
Em **Add-on Modules → Install Module**, cole no campo *Manifest URL*:

```
https://github.com/igorpdasilvaa/asset-foundry/releases/latest/download/module.json
```

## Publicar nova versão
Atualize `version` no `module.json` e faça commit na `main`.
O GitHub Actions cria a tag e o release com o `.zip` automaticamente.
