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
2. Na camada de Tiles, clique com o botão direito na mesa: aparece um botão
   com o ícone 🔁 no HUD. Clicar alterna entre **Inteira** e **Quebrada**.

Também dá pra trocar por macro: `api.nextState(tile)` / `api.setState(tile, 1)`.

## Adicionar novos assets
Coloque os PNGs (todos os estados com o mesmo tamanho) em `assets/<nome>/`
e registre em `assets/assets.json`.

## Instalar pelo Foundry (Manifest URL)
Em **Add-on Modules → Install Module**, cole no campo *Manifest URL*:

```
https://github.com/igorpdasilvaa/asset-foundry/releases/latest/download/module.json
```

## Publicar nova versão
Atualize `version` no `module.json` e faça commit na `main`.
O GitHub Actions cria a tag e o release com o `.zip` automaticamente.
