# Registro de validação

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
