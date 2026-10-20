# Candlekeep: plano da cidade interativa

Plano para montar Candlekeep como um conjunto de mapas ligados, no mesmo padrão dos mapas deste módulo:
`layout.txt` + `mapa.json` → `cena.json`, construção quebrável, objetos interativos e relevo.
Os jogadores andam com os tokens, entram nos estabelecimentos por portas que levam a outras cenas e
podem quebrar, queimar, empurrar e acender o que estiver no caminho.

Marcação usada no plano:
- **[CM]**: lore oficial de *Candlekeep Mysteries* (2021, 1492 DR), que continua sendo a versão atual.
- **[nosso]**: decisão nossa onde a lore não diz nada (nomes, plantas, tamanhos). Dá para trocar.

---

## 1. Resumo da lore usada (1492 DR)

**Onde fica.** Fortaleza-biblioteca num rochedo vulcânico de uma península estreita, sobre o Mar das Espadas,
uns 190 km ao sul de Baldur's Gate. A única estrada é o **Caminho do Leão**, que sai do Caminho da Costa.
O mapa dos lobisomens (`mapas/lobisomens`) já é esse caminho, então ele vira o mapa anterior à entrada. **[CM]**

**Aparência.** Muralhas de pedra e ferro com 50 pés de altura. Dezenas de torres de alturas e estilos diferentes
("um bolo com velas demais"). O lado do mar, a oeste, pega névoa e borrifo e congela no inverno. **[CM]**

**Entrada.** Portão duplo enorme, virado para leste, de um metal negro estranho, com o brasão de Candlekeep
(um castelo com chamas no alto de cada torre). Para entrar, o visitante doa **uma obra escrita que a biblioteca ainda não tenha**:
pode ser um diário, uma balada ou uma receita. Cinco sacerdotes Avowed de Deneir guardam o portão, e quem manda neles é o
**Guardião do Portão, Kalan Strongbranch** (arquimago). A troca da guarda acontece nos sinos do amanhecer, do meio-dia e do pôr do sol. **[CM]**

**Duas entradas controladas.**
1. O **portão principal** leva ao **Pátio do Ar**. Visitantes ("buscadores") podem circular lá.
2. A **Porta Esmeralda**, no fim oeste do Pátio, leva ao **Pátio Interno**, onde ficam a Grande Biblioteca e a Exaltação.
   Ela tem 15 pés de altura, é de pedra verde translúcida que brilha por dentro, está trancada com *arcane lock* e
   protegida contra qualquer dano. Só passa quem tem uma **carta de admissão** selada pelo Guardião dos Tomos,
   pelo Primeiro Leitor ou por um Grande Leitor, e ela vale por um decêndio. **[CM]**

**Ordens de Concordância** (as regras do visitante): não brigar, não roubar, não copiar (cópias se encomendam na
Casa do Encadernador) e não danificar nenhuma obra. A lei maior é "quem destrói conhecimento, com tinta, fogo ou espada,
será destruído". A pena é o banimento. **[CM]**

**Proteções mágicas** **[CM]**
- Ninguém entra por teleporte nem por magia, só pelo portão. Sair por magia é permitido.
- Qualquer chama maior que uma vela é apagada, e *bola de fogo* e afins falham. A única exceção é a lareira do Hearth.
- Uma obra do acervo que sai da fortaleza some e reaparece no lugar.
- O Guardião dos Tomos pode erguer o **Grande Escudo** (mythal): só ar e som passam.
- Em caso de briga, **1 arquimago e 4 magos** aparecem na hora, e mais 4 arquimagos se precisar.

**Hierarquia dos Avowed** (cerca de 300 membros, quase todos plebeus devotos de Deneir e Oghma) **[CM]**
- **Guardião dos Tomos**: governa.
- **Primeiro Leitor**: adquire as obras.
- **8 Grandes Leitores**: cada um especialista numa área, cuidam do dia a dia.
- **Leitores Mestres**: supervisionam os escribas.
- **Cantor**: conduz o **Cântico Sem Fim** das profecias de Alaundo, dia e noite, em procissão pelo Pátio.
- **Guardião do Portão** e **Guardião da Porta Esmeralda**.
- **Adjuntos Avowed**: guias que buscam os livros para os visitantes.

