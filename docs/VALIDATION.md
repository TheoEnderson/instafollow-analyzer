# Registro de validação

## Inventário COLLECT após a quarta execução do CI — 13/10/2026

O mantenedor informou sucesso dos quatro jobs de testes e do build Linux;
o build Windows passou pelo smoke inicial e falhou na comparação do inventário,
antes de preparar o pacote. O TOC/arquivo Windows real não está disponível neste
ambiente; uma eventual divergência adicional dependerá dos novos diagnósticos.

Foi conferido o código instalado e oficial de PyInstaller 6.22.3: COLLECT guarda
um tuple contendo a lista de triplas (destino, origem, tipo). EXECUTABLE e PKG
externo ficam na raiz; DATA, BINARY, EXTENSION e SYMLINK ficam em `_internal`
na configuração deste spec. Nenhuma mudança de spec ou workflow foi necessária.
[Implementação COLLECT](https://github.com/pyinstaller/pyinstaller/blob/v6.22.3/PyInstaller/building/api.py).

Uma causa concreta foi reproduzida antes da correção: destino TOC
`PySide6\QtCore.pyd` era prefixado literalmente como `_internal/PySide6\QtCore.pyd`,
enquanto a varredura produzia `_internal/PySide6/QtCore.pyd`. Para os mesmos dois
arquivos, o validador antigo relatou um ausente e um inesperado. Também foram
examinadas diferenças de caixa, tipos, localização na raiz e colisões.

O validador agora compara chaves relativas coerentes com a plataforma: no Windows,
separadores são uniformizados e caixa normalizada; no Linux, caixa e barras
invertidas literais permanecem distintas. `..`, unidades, caminhos absolutos,
NUL e aliases Windows com ponto/espaço final são recusados antes da comparação.
Colisões não são silenciosamente deduplicadas. Tipos desconhecidos e formato de
TOC inválido interrompem o processo; nenhuma nova exceção para arquivo extra foi
adicionada. Links externos continuam recusados.

Primeiro foram implementados diagnósticos, depois a normalização. Em divergência,
o erro informa contagens esperadas/encontradas/ausentes/inesperadas, até 12 exemplos
por lista (nomes até 180 caracteres), modo de comparação e contagem de caminhos
com barra invertida. Mostra somente destinos relativos do inventário; nomes extras
desconhecidos são redigidos com identificador SHA-256 abreviado e extensão segura.
Não imprime caminhos absolutos de origem nem conteúdo dos arquivos.

Validação local: **161 testes aprovados** em Python 3.12.3 e 3.14.4; Ruff,
formatação e `git diff --check` aprovados. Regressões cobrem TOC Windows aninhado,
caixa, distinção Linux, arquivo ausente, extras pessoais, limites/redação dos
logs, destinos inseguros, colisões, tipos desconhecidos, PKG externo e symlinks.
O inventário COLLECT e diretório Linux reais disponíveis passaram na nova
comparação; isso não transforma o pacote Linux local antigo em release aprovada.

**Pendente:** repetir o build Windows Server 2022. Confirmar aprovação do inventário,
empacotamento, checksum/smoke do ZIP extraído e upload do candidato. Se ainda falhar,
analisar as contagens, destinos relativos ausentes e seus pares inesperados nos
logs; nenhuma conclusão sobre arquivos realmente ausentes/extras pode ser tomada
apenas a partir da mensagem genérica anterior. Sem commit/push ou mudanças de UI,
parser, análise, exportação ou configuração de build nesta etapa.

## Resultados responsivos após a terceira execução Windows — 13/10/2026

Resultado remoto informado pelo mantenedor: tela inicial aprovada no Windows;
resultados ainda com 80 px de rolagem horizontal externa em 640×560, nos dois
temas e Python 3.12/3.14 (140 aprovações, duas falhas). Linux aprovado.

Investigação local antes da alteração: a tabela tinha minimumSizeHint horizontal
de 70 px, as abas 123 px, cards em duas colunas 217 px, toolbar 295 px e ações
inferiores 373 px. Search era Expanding, botões Minimum e textos Preferred.
Os botões inferiores continuavam em três colunas, e os de exportação em duas,
mesmo no modo compacto. A grade de cards considerava somente breakpoints, sem
conferir os mínimos reais. Esses grupos podiam propagar suas somas para a página.

O código anterior do commit foi exercitado localmente com mínimos de ações de
213, 213 e 212 px: mínimo inferior 658, página 706, viewport 626 e rolagem **80**.
É uma reprodução controlada Linux do problema estrutural, não uma medição das
larguras individuais dos botões Windows, ainda não fornecidas pelo CI.

Correções restritas à apresentação da ResultsPage:

- Exportações e ações passam para coluna quando suas larguras reais não cabem.
  O modo amplo mantém a disposição anterior quando há espaço suficiente.
- Cards reduzem o número de colunas conforme o maior mínimo real; os cinco
  continuam presentes, chegando a uma coluna quando necessário.
- O mínimo da página representa controles reorganizados individualmente, mais
  suas margens; o layout não pode fixar no widget o mínimo de uma linha larga e
  impedir a redução seguinte. A altura mínima permanece baseada no layout atual.
- Cabeçalho também pode passar para coluna. Textos com quebra de linha preservam
  heightForWidth sem impor seus hints horizontais à página.
- Abas usam os botões de rolagem próprios do Qt e mantêm os títulos completos;
  regressões verificam troca de categoria por teclado e visibilidade da aba ativa.
- Pesquisa permanece adaptável; tabela conserva a rolagem interna das colunas.
  Nenhuma barra externa foi ocultada e nenhum controle foi removido.
- Resize, LayoutRequest e mudanças de fonte/estilo recalculam as disposições.

Os diagnósticos dos testes agora incluem viewport, geometria, minimumSizeHint,
sizeHint, minimumWidth e política horizontal de página, cabeçalho, cards, barra,
avisos, abas, pesquisa, tabela, exportações e ações. Falhas podem ser localizadas
sem depender apenas do valor da barra externa.

Validação local: **144 testes aprovados** em Python 3.12.3 e 3.14.4; Ruff,
formatação e `git diff --check` aprovados. Preservados os 142 anteriores.
Duas regressões novas, uma por tema, ampliam mínimos de ações, exportações e
cards; percorrem 1920×1080 → 640×560 → 820×620 → 1180×820 → 1920×1080 → 640×560.
Conferem todos os cinco cards, mínimos e geometria dos controles, acesso integral
por rolagem vertical, abas por teclado e retorno à disposição ampla. Na menor
resolução, a tabela pode rolar internamente e a página externa permanece em zero.

**Confirmação definitiva pendente:** executar novamente no Windows Server 2022,
Python 3.12 e 3.14, com os oito casos originais e as duas novas regressões. A
reprodução local não substitui esse resultado nem testes gráficos interativos.
Parser, análise, exportação e empacotamento não foram alterados. Sem commit/push.

## Reorganização dos botões após a segunda execução Windows — 13/10/2026

Resultado remoto informado pelo mantenedor: 138 testes aprovados e duas falhas
de layout em Windows Server 2022, Python 3.12/3.14, nos dois temas em 640×560.
Parser e caminhos de drag and drop aprovados. Os valores `drop_min=656`,
`content_min=656`, `page_min=704` e viewport 626 localizaram a restrição na DropArea.

Antes desta correção, um experimento local impondo mínimos de 296 px a cada
botão reproduziu **exatamente** esses valores e 78 px de rolagem: a linha
horizontal somava 592 px de botões, 12 px de espaçamento e 52 px de margens/bordas.
Alterar apenas QLabel não removia a restrição de largura da linha de botões.
O experimento é uma regressão controlada no Linux, não um teste Windows nativo.

A DropArea agora usa QBoxLayout adaptável: compara a largura disponível com os
size hints/mínimos reais dos dois botões e o espaçamento. Os botões ficam em
coluna quando não cabem e voltam à linha quando há espaço. Ambos permanecem
centralizados, com dimensões suficientes para seus textos. Não há largura fixa
de botão nem breakpoint arbitrário no código da interface.

O mínimo horizontal da DropArea representa a disposição em coluna (maior botão
mais margens/bordas). A restrição automática de mínimo do layout interno foi
substituída por esse minimumSizeHint, mantendo a altura mínima do layout atual.
Isso evita que a disposição horizontal imponha um mínimo largo ao widget e
impeça o próximo redimensionamento para coluna. Resize, mudanças de estilo/fonte
e LayoutRequest recalculam a direção. Nenhuma barra de rolagem foi ocultada.

Na regressão local, os mínimos passaram a drop 348/page 396, com zero rolagem
horizontal em 640×560. Em 820×620, 1180×820 e 1920×1080 os botões voltaram à linha;
ao retornar a 640×560, voltaram à coluna. O limite de conteúdo de 820 px,
centralização, textos, ações e navegação existentes foram preservados.

Validação local: **142 testes aprovados** em Python 3.12.3 e 3.14.4, Qt offscreen
no Linux. Mantidos os 140 anteriores e acrescentadas duas regressões (temas
claro/escuro) com mínimos de botão ampliados. Elas percorrem as quatro resoluções
e o retorno à menor, conferindo geometria, ausência de sobreposição, mínimos,
centralização e visibilidade completa por rolagem vertical. Ruff, formatação e
`git diff --check` aprovados.

**Pendente:** próxima execução real no Windows Server 2022 com Python 3.12/3.14,
incluindo os oito casos originais de resolução/tema e as duas novas regressões.
Somente esse resultado confirmará o ajuste com as métricas nativas Windows.
Não houve alteração de parser, análise, exportação ou empacotamento, nem commit/push.

## Correções após a primeira execução Windows do CI — 13/10/2026

Resultado remoto informado pelo mantenedor: Linux aprovado; Windows Server 2022
com Python 3.12 e 3.14 apresentou 129 aprovações e quatro falhas em cada ambiente.
As alterações abaixo ainda precisam de uma nova execução real desses jobs.

- ZIP: `ZipInfo.filename` é normalizado conforme o SO (barras invertidas viram
  barras normais no Windows) e truncado no primeiro NUL. O parser passou a validar
  `orig_filename` antes de classificar/ler as entradas, mantendo rejeição de
  caminhos absolutos, `..`, barras invertidas, `:`, symlinks e criptografia, e
  acrescentando rejeição explícita de NUL. Nenhuma extração foi introduzida.
- O escritor ZIP usado pelo teste também podia normalizar o nome no Windows.
  O teste de caminhos perigosos agora grava literalmente o nome nos cabeçalhos
  e confere `orig_filename` ao reabrir. Casos adicionais cobrem travessia interna,
  unidade relativa/absoluta Windows, UNC e NUL; uma regressão também confere um
  ZipInfo já normalizado, inclusive no host Linux.
  [Implementação oficial CPython](https://github.com/python/cpython/blob/3.12/Lib/zipfile/__init__.py).
- Layout inicial: os textos com quebra de linha deixaram de impor largura mínima
  baseada nos seus hints de fonte/plataforma (`QSizePolicy.Ignored` somente no eixo
  horizontal). A política vertical e `heightForWidth` são preservados. Margens,
  tipografia, botões e configuração das barras de rolagem permanecem iguais.
  Os 78 pixels de excesso observados no Windows não foram reproduzidos neste host;
  a eficácia com as métricas nativas Windows precisa de confirmação no CI.
  Os testes existentes passaram a conferir também largura, posição horizontal
  e visibilidade completa dos botões de importação após rolagem vertical.
  [Políticas de tamanho Qt](https://doc.qt.io/qt-6/qsizepolicy.html).
- Drag and drop: o teste compara objetos `Path`, aceitando a representação
  equivalente emitida por QUrl no Windows. A implementação de drag and drop
  permanece igual, assim como a distinção de caminhos no Linux.

Validação local desta etapa: **140 testes aprovados** em Python 3.12.3 e 3.14.4,
com Qt offscreen no Linux. Preservados os 133 testes anteriores, com sete casos
novos de segurança ZIP. Ruff, formatação, `git diff --check`, `pip check` e
validação estática do workflow por actionlint aprovados.

Pendente: repetir o GitHub Actions em Windows Server 2022 com Python 3.12/3.14;
conferir ausência de rolagem horizontal em 640×560 nos dois temas e preservação
das outras resoluções; prosseguir para os builds e smoke tests apenas se os testes
passarem. Testes gráficos interativos Windows e portabilidade dos artefatos
continuam separados da suíte offscreen. Nenhum commit ou push feito pelo agente.

## Registros das etapas anteriores

Validação local em 12/10/2026 (America/Sao_Paulo).

## Revisão de distribuição da v0.1.0

A revisão final está em [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md), com 118 testes
locais aprovados e validação estática do workflow por actionlint. O teste em
contêiner Debian 13 sem Python externo acessível encontrou incompatibilidade
GLIBC_2.43 da GLib incluída no pacote local. Assim, a validação anterior de
inicialização no host não constitui aprovação de portabilidade ou da release.
As pendências Windows, Linux de destino e licenças nativas continuam explícitas.

## Refinamento da interface antes da release

- Python 3.12.3 e 3.14.4: **111 testes aprovados** em cada ambiente, preservando os
  97 existentes e acrescentando 14 verificações de regressão da interface.
- Ruff: análise e formatação aprovadas.
- Executável Linux reconstruído com a interface refinada.
- Testes Qt executados em modo offscreen, sem consultar perfis.

A suíte passou a incluir redimensionamento em 640×560, 820×620, 1180×820 e
1920×1080 nos dois temas; controles alcançáveis sem rolagem horizontal;
contraste mínimo de 4,5:1 para as cores de texto verificadas da paleta;
estados vazios; ações desabilitadas sem seleção; duplo clique e Enter com
navegador simulado; destaque ao arrastar e rejeição de URLs remotas;
preservação e exportação de identificadores fictícios `_deleted_`.
As capturas em `assets/` foram atualizadas com dados fictícios.

A investigação de `_deleted_` foi limitada à leitura do código e a fixtures
sintéticas: não havia exportações reais para inferir semântica do Instagram.
O parser não interpreta o prefixo como estado da conta e não foi alterado.
Aviso e dicas de contexto deixam essa incerteza explícita. Nomes incompatíveis
com as validações existentes continuam gerando erro, sem descarte silencioso.

O Git não contém ZIP/JSON rastreados. `.gitignore` exclui essas extensões,
inclusive em maiúsculas; os dados de teste são gerados em pastas temporárias.

## Validação inicial executada

- Python 3.12.3: `python -m pytest -q` — **97 testes aprovados**.
- Python 3.14.4: `python -m pytest -q` — **97 testes aprovados**.
- PySide6/Qt 6.12.0; pytest 9.1.1; Ruff 0.17.0; PyInstaller 6.22.3.
- `ruff check src tests scripts` — aprovado.
- `ruff format --check src tests scripts` — aprovado.
- Instalação editável do projeto em ambientes virtuais isolados.
- PyInstaller onedir em Linux x86_64 — build concluído.
- `scripts/check_bundle.py` — processo empacotado iniciou e permaneceu ativo
  durante três segundos com Qt offscreen, sem falha de inicialização.
- `scripts/package.py` — pacote tar.gz Linux com fontes oficiais correspondentes
  de QtBase, QtImageFormats, QtSvg, QtWayland, PySide/Shiboken e Python.
- Capturas reais com fixtures fictícias em `assets/`; revisadas visualmente.

A suíte inclui leitura de seguidores/seguindo, normalização, duplicatas,
comparações, multipartes, pastas/ZIP com subpastas, BOM UTF-8, JSON/ZIP inválidos,
exportações incompletas, listas vazias, estruturas desconhecidas, limites de
arquivos e diretório central, ZIP bombs, caminhos inseguros, symlinks,
ZIP64 recusado, erros de permissão, exportação TXT/CSV, ordenação, escrita
atômica e preservação do arquivo anterior em falha. A integração Qt verifica
importação em QThread, feedback/erros, estatísticas, abas, busca, ordenação,
cópia, exportação de categoria com filtro ativo, tema e limpeza da sessão.

## Limites da validação

- O Python 3.12.3 disponível neste host não possui `libpython3.12.so.1.0`;
  o PyInstaller recusou essa instalação. O build local foi realizado com Python
  3.14.4, que possui biblioteca compartilhada, sem alterar pacotes globais.
  A execução pelo código-fonte e os testes no `.venv` Python 3.12 funcionam.
- Não foi executado build Windows nesta máquina Linux. O workflow está preparado
  para testes e build nativos no Windows; sua execução depende de publicar o
  repositório no GitHub. Não houve commit, push ou publicação.
- Não houve teste interativo em sessão desktop real nem com leitor de tela.
  Capturas e integração Qt offscreen não comprovam todos os comportamentos do
  gerenciador de janelas, seletor de arquivos ou arrastar/soltar do desktop.
- O navegador não foi aberto durante testes. Os dados são fictícios.
- O executável local foi gerado no host com glibc 2.43; é uma validação local,
  não uma distribuição portátil para Linux mais antigo. O CI usa Ubuntu 22.04
  com Python 3.12 para construir o artefato destinado à distribuição.
- Antes de uma release pública, valide manualmente Windows 10/11 e desktops
  Linux de destino e revise licenças/fontes dos demais binários nativos que o
  PyInstaller coletar, conforme `THIRD_PARTY_NOTICES.md`.
- Não há executável assinado, instalador, AppImage ou teste em ARM.
