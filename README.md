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

## Mesa pegando fogo
- Dano de **fogo** com a mesa ainda de pé: ela começa a pegar fogo (imagem, luz e som de fogo).
- Queimando, ela leva **2 de dano de fogo** a cada nova rodada de combate na cena, ou a cada
  **6 segundos** fora de combate (o relógio para quando o jogo está pausado).
- Chegando a 0 PV queimando (ou com o golpe final de fogo): vira **mesa queimada**.
  Chegando a 0 PV com outro dano: vira **mesa quebrada**.
- O botão 🔁 no HUD passa por Inteira → Quebrada → Pegando fogo → Queimada.

Isso é configurado em `assets.json` com `"burn"` no asset e `burning` / `burnt` nos estados,
então outros objetos inflamáveis podem reaproveitar a mesma regra.

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