---

## 2. Mapas e como se ligam

```
Caminho do Leão (lobisomens, já existe)
        │ estrada
        ▼
[1] Portão de Candlekeep ──portão──▶ [2] Pátio do Ar (mapa geral)
                                        ├─▶ [3] Hearth (taverna) ──portas──▶ salas e santuários extradimensionais
                                        ├─▶ [4] Casa do Repouso (3 andares) ──alçapão──▶ (fase 5) Porão dos Vaga-lumes
                                        ├─▶ [5] Casa de Banho e Vapor
                                        ├─▶ [6] Casa do Encadernador
                                        ├─▶ [7] Pilares da Pedagogia (torres de leitura)
                                        ├─▶ [8] Templo de Oghma
                                        ├─▶ [9] Erudite Outfitters & Clothiers (alfaiataria)
                                        ├─▶ [10] Ferraria e Estábulos
                                        └─▶ Porta Esmeralda ──carta──▶ (fase 5) [11] Pátio Interno, Grande Biblioteca,
                                                                        Exaltação, [12] subterrâneo (catacumbas, cofres, Miirym)
```

Tamanhos em quadrados de 5 pés. São estimativas **[nosso]**, porque o mapa-pôster de CM não está no repositório.
Se você tiver o livro, a planta oficial pode guiar os `layout.txt`.

| # | Mapa (pasta) | Tamanho | Gerador | O que tem |
|---|---|---|---|---|
| 1 | `candlekeep_portao` | 48 x 36 | `gen_relevo.py` | O fim do Caminho do Leão subindo o rochedo, com penhasco e o mar ao sul. Muralha, duas torres, o portão negro, a guarita com a sala do tributo (mesa onde o livro é examinado), a fila de buscadores e as carroças de caravana. Do lado de dentro, uma faixa do Pátio com a saída para o mapa 2. |
| 2 | `candlekeep_patio` | 80 x 56 | `gen_mapa.py` (+ relevo leve) | O Pátio do Ar, de paralelepípedo. Os prédios aparecem como telhados, e as portas levam aos interiores. Tem a muralha externa e a Porta Esmeralda a oeste, com as torres do Pátio Interno ao fundo (só telhado, sem entrada). Um poço, bancos, carroças, barris e a rota da procissão do Cântico. As gárgulas do Templo ficam nos beirais. |
| 3 | `candlekeep_hearth` | 40 x 26 | `gen_mapa.py` | O salão (3x maior por dentro), o balcão de 20 lugares, mesas redondas e compridas, a fogueira central acesa, a lareira e uma dúzia de poltronas. O **amplificador geométrico** fica sobre o balcão. Num fundo escuro (o "vazio"), 5 salas de 6 x 6: 2 salas de reunião e os santuários de Deneir, Gond e Milil. |
| 4 | `candlekeep_repouso` | 64 x 18 | `gen_mapa.py` | 3 andares lado a lado ligados por escadas. Térreo: recepção e quarto comum. 1º e 2º: quartos privados e coletivos. No térreo, o alçapão laranja para o Porão dos Vaga-lumes (fase 5). |
| 5 | `candlekeep_banhos` | 24 x 18 | `gen_mapa.py` | Piscinas termais (água que já solta vapor), saunas (área de visão prejudicada) e salas de massagem. |
| 6 | `candlekeep_encadernador` | 22 x 16 | `gen_mapa.py` | O balcão de encomendas, o scriptorium com escrivaninhas, a oficina de encadernação com prensa, e o depósito de papel e couro. |
| 7 | `candlekeep_pilares` | 48 x 20 | `gen_mapa.py` | 3 torres de topo plano, 2 andares cada, lado a lado. As salas de leitura privadas têm *silêncio* permanente (região sem som). |
| 8 | `candlekeep_templo` | 18 x 24 | `gen_mapa.py` | A nave, o altar de Oghma e o campanário com o sino de bronze. |
| 9 | `candlekeep_alfaiataria` | 18 x 14 | `gen_mapa.py` | A loja, a oficina com teares e rolos de tecido, e o átrio dos bichos-da-seda. |
| 10 | `candlekeep_ferraria` | 28 x 18 | `gen_mapa.py` | A forja, a bigorna, o cocho, o palheiro, 8 baias de cavalo e 4 baias reforçadas (hipogrifo, grifo, serpe). |
| 11 | `candlekeep_biblioteca` (fase 5) | 30 x 30 por andar | `gen_mapa.py` | Uma torre da Grande Biblioteca com estantes do chão ao teto e um disco flutuante que leva até 3 criaturas aos andares altos. |
| 12 | `candlekeep_subterraneo` (fase 5) | a definir | `gen_relevo.py` | As catacumbas, os cofres dos Ecos de Alaundo, a Câmara do Saber Perdido e o caminho patrulhado por Miirym. |

