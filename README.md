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
  A macro dos mapas usa o mesmo commit que o módulo carregou e, sem ele, lê os arquivos direto do repositório,
  então funciona mesmo com o limite estourado (mantenha o módulo instalado atualizado para esse caso).
- Desligar o modo volta para os arquivos instalados; tokens já na cena trocam as imagens sozinhos.

## O que jogadores podem fazer

Cada asset diz no `assets.json`, em `"player"`, o que os jogadores podem fazer:

- `"move": true` deixa o jogador mover o token (ele vira dono do ator, sem visão).
- `"toggle": ["acesa", "apagada"]` mostra no HUD do jogador um botão que alterna só entre esses estados.

Todo o resto (vida, imagem, estados, apagar o ator) fica com o GM ou com o dano de combate.
Se o asset não tem `"move"`, o jogador não consegue arrastar o token.
Hoje mesa, barril e caixa só podem ser movidos, a tocha pode ser movida e acesa/apagada,
a porta pode ser aberta e fechada (pelo HUD ou pela porta do Foundry), mas não movida,
e carroça e barco podem ser movidos levando quem está em cima.

## Pastas

Os atores ficam na aba de Atores em:

```
Interactive Assets/
├─ Móveis/      Jogador · Mestre · Armadilhas
└─ Imóveis/     Jogador · Mestre · Armadilhas
```

Cada asset escolhe a sua no `assets.json`:

- `"tipo"`: `"movel"` (se carrega ou empurra durante a cena) ou `"imovel"` (parte do cenário).
- `"interacao"`: `"jogador"` (o jogador faz algo sozinho: mover, acender, abrir), `"mestre"`
  (só o GM, além do dano de combate) ou `"armadilha"` (escondida e controlada pelo GM, disparada pelo jogador).

As imagens continuam em `assets/<asset>/`; mudar a categoria só troca a pasta no Foundry
(o ator muda de pasta sozinho no próximo F5) e não quebra cenas salvas.
Assets sem `actor` viram Tile e não aparecem na aba de Atores.

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

## Construção quebrável (parede, porta, pilar) e barris/caixas
Os mapas de `mapas/` são montados com estruturas que quebram de verdade:

| Asset | CA / PV | Observação |
|---|---|---|
| Parede de pedra (1 bloco de 5 ft) | 17 / 40 | Resiste a perfurante e cortante; imune a veneno, psíquico, necrótico e radiante. Concussão/trovão/força racham. A 0 PV desmorona e abre um buraco por onde dá para passar e ver. |
| Porta de madeira (dupla) | 15 / 18 | Abrir/fechar pela porta do Foundry troca a imagem. Fogo/raio põe fogo (2 de fogo por rodada). A 0 PV é arrombada (ou queima) e a passagem fica livre. |
| Pilar de pedra | 17 / 50 | Mesmas resistências da parede. A 0 PV desmorona e deixa de bloquear visão. |
| Barril / Caixa de madeira | 15 / 10 e 8 | Jogadores podem empurrar. Fogo põe fogo; a 0 PV quebram (ou viram cinzas). |

As paredes do Foundry são recalculadas sozinhas (`scripts/mapa.js`) a partir dos blocos de pé:
quando um bloco quebra, o buraco se abre e as bordas dele viram parede; curar o bloco (ou
voltar o estado no HUD) fecha de novo. Estados com `"door": "open"/"closed"` seguem a porta do
Foundry, e `"sfx"` toca um som ao entrar no estado (madeira quebrando, por exemplo).

## Árvores (grande e pequena)
Ficam em *Imóveis / Mestre*. As imagens são montadas a partir de fotos CC0 (`tools/gen_arvores.py`, créditos em
[`mapas/CREDITOS.md`](mapas/CREDITOS.md)). O tronco bloqueia movimento, mas não a visão (dá para ver por baixo da copa).

| Asset | Tamanho | CA / PV | Observação |
|---|---|---|---|
| Árvore grande | 3 x 3 | 13 / 45 | Fogo pega de 5 em 5 por rodada |
| Árvore pequena | 1 x 1 | 12 / 15 | Fogo pega de 3 em 3 por rodada |

| Dano | Efeito |
|---|---|
| Fogo / Raio | Pega fogo (luz e som de fogo). A 0 PV vira só o tronco preto, que continua bloqueando. |
| Gelo numa árvore pegando fogo | Apaga; fica chamuscada. |
| Outros, a 0 PV | Desaba: sobra o toco e o tronco caído, e a passagem fica livre. |

Resistentes a perfurante, imunes a veneno e psíquico. Nos mapas, as árvores entram giradas ao acaso para não
ficarem todas iguais; o GM pode arrastar uma árvore e o tronco vai junto.

## Água (lago)
Cada quadrado de água é um token "Água" (pasta *Imóveis / Mestre*), montado pelo mapa como as paredes.
A água não tem vida: ela só reage ao tipo do dano quando é alvo de um ataque ou magia, e a mudança se
espalha pela água ligada.

| Dano | Efeito |
|---|---|
| Gelo | Congela o quadrado e os vizinhos. Dá para andar por cima; o barco fica preso. |
| Fogo | Derrete o gelo. Na água solta vapor por 3 rodadas (visão prejudicada). |
| Concussão / Trovão / Força no gelo | Parte o gelo daquele quadrado. |
| Raio | Eletrifica o lago inteiro (o gelo não conduz) e todo mundo dentro da água leva o mesmo dano de raio. Quem está num barco não leva. |
| Veneno / Ácido | Envenena o quadrado e os vizinhos por 10 rodadas: 1 de veneno por rodada em quem estiver dentro. |
| Radiante na água envenenada | Purifica. |