**Escala do mapa geral.** Hoje o fundo é desenhado com 200 px por quadrado. Com 80 x 56 quadrados, isso dá 16000 x 11200 px,
grande demais para muitas placas de vídeo. O plano é aceitar `"px"` no `mapa.json` e usar 120 no Pátio (9600 x 6720).
Os prédios do Pátio entram como **telhado com paredes simples do Foundry**, sem um token por bloco. Só a muralha externa,
o portão e as portas dos prédios são assets com vida. Isso mantém o número de tokens baixo. Os interiores usam a construção
quebrável completa.

---

## 3. Infraestrutura nova no módulo (fase 0)

### 3.1 Cenas ligadas (`scripts/cidade.js`)
- No `mapa.json` entra `"saidas"`: `{ "id": "porta_hearth", "x", "y", "w", "h", "para": "candlekeep_hearth", "chegada": "entrada" }`.
  Cada saída vira uma **Region** com o comportamento *Teleport Token* do Foundry (nativo no v12 e no v13), apontando para a
  região `chegada` da outra cena, com a opção de pedir confirmação ao jogador.
- `api.buildCity("candlekeep")` lê `mapas/candlekeep/cidade.json` (a lista de mapas), cria a pasta de cenas *Candlekeep*,
  monta todas as cenas e só então liga as regiões, quando todas já têm UUID.
- **Montar de novo sem duplicar:** cada cena guarda a flag `mapId`. Rodar outra vez pergunta se substitui as cenas da pasta.
- Uma saída pode depender de uma porta. Na entrada de um prédio, a região fica dentro da porta, então só funciona com a porta aberta ou arrombada.
- Notas no mapa (alfinetes) no Pátio, uma por estabelecimento, abrindo a página do diário **"Guia de Candlekeep"**, que é gerado
  de `mapas/candlekeep/guia.json` com a descrição, os NPCs e os ganchos de cada lugar.

### 3.2 NPCs (`assets/npcs.json` + `scripts/npc.js`)
- **NPC nomeado:** `{ id, nome, titulo, especie, base, img, bio, local }`. `base` é o nome do bloco de estatísticas no compêndio SRD
  do dnd5e (Commoner, Acolyte, Priest, Guard, Veteran, Mage, Archmage, Noble, Scout, Stone Golem, Ogre...). O ator é copiado do
  compêndio e renomeado, e ganha a imagem e a biografia. Fica na pasta *Candlekeep / NPCs nomeados*.
- **Blocos que não estão no SRD**, como o *sage* e o *master sage* de CM: criamos versões aproximadas **[nosso]** a partir do Mage,
  com perícias de História, Arcanismo e Religião em expertise.
- **Plebeus aleatórios:** tabelas de espécie, ofício, nome (por espécie, no estilo de Faerûn) e uma mania de uma linha. O ofício
  define o bloco de estatísticas, e o token sai de um conjunto de imagens por ofício e espécie.
  `api.gerarPlebeus(n, { ofício, área })` coloca os plebeus numa área da cena atual.
- No `mapa.json`, `"npcs"` lista os nomeados e onde ficam, e `"multidao"` traz áreas com quantidade e tabela de ofícios
  (exemplo: `{ "area": [x, y, w, h], "n": 8, "oficios": ["buscador", "peregrino"] }`).
- `"periodo": "dia" | "noite"` nos dois: o Pátio de noite tem só a procissão do Cântico e alguns guardas.

### 3.3 Proteções de Candlekeep (`"protecoes": true` na cena)
- **Fogo abafado:** com a proteção ligada, as reações de fogo (`fire`/`lightning` → `queimando`) não acontecem. O chat diz que
  "as proteções de Candlekeep sufocam a chama" e o objeto fica chamuscado. Assets com `"fogoPermitido": true` (a lareira do Hearth)
  continuam queimando. Velas acendem normalmente.
- **Botão "Proteções caídas"** no HUD da cena: o mestre desliga as proteções para um cenário (um apagão das proteções, como em
  *When the Lights Went Out in Candlekeep*) e o fogo volta a funcionar como no resto do módulo. Uma biblioteca em chamas fica
  disponível sem mudar nenhum asset.
- **Ordens de Concordância:** dano em estante, pilha de livros, atril ou rolo de pergaminho soma no contador
  "Conhecimento destruído" da cena e avisa no chat. Ao passar do limite (`"alarme": 1` por padrão), toca o sino e aparecem
  **1 arquimago e 4 magos** Avowed no ponto de chegada mais próximo. Eles são criados a partir do SRD.
- **Livro do acervo levado embora:** só um aviso no chat ao sair da cena da fortaleza ("o livro some da mochila"). Quem
  remove o item é o mestre.

### 3.4 Gerador
- `gen_mapa.py` e `gen_relevo.py` passam a aceitar `"px"` (pixels por quadrado), `"saidas"`, `"npcs"` e `"multidao"`.
- Na legenda, `edificio` vira um telhado sólido com paredes simples do Foundry, `vazio` é o fundo escuro dos demiplanos,
  `escada` é uma peça com saída e `muralha` é a muralha externa, mais forte que a parede.
- A prévia desenha as saídas (azul), os NPCs nomeados (círculo com a inicial) e as áreas de multidão.

---

## 4. Assets interativos novos

Todos seguem o `assets.json` atual (estados, `reactions`, `onZero`, `player`, `sfx`, `light`, `sound`).
CA e PV são uma proposta inicial.

### Construção e portas
| Asset | Tamanho | CA / PV | Estados e reações |
|---|---|---|---|
| Muralha de Candlekeep | 1 x 1 | 19 / 120 | Pedra e ferro. Imune a veneno, psíquico, necrótico e radiante; resiste a contundente, cortante e perfurante. Inteira → rachada → brecha (a passagem abre). |
| Portão negro (duplo) | 4 x 1 | 20 / 250 | Fechado / aberto / arrombado. Só o mestre abre. Imune a fogo e raio (metal estranho). Trovão e força racham, mas só ao chegar a 0 PV ele cede. |
| Porta Esmeralda | 3 x 1 | — | Trancada / aberta. Sem vida: o dano não faz efeito (protegida contra todo dano) e o chat avisa. Brilho verde de luz. Só o mestre abre. |
| Torre de muralha | 3 x 3 | 19 / 200 | Bloco sólido, com seteiras. |
| Janela com venezianas | 1 x 1 | 12 / 6 | Fechada / aberta / quebrada. Aberta, deixa ver através. Quebrada, deixa passar. |
| Escada | 1 x 1 | — | Saída para o andar de cima ou de baixo. |
| Alçapão | 1 x 1 | 15 / 15 | Fechado / aberto / arrombado. O alçapão laranja da Casa do Repouso é de metal (CA 19). |