Objetos pegando fogo (mesa, barril, caixa, porta) e a tocha acesa se apagam ao entrar na água.

## Veículos (carroça e barco)
Ficam em *Móveis / Jogador*: os jogadores podem mover. Tudo que está em cima do veículo
(o centro do token dentro dele) anda junto: personagens, barris, caixas. Para embarcar, é só
colocar o token em cima; o chat avisa quem sobe, desce ou pula na água.

| Asset | CA / PV | Observação |
|---|---|---|
| Carroça (2 x 3) | 11 / 30 | Não entra na água, mas passa por cima do gelo. Abaixo da metade da vida, concussão/corte/trovão/força quebram uma roda e ela trava. Pega fogo; a 0 PV queima ou se desmancha. |
| Barco a remo (4 x 2) | 11 / 40 | Só navega em água livre (o gelo prende). Abaixo da metade, um golpe abre um rombo e ele faz água. Pega fogo; a 0 PV afunda ou queima, e quem estava a bordo cai na água. |

Trovão e força empurram o veículo 1 quadrado, com quem está em cima. O GM pode mover para qualquer lugar.
No `assets.json`: `"vehicle": { "terreno": "agua" | "terra" }`, estados com `"travado": true` não andam,
e regras com `"below": 0.5` só valem com metade da vida ou menos. Na água, `"spread"` (quadrados ou `"all"`)
e `"zap"` nas regras, e `"wet"`, `"gelo"`, `"areaDot"` e `"oculto"` nos estados (`"oculto"`: o token não é
desenhado, porque a água calma já está pintada no fundo do mapa; só os quadrados que mudam de estado aparecem).

## Tokens dentro de um template
- Ao colocar um template (bola de fogo, cone, linha...), os tokens dentro dele viram seus alvos.
  Dá para desligar em *Configurações > Alvos automáticos nos templates* (vale para cada usuário).
- **Alt+T** com o mouse sobre um template, ou o botão *Selecionar tokens no template* nas ferramentas de
  template: seleciona e marca como alvo todos os tokens dentro, prontos para aplicar o dano pelo chat.
- Conta como dentro o token com qualquer quadrado destacado pelo template. Quadrados de água viram alvo
  (para reagirem ao dano), mas não são selecionados.

## Relevo, armadilhas e pedregulhos (mapa da emboscada)
Mapas com relevo guardam a altura de cada quadrado na cena (o mapa **Emboscada na estrada** tem dois
morros com penhascos virados para a estrada). O módulo usa essa altura assim:

- **Altura do token**: quem anda fica na altura do chão de cada quadrado (o *elevation* do token muda sozinho).
  Voando, nada muda.
- **Subir custa movimento** (a régua já mostra o custo): cada 5 pés de encosta subidos custam 5 pés a mais;
  descer é normal. Na trilha, subir não custa extra. Mato fechado, cascalho solto e o tronco caído são
  terreno difícil (regiões do dnd5e).
- **Penhasco** (10 pés ou mais entre dois quadrados): andando, o jogador não passa. Escolha a ação de
  movimento **Escalar** (botão direito no token, ícone de movimento no HUD): cada pé de altura custa 2, subindo ou descendo, além do passo (que escalando já
  custa o dobro). O penhasco de 15 pés custa 40 pés de movimento e o de 10 pés, 30. O chat pede um teste
  de Atletismo (se falhar, cai). Para descer rápido, **Pular**: não
  custa extra, mas cai (1d6 de concussão a cada 10 pés, aplicado na hora) e fica caído. O GM move para
  qualquer lugar.
- **Armadilhas** (*Imóveis / Armadilha*), escondidas no mapa: quem passa por cima para no quadrado, a
  armadilha aparece e o chat mostra o teste e o dano para clicar. Tokens hostis (os bandidos que armaram)
  passam sem disparar.

| Asset | Ao disparar |
|---|---|
| Armadilha de urso | Fecha. Destreza CD 13, 2d4 perfurante e preso (Atletismo CD 13 para soltar). |
| Fosso camuflado | Abre: o chão vira -10 pés e quem caiu desce junto. Destreza CD 12 para se agarrar; 1d6 + 1d4 das estacas. |
| Fio de tropeço | Arrebenta e solta o pedregulho ligado a ele (flag `link`). |

- **Pedregulho** (*Móveis / Mestre*): rola quando o fio dispara, quando leva dano de concussão, trovão ou
  força (um empurrão), ou quando o GM troca o estado para *Rolou*. Vai até o quadrado da flag `roll`, deixa o
  rastro como um template de linha e marca como alvo quem estava no caminho; o chat pede Destreza CD 14 e
  3d10 de concussão. No mapa, os bandidos podem derrubar pedregulhos do alto dos penhascos na estrada.

No `assets.json`: `"trap": { "to", "say", "roll" }` e estados com `"armed": true` (armada) e
`"altura"` (muda o chão do quadrado, em pés); `"boulder": { "dc", "damage" }` e estados com `"rolls": true`.

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