### Biblioteca e estudo
| Asset | Tamanho | CA / PV | Estados e reações |
|---|---|---|---|
| Estante de livros | 2 x 1 | 13 / 20 | Inteira / tombada (terreno difícil, não bloqueia mais) / cortada / molhada (livros arruinados com água ou gelo) / queimando e cinzas (só com as proteções caídas). Trovão e força derrubam a estante. Conta como conhecimento. |
| Pilha de livros | 1 x 1 | 10 / 4 | Pode ser movida pelo jogador. Espalhada / molhada / queimando. Conta como conhecimento. |
| Atril de leitura | 1 x 1 | 12 / 6 | Inteiro / tombado / quebrado. Com livro aberto, conta como conhecimento. |
| Escrivaninha de escriba | 2 x 1 | 12 / 10 | Inteira / tinta derramada (concussão espalha uma mancha num quadrado: terreno difícil escorregadio) / quebrada. |
| Carrinho de livros | 1 x 2 | 11 / 12 | Veículo de terra: leva as pilhas de livros que estão em cima, como a carroça. |
| Vela e candelabro | 1 x 1 | 10 / 2 | Aceso / apagado (o jogador alterna). É a luz permitida pelas proteções. |
| Lâmpada de chama contínua | 1 x 1 | 13 / 5 | Acesa (não apaga com gelo nem com água) / quebrada. *Dissipar magia* apaga. |
| Globo flutuante (driftglobe) | 1 x 1 | 15 / 3 | Aceso / apagado. Pode ser movido. |
| Disco flutuante (fase 5) | 1 x 1 | 15 / 20 | Veículo que muda de altura (usa a altura do relevo) e leva até 3 criaturas. |

### Hearth e hospedagem
| Asset | Tamanho | CA / PV | Estados e reações |
|---|---|---|---|
| Amplificador geométrico | 1 x 1 | 15 / 10 | Orbe de cristal com engrenagens. Brilhando / rachado (a luz pisca) / estilhaçado. A 0 PV o espaço extradimensional desaba: o chat pede Destreza CD 15 e 2d6 de concussão para todos no salão e a cena manda todo mundo para a frente do Hearth no Pátio. |
| Fogueira e lareira do Hearth | 1 x 1 e 2 x 1 | — | Acesa e nunca apaga (`"fogoPermitido"`, mas gelo e água não apagam). Quem entra leva 1d10 de fogo. |
| Balcão do bar | 1 x 1 (em segmentos) | 13 / 15 | Inteiro / quebrado / queimando. Serve de cobertura. |
| Cadeira / banco / poltrona | 1 x 1 | 10 / 3–5 | O jogador pode mover. Quebrada / queimando. |
| Cama e beliche | 1 x 2 | 10 / 8 | Inteira / quebrada / queimando. |
| Tapeçaria | 1 x 1 (na parede) | 10 / 4 | Pendurada / rasgada / queimando. |

### Templo, ofícios e banhos
| Asset | Tamanho | CA / PV | Estados e reações |
|---|---|---|---|
| Sino de bronze | 1 x 1 | 19 / 30 | O mestre toca ou para de tocar. Tocar dispara o alarme da cena. Trovão faz o sino tocar sozinho. |
| Altar | 2 x 1 | 15 / 25 | Inteiro / profanado / quebrado. |
| Gárgula de pedra | 1 x 1 | 17 / 178 | Estátua no beiral. "Despertar" troca o token por um **Golem de Pedra** (SRD), que desce planando (queda lenta). |
| Forja | 2 x 2 | 17 / 40 | Acesa (luz, som e fogo permitido) / apagada. Quem entra leva 2d6 de fogo. |
| Bigorna | 1 x 1 | 19 / 50 | Pode ser empurrada com dificuldade. |
| Fardo de feno | 1 x 1 | 8 / 4 | O jogador pode mover. Queima rápido (só com as proteções caídas, fora do Hearth e da forja). |
| Porta de baia | 1 x 1 | 13 / 12 | Fechada / aberta / arrombada. Ao abrir, o animal de dentro pode fugir (o mestre decide). |
| Cocho d'água | 2 x 1 | 12 / 10 | Usa a água do lago (congela, eletrifica, envenena) em escala pequena. |
| Tear e rolo de tecido | 2 x 1 e 1 x 1 | 10 / 6 | Inteiro / cortado / queimando. |
| Casulário (bichos-da-seda) | 1 x 1 | 10 / 3 | Vivo / esmagado. |
| Água termal | 1 x 1 | — | Novo estado `termal` da água existente: solta vapor fraco (luz difusa, sem bloquear a visão). O gelo a congela por só 1 rodada. |
| Sauna | área | — | Região de visão prejudicada fixa. |

Assets que já existem e serão reaproveitados: mesa, barril, caixa, carroça, porta, parede, pilar, tocha (só fora das muralhas),
água, árvore pequena (jardins) e as armadilhas (fase 5, nos subterrâneos).

### Peças de chão (`mapas/pecas/`)
Paralelepípedo, mármore, tapete, rocha vulcânica, telhado de ardósia e de telha, vazio (demiplano) e escada.

---

## 5. NPCs nomeados

Todos são **[CM]**, salvo onde diz **[nosso]**. "Sábio" e "sábio mestre" são blocos de CM que não estão no SRD
e terão a nossa aproximação (seção 3.2).

| NPC | Papel | Espécie | Base | Onde fica |
|---|---|---|---|---|
| Kalan Strongbranch | Guardião do Portão | humano | Archmage | Portão (guarita) |
| 5 guardas do portão | Avowed de Deneir | variadas | Priest | Portão, com troca nos sinos |
| Guardião da Porta Esmeralda | Recebe as cartas de admissão | **[nosso]** nome a definir | Mage | Pátio, na Porta Esmeralda |
| Benedora Stoneforge | Cantor do Cântico Sem Fim | anã do escudo | Priest | Pátio, à frente da procissão |
| Fembris Larlancer | Adjunto (18, ansioso por agradar) | humano | Commoner | Pátio e Pilares |
| Sprig Summerfoot | Adjunta (dedos sujos de tinta, carrega biscoitos) | halfling | Commoner | Pilares |
| Parmak | Adjunto escriba (sempre lendo, esbarra nas coisas) | humano | Commoner | Encadernador |
| Garlyth Graystock | Adjunto (interrompe, adivinha o que você quer) | anão | Commoner | Pilares |
| Nax Olossis | Adjunto (falante) | draconato de latão | Commoner | Pátio |
| Orrin Glass | Adjunto escriba (67, surdo de um ouvido, esquecido) | humano | Commoner | Encadernador |
| Vooshadi Moonriver | Adjunta (87, estoica e direta) | elfa da lua | Acolyte | Pilares |
| Irony | Adjunta escriba (15, segue todas as regras) | tiefling | Commoner | Encadernador |
| Taberneiro do Hearth | Dono do balcão, aluga as salas (5 po) | **[nosso]** nome a definir | Commoner | Hearth |
| Little One | Ogro erudito, gênio graças a uma *tiara do intelecto* | ogro | Ogre (INT 19) **[nosso]** | Hearth, perto do fogo |
| Anfitrião da Casa do Repouso | Recepção | **[nosso]** nome a definir | Commoner | Casa do Repouso |
| Lorekeeper Kei Tigersteel | Cuida do Templo de Oghma | humano shou | Priest | Templo |
| 4 gárgulas | Golens de pedra nos beirais | — | Stone Golem | Templo (Pátio) |
| Feldmar Bisset III | Alfaiate, acólito de Gond, cria bichos-da-seda | humano | Acolyte | Alfaiataria |
| Khe'ril Hammerbind | Ferreiro e chefe dos estábulos | anão dourado | Veteran | Ferraria |
| Leitor Mestre do Encadernador | Supervisiona os escribas | **[nosso]** nome a definir | Sábio | Encadernador |
| Lorris Niss | Acólito (gancho de *The Price of Beauty*) | meio-elfo | Acolyte | Encadernador |
| Matreous | Sábio especialista em maldições (gancho de *The Joy of Extradimensional Spaces*) | humano | Sábio | Pilares (sala de leitura) |

**Fase 5 (Pátio Interno e subterrâneo)**
- Janussi, Guardião dos Tomos (humano, Archmage).
- Skoda "Bookwyrm" Valanaster, Primeiro Leitor (draconato verde, sábio mestre).
- Os 8 Grandes Leitores: A'lai Aivenmore, Alkrist, Daral Yashenti, Fheminor Scrivenbark, Kazryn Nyantani,
  Sylvira Savikas (com a quasit Jezebel), Teles Ahvoste e V'ziir-Ag.
- Miirym, o fantasma de dragão de prata.
- Os NPCs do Porão dos Vaga-lumes: Varnyr, Ebder e Gailby Smallstone, K'Tulah e Crinkle.

**Gatos de Candlekeep:** não existem na lore oficial. Se quiser, entram como **[nosso]**, com o bloco Cat do SRD.

---

## 6. Plebeus aleatórios (multidão)

| Ofício | Base | Onde aparece |
|---|---|---|
| Buscador (estudioso visitante) | Noble ou Commoner | Fila do portão, Pátio, Hearth, Pilares |
| Peregrino (de Oghma, Deneir, Gond ou Milil) | Acolyte | Fila do portão, Templo, Pátio |
| Mercador e caravaneiro | Commoner | Fila do portão (com carroças), Ferraria |
| Guarda de caravana | Guard | Fila do portão, Hearth |
| Aventureiro | Veteran, Scout, Mage ou Priest | Hearth, Pátio |
| Bardo | Bard (se o sistema tiver) ou Commoner | Hearth |
| Avowed servo (cozinha, limpeza, carregador) | Commoner | Todos os prédios |
| Acólito Avowed (procissão do Cântico) | Acolyte | Pátio (6 a 8, em fila atrás de Benedora) |
| Escriba | Commoner | Encadernador, Pilares |
| Aprendiz de ferreiro e cavalariço | Commoner | Ferraria |
| Atendente dos banhos | Commoner | Banhos |
| Animais | Horse, Pony, Mule, Hippogriff, Griffon, Wyvern | Ferraria, fila do portão |

Lotação sugerida de dia: portão 10 a 14 (com os guardas), Pátio 20 a 25, Hearth 12 a 18, Casa do Repouso 8, Banhos 6,
Encadernador 6, Pilares 6, Templo 5, Alfaiataria 3, Ferraria 4 pessoas e 10 animais.
Os plebeus nunca são hostis. Quem bate num plebeu dispara o alarme como quem bate num livro.

**Imagens dos tokens** (precisa de decisão, ver seção 9): gerar no orquestrador local de imagens (uma por ofício e espécie,
vista de cima, borda redonda igual em todos) ou usar um pacote CC0.

---

## 7. Sons

- **Portão:** vento do mar e ondas.
- **Pátio:** o Cântico Sem Fim preso ao token de Benedora, andando com a procissão (como o som da tocha), mais o sino da hora.
- **Hearth:** reaproveita `taverna_loop.ogg` e o som do fogo.
- **Ferraria:** martelo e cavalos.
- **Banhos:** água borbulhando.
- **Templo:** coro baixo.
- **Pilares:** nenhum dentro das salas de leitura (silêncio).

Tudo CC0, com os créditos em `mapas/CREDITOS.md`. O canto pode ser gerado se não houver um CC0 bom.

---

## 8. Fases de entrega (um PR por fase, como os mapas anteriores)

0. **Infraestrutura:** cenas ligadas, NPCs e plebeus, proteções de Candlekeep e o `"px"` no gerador.
   Teste: ligar os mapas `taverna` e `lago` por uma porta e colocar 5 plebeus.
1. **Portão:** muralha, torre, portão negro, peças de rocha e paralelepípedo, mapa 1 ligado ao Caminho do Leão,
   Kalan e os guardas, fila de buscadores e caravanas.
2. **Pátio do Ar:** mapa 2 com telhados, saídas para todos os prédios (as que ainda não existem levam a uma cena "Em obras"),
   a Porta Esmeralda, as gárgulas, a procissão, a multidão e o Guia de Candlekeep.
3. **Hearth e Casa do Repouso:** amplificador, balcão, móveis, camas, escadas, salas extradimensionais.
4. **Os outros prédios:** Encadernador e Pilares (estantes, pilhas de livros, atris, escrivaninhas, velas), Templo (sino,
   altar), Alfaiataria, Ferraria e Estábulos (forja, baias, animais), Banhos (água termal, sauna).
5. **Pátio Interno e subterrâneo**, para os cenários de *Candlekeep Mysteries*: uma torre da Grande Biblioteca com disco
   flutuante, o Porão dos Vaga-lumes, as catacumbas e os cofres com Miirym.

### Cenários que já cabem nos mapas
| Aventura (nível) | Onde começa |
|---|---|
| *The Joy of Extradimensional Spaces* (1) | Pilares: a sala de leitura de Matreous |
| *Mazfroth's Mighty Digressions* (2) | Pilares (o livro ataca), depois o Encadernador e o Pátio |
| *A Deep and Creeping Darkness* (4) | Pilares e Casa do Repouso |
| *Shemshime's Bedtime Rhyme* (4) | Porão dos Vaga-lumes, sob a Casa do Repouso (fase 5) |
| *The Price of Beauty* (5) | Encadernador |
| *Kandlekeep Dekonstruktion* (9) | Pátio do Ar, com o terremoto (fase 5 para a torre "Barn Door") |
| *The Scrivener's Tale* (14) | Cofres (fase 5) |
| *Alkazaar's Appendix* (15) | Hearth |

A maior parte das outras aventuras começa com um livro lido em Candlekeep e depois sai para outros lugares.

---

## 9. Decisões (20/10/2026)
1. **Planta:** desenhamos uma planta nossa, fiel às descrições de CM (sem o mapa-pôster).
2. **Imagens dos NPCs:** geradas localmente no orquestrador `ia-orc` (ComfyUI), vista de cima, borda redonda igual em todos.
3. **Proteções:** ligadas por padrão. O fogo só funciona com "Proteções caídas" (exceto lareira do Hearth e forja).
4. **Fase 5 (Pátio Interno e subterrâneo):** fica para depois.

## 10. Estado (20/10/2026)
Feito (ainda sem teste no Foundry):
- **Fase 0:** cenas ligadas (`scripts/cidade.js`), NPCs e plebeus (`scripts/npc.js`, `assets/npcs.json`), proteções
  (`scripts/protecoes.js`) e efeitos de estado (`scripts/estados.js`: gárgula → golem, colapso do Hearth, sino do alarme).
- **Fases 1 a 4:** os 10 mapas (`mapas/candlekeep_*`), ligados entre si e ao Caminho do Leão (lobisomens), com 43 assets
  (29 novos) e 10 materiais novos. `MAPA = "candlekeep"` na macro monta tudo.
- **NPCs:** 31 nomeados (24 de Candlekeep, 7 animais) e 11 ofícios de plebeus. Os 24 nomeados têm token próprio e os
  plebeus têm 64 rostos (5 a 6 por ofício), gerados no `ia-orc` e emoldurados por `tools/gen_tokens.py`. Os animais usam a
  imagem do compêndio.
- **Sons:** 85 estados de 42 assets têm efeito ao mudar. Cada mapa tem música própria e ambiência, e a cidade tem uma playlist
  (com combate, o Cântico Sem Fim e a canção do bardo). São 36 efeitos, 11 ambiências, 11 músicas e 2 canções, gerados no
  `ia-orc` e preparados por `tools/gen_sons.py`. A variação de cada um foi escolhida por medição (silêncio, picos, volume),
  sem ouvir; as outras ficam em `~/Downloads/ia-orc/<job>` e o job de cada som está em `tools/sons.json`.

Ficou de fora ou simplificado:
- **Água termal:** as piscinas dos Banhos usam a água normal (reage igual ao lago).
- **Regiões de silêncio e de vapor:** os Pilares e as saunas só têm a nota para o mestre.
- **Fogueira e forja:** não causam dano em quem entra; o mestre aplica.
- **Alçapão laranja:** o da Casa do Repouso usa a peça de porta (sem cor própria).
- **Mobília:** não há mesa redonda, prensa nem rolo de tecido; foram usados `mesa` e `caixa`.
- **Procissão:** os acólitos e Benedora ficam parados; o mestre os move.
- **Dia e noite:** a multidão é sempre a de dia.
- **Baias reforçadas da Ferraria:** usam parede e porta comuns. Para serem mais fortes, trocar por `muralha` e `portao`.
