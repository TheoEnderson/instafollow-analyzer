# Auditoria de distribuição e licenças — v0.1.0

Evidência local de 12/10/2026. Este registro se refere ao pacote Linux existente,
gerado em host glibc 2.43 com Python 3.14.4, Qt/PySide 6.12.0 e PyInstaller 6.22.3.
Não é o resultado do workflow Ubuntu 22.04 nem de um build Windows.

## Linux: causa e prevenção

O workflow efetivamente declara `ubuntu-22.04` no job de build. Agora verifica
Ubuntu 22.04/glibc 2.35 antes do build, usa Python 3.12 x64, versões auditadas em
`requirements-build.txt` e executa `scripts/audit_linux.py`. O empacotador repete
a auditoria, impedindo gerar um novo arquivo final a partir do build local
incompatível. O relatório `build/linux-abi.json` é preservado pelo CI mesmo se
a auditoria falhar. Ele será incluído em `third-party/linux-abi.json` nos pacotes
que passarem pela checagem.

O auditor usa `readelf --version-info --wide`, com `LC_ALL=C`, em cada ELF real.
Considera somente a seção de versões **requeridas**, não as definições exportadas.
Compara versões numericamente e recusa requisitos GLIBC desconhecidos. Não executa
os arquivos nem modifica a glibc. A análise cobre 168 ELF, sem contar novamente
links simbólicos: 37 exigem mais que 2.35. Máximo observado: 2.43.

| Componente do pacote local | Maior versão GLIBC requerida |
| --- | --- |
| Executável/bootloader InstaFollowAnalyzer | 2.14 |
| libpython3.14.so.1.0 | 2.38 |
| QtCore / QtGui | 2.34 |
| QtWidgets | 2.29 |
| libpyside6 | 2.32 |
| libshiboken6 | 2.14 |
| libglib-2.0.so.0 | **2.43** (`free_sized`, `free_aligned_sized`) |
| liblcms2.so.2 | **2.43** (`sqrtf`) |
| libsystemd.so.0 / libglycin-2.so.0 | 2.39 |
| GTK, Cairo, OpenSSL, libstdc++ e outras bibliotecas do host | 2.38 |
| libXdmcp.so.6 | 2.36 |

As três bibliotecas sem requisito GLIBC numérico direto são libicudata,
libX11-xcb e libcairo-gobject; isso não elimina suas dependências transitivas.
O JSON lista o requisito por arquivo. Corrigir apenas GLib seria insuficiente:
Python e outras bibliotecas também vieram de um sistema mais recente.

A baseline de distribuição planejada é Ubuntu 22.04 x86_64/glibc 2.35.
Não se promete suporte a todo Linux com glibc 2.35: drivers, plugins, bibliotecas
externas, arquitetura e sessões gráficas também precisam de validação. Alpine/musl
fica fora desse alvo. Não se copiou glibc para o pacote, não se removeu biblioteca
transitiva e não se alterou o host. Um novo build Ubuntu 22.04 ainda deve ser feito.

Esta abordagem segue a recomendação do
[PyInstaller para compatibilidade Linux](https://pyinstaller.org/en/stable/usage.html#making-gnu-linux-apps-forward-compatible):
construir no sistema mais antigo pretendido e considerar as bibliotecas nativas
copiadas. O Qt reconhece Ubuntu 22.04 como configuração de fontes, mas distingue
isso dos requisitos dos seus binários oficiais. Medimos os ELF do wheel utilizado,
sem inferir o requisito a partir da versão do Qt.
[Plataformas Qt](https://doc.qt.io/qt-6/supported-platforms.html).

## Windows: alcance da automação

Runner fixado em `windows-2022`, Python 3.12 x64 para build e 3.12/3.14 nos testes.
Os rótulos constam na [documentação GitHub](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
O spec resolve caminhos com `SPECPATH`/`Path`, usa COLLECT onedir e `console=False`.
Comandos, hooks e URLs de fontes independem de `/home`, `/usr` ou separadores Linux;
a consulta `dpkg-query` é restrita ao ramo Linux.

Antes de iniciar o EXE, o checker exige PE AMD64/PE32+/subsistema GUI, runtime
Python, módulos PySide, QtCore/Gui/Widgets, plugins qwindows/qoffscreen e runtime
vcruntime140/vcruntime140_1. Depois inicia Qt offscreen fora do projeto, em caminho
com espaços e com PATH isolado. Repete após extrair o ZIP.

Esse teste confirma somente que o processo fica ativo por três segundos; não é
um sinal explícito de prontidão da interface. Não valida diálogos, renderização,
interação, acessibilidade, navegador ou encerramento normal. O runner tem Python
instalado, embora fora do PATH do subprocesso. Windows Server 2022 não substitui
testes Windows 10/11 sem Python. Nenhum job remoto ou EXE Windows foi executado
nesta revisão.

## Licenças: evidências e obrigações

Inventário derivado de `COLLECT-00.toc`, das versões instaladas e dos textos
efetivamente disponíveis no pacote e no sistema. Foram associados 85 binários
a 78 pacotes Debian/Ubuntu, sem proprietário não resolvido nessa classe. Isso
não cobre sozinho as bibliotecas vendorizadas nos wheels nem código incorporado
estaticamente. O inventário de fontes dos seis arquivos Qt/Python foi conferido.

| Componentes presentes | Licença/opção e providência |
| --- | --- |
| PySide/Shiboken e QtBase, QtSvg, QtImageFormats, cliente QtWayland | Opção LGPLv3; textos LGPL/GPL e atribuições, fontes correspondentes e scripts de construção; alterações devem ser identificadas; permitir substituir bibliotecas e depurar modificações. |
| GLib/GObject/GIO, GTK/GDK, ATK/AT-SPI, Pango, libdatrie, libthai, FriBidi, libseccomp, systemd | Bibliotecas sob LGPL (versão e arquivos específicos no copyright de cada pacote). Entregar fontes correspondentes, patches da distribuição e condições de reconstrução aplicáveis; manter substituição dinâmica. |
| Cairo | LGPL-2.1 ou MPL-1.1; opção LGPL-2.1 avaliada, com as mesmas pendências de fontes. |
| glycin / Graphite2 | Opções LGPL/MPL e componentes com licenças próprias. Conferir arquivos efetivamente compilados antes de fechar a seleção da licença. |
| libmount/libblkid | Bibliotecas LGPL e código auxiliar com termos próprios; o pacote-fonte util-linux também contém ferramentas GPL que não estão automaticamente no binário da biblioteca. Revisar o subconjunto e patches. |
| libatomic, libgcc_s, libstdc++ | GPL com GCC Runtime Library Exception, sujeita às condições da exceção; preservar textos e verificar origem/processo de compilação. |
| Little CMS (liblcms2), Brotli, Expat, libffi, Pixman, X11/XCB e bibliotecas X | MIT/Expat/BSD ou variantes permissivas; manter copyrights, condições e disclaimers. A biblioteca liblcms2 é MIT; plugins GPL do pacote-fonte não foram identificados como binários separados neste bundle. |
| FreeType / HarfBuzz / Fontconfig / PNG / WebP / JPEG | FTL, MIT e termos próprios dos codecs/fontes; preservar atribuições individuais. Avisos FreeType/IJG adicionados em THIRD_PARTY_NOTICES.md. Conferir componentes incorporados ao Qt. |
| ICU libicuuc/libicui18n/libicudata | Versão 73.2 confirmada por `u_getVersion_73` → `[73, 2, 0, 0]`. Aviso Unicode e terceiros oficial completo agora fornecido separadamente; não há obrigação geral de entregar fontes por esses termos permissivos. |
| OpenSSL 3 | Apache-2.0: texto, avisos aplicáveis e identificação de modificações, se houver. |
| Python | PSF e componentes terceiros; fontes upstream não substituem patches Ubuntu da libpython local. Preservar avisos da distribuição e conferir reconstrução do build final. |
| libselinux | Aviso principal de domínio público/limitação de responsabilidade; ferramentas/debianização GPL no mesmo copyright não tornam automaticamente a biblioteca GPL. |
| PyInstaller / altgraph | GPL com exceção de empacotamento / MIT; avisos preservados. A exceção permite manter a licença do aplicativo. |
| DLLs Microsoft de um futuro build Windows | Ainda não inventariadas; conferir origem, direitos de redistribuição e termos do Visual C++/UCRT. Não aplicar MIT ou LGPL a essas DLLs. |

A tabela registra a opção avaliada e as pendências, não uma certificação jurídica.
Não foi atribuída uma licença única a todas as entradas de um copyright DEP-5:
há testes, ferramentas e documentação no mesmo pacote-fonte. Nenhum módulo Qt
exclusivamente GPL foi identificado no inventário local; há QtWayland **cliente**,
sem QtWaylandCompositor, QtVirtualKeyboard, QtPdf ou QtCharts. A lista deve ser
conferida novamente nos dois builds finais.

Correções verificadas separadamente, sem reempacotar o build incompatível:

- As pastas `LICENSES` de Qt/PySide agora são copiadas integralmente para os avisos.
  Antes, seus textos estavam nos TAR de fontes, mas eram omitidos da pasta notices.
- Os 14 textos referenciados em `/usr/share/common-licenses` foram copiados numa
  preparação local de avisos, incluindo LGPL-2.1 e GPL-2. O pacote não dependerá
  desses caminhos existirem na máquina do usuário.
- `docs/licenses/ICU-73.2.license` contém o aviso oficial completo; SHA-256:
  `f3005e195ff74d8812cc1f182a1c446fab678d70a10e3dada497585befee5416`.
  O empacotador inclui esse aviso para SONAME 73 e exige revisão para outro major.
  Novos builds devem confirmar também a versão exata do ICU.
- O manifesto passa a mapear binário → pacote e registrar os textos comuns e ICU.
  `sources_review_required` permanece verdadeiro.

O layout onedir mantém bibliotecas compartilhadas substituíveis por ABI compatível.
Isso atende parte do mecanismo pretendido de substituição; ainda é necessário
testar uma substituição real e conferir todas as condições aplicáveis. Não há
modificações próprias nessas bibliotecas nesta revisão. Isso **não** significa
ausência de patches de Ubuntu ou do fornecedor dos wheels.

Para liberar o artefato final, obter os fontes dos pacotes-fonte e versões exatas
registradas no manifesto, incluindo arquivos Debian/Ubuntu de patches e receitas
de build, e oferecer acesso correspondente junto à distribuição, conforme a
opção de licença adotada. Revisar também fontes/configurações do fornecedor Qt.
Não foi criada uma oferta escrita nem um serviço externo de fontes. O pacote
local antigo permanece inadequado para publicação; os novos avisos serão
integrados quando o build passar pela baseline.

### Fontes oficiais consultadas

- [Qt: LGPLv3 completa, seção 4](https://doc.qt.io/qt-6/lgpl.html) e
  [orientações de obrigações](https://www.qt.io/development/open-source-lgpl-obligations).
- [Qt: módulos e terceiros](https://doc.qt.io/qt-6/licensing.html) e
  [terceiros do Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html).
- [LGPL-2.1, texto e seções 4/6](https://spdx.org/licenses/LGPL-2.1-or-later.html).
- [GLib: licença e fonte upstream](https://docs.gtk.org/glib/).
- [GCC: runtime e exceção](https://gcc.gnu.org/onlinedocs/libstdc++/manual/license.html).
- [FreeType: opções e atribuição](https://freetype.org/license.html).
- [ICU 73.2: licença/avisos oficiais](https://raw.githubusercontent.com/unicode-org/icu/release-73-2/icu4c/LICENSE).
- [OpenSSL: licença](https://openssl-library.org/source/license/index.html) e
  [Apache-2.0, seção 4](https://www.apache.org/licenses/LICENSE-2.0).
- [Python: termos](https://docs.python.org/3.14/license.html) e
  [PyInstaller: exceção](https://pyinstaller.org/en/stable/license.html).
- [Microsoft: redistribuição Visual C++](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files?view=msvc-170).

Os copyrights locais, mantidos integralmente, identificam versões, autores e
condições específicas. A relação completa dos pacotes do build local segue abaixo;
não deve ser usada no lugar do inventário do futuro build Ubuntu 22.04/Windows.

### Pacotes nativos efetivamente identificados no build local

| Pacote binário | Versão binária | Pacote-fonte / versão | Binários associados |
| --- | --- | --- | --- |
| libatk-bridge2.0-0t64:amd64 | 2.60.4-0ubuntu0.1 | at-spi2-core / 2.60.4-0ubuntu0.1 | 1 |
| libatk1.0-0t64:amd64 | 2.60.4-0ubuntu0.1 | at-spi2-core / 2.60.4-0ubuntu0.1 | 1 |
| libatomic1:amd64 | 16-20260322-1ubuntu1 | gcc-16 / 16-20260322-1ubuntu1 | 1 |
| libatspi2.0-0t64:amd64 | 2.60.4-0ubuntu0.1 | at-spi2-core / 2.60.4-0ubuntu0.1 | 1 |
| libblkid1:amd64 | 2.41.3-3ubuntu2.2 | util-linux / 2.41.3-3ubuntu2.2 | 1 |
| libbrotli1:amd64 | 1.2.0-3build1 | brotli / 1.2.0-3build1 | 2 |
| libbz2-1.0:amd64 | 1.0.8-6ubuntu0.1 | bzip2 / 1.0.8-6ubuntu0.1 | 1 |
| libcairo-gobject2:amd64 | 1.18.4-3 | cairo / 1.18.4-3 | 1 |
| libcairo2:amd64 | 1.18.4-3 | cairo / 1.18.4-3 | 1 |
| libcom-err2:amd64 | 1.47.2-3ubuntu4 | e2fsprogs / 1.47.2-3ubuntu4 | 1 |
| libdatrie1:amd64 | 0.2.14-1 | libdatrie / 0.2.14-1 | 1 |
| libdbus-1-3:amd64 | 1.16.2-2ubuntu4 | dbus / 1.16.2-2ubuntu4 | 1 |
| libepoxy0:amd64 | 1.5.10-2build1 | libepoxy / 1.5.10-2build1 | 1 |
| libexpat1:amd64 | 2.7.4-1ubuntu0.2 | expat / 2.7.4-1ubuntu0.2 | 1 |
| libffi8:amd64 | 3.5.2-4 | libffi / 3.5.2-4 | 1 |
| libfontconfig1:amd64 | 2.17.1-3ubuntu1 | fontconfig / 2.17.1-3ubuntu1 | 1 |
| libfreetype6:amd64 | 2.14.2+dfsg-1ubuntu0.2 | freetype / 2.14.2+dfsg-1ubuntu0.2 | 1 |
| libfribidi0:amd64 | 1.0.16-5 | fribidi / 1.0.16-5 | 1 |
| libgcc-s1:amd64 | 16-20260322-1ubuntu1 | gcc-16 / 16-20260322-1ubuntu1 | 1 |
| libgdk-pixbuf-2.0-0:amd64 | 2.44.5+dfsg-4ubuntu1 | gdk-pixbuf / 2.44.5+dfsg-4ubuntu1 | 1 |
| libglib2.0-0t64:amd64 | 2.88.0-1ubuntu0.1 | glib2.0 / 2.88.0-1ubuntu0.1 | 5 |
| libglycin-2-0:amd64 | 2.1.5+ds-0ubuntu0.2 | glycin / 2.1.5+ds-0ubuntu0.2 | 1 |
| libgraphite2-3:amd64 | 1.3.14-11ubuntu1.1 | graphite2 / 1.3.14-11ubuntu1.1 | 1 |
| libgssapi-krb5-2:amd64 | 1.22.1-2ubuntu4.1 | krb5 / 1.22.1-2ubuntu4.1 | 1 |
| libgtk-3-0t64:amd64 | 3.24.52-0ubuntu1 | gtk+3.0 / 3.24.52-0ubuntu1 | 2 |
| libharfbuzz0b:amd64 | 12.3.2-2 | harfbuzz / 12.3.2-2 | 1 |
| libk5crypto3:amd64 | 1.22.1-2ubuntu4.1 | krb5 / 1.22.1-2ubuntu4.1 | 1 |
| libkeyutils1:amd64 | 1.6.3-6ubuntu3 | keyutils / 1.6.3-6ubuntu3 | 1 |
| libkrb5-3:amd64 | 1.22.1-2ubuntu4.1 | krb5 / 1.22.1-2ubuntu4.1 | 1 |
| libkrb5support0:amd64 | 1.22.1-2ubuntu4.1 | krb5 / 1.22.1-2ubuntu4.1 | 1 |
| liblcms2-2:amd64 | 2.17-1ubuntu0.2 | lcms2 / 2.17-1ubuntu0.2 | 1 |
| liblzma5:amd64 | 5.8.3-1 | xz-utils / 5.8.3-1 | 1 |
| libmount1:amd64 | 2.41.3-3ubuntu2.2 | util-linux / 2.41.3-3ubuntu2.2 | 1 |
| libpango-1.0-0:amd64 | 1.57.0-1 | pango1.0 / 1.57.0-1 | 1 |
| libpangocairo-1.0-0:amd64 | 1.57.0-1 | pango1.0 / 1.57.0-1 | 1 |
| libpangoft2-1.0-0:amd64 | 1.57.0-1 | pango1.0 / 1.57.0-1 | 1 |
| libpcre2-8-0:amd64 | 10.46-1build1 | pcre2 / 10.46-1build1 | 1 |
| libpixman-1-0:amd64 | 0.46.4-1 | pixman / 0.46.4-1 | 1 |
| libpng16-16t64:amd64 | 1.6.57-1ubuntu0.1 | libpng1.6 / 1.6.57-1ubuntu0.1 | 1 |
| libpython3.14:amd64 | 3.14.4-1ubuntu0.2 | python3.14 / 3.14.4-1ubuntu0.2 | 1 |
| libseccomp2:amd64 | 2.6.0-2ubuntu5 | libseccomp / 2.6.0-2ubuntu5 | 1 |
| libselinux1:amd64 | 3.9-4build1 | libselinux / 3.9-4build1 | 1 |
| libssl3t64:amd64 | 3.5.5-1ubuntu3.7 | openssl / 3.5.5-1ubuntu3.7 | 2 |
| libstdc++6:amd64 | 16-20260322-1ubuntu1 | gcc-16 / 16-20260322-1ubuntu1 | 1 |
| libsystemd0:amd64 | 259.5-0ubuntu3.4 | systemd / 259.5-0ubuntu3.4 | 1 |
| libthai0:amd64 | 0.1.30-1 | libthai / 0.1.30-1 | 1 |
| libx11-6:amd64 | 2:1.8.13-1ubuntu0.1 | libx11 / 2:1.8.13-1ubuntu0.1 | 1 |
| libx11-xcb1:amd64 | 2:1.8.13-1ubuntu0.1 | libx11 / 2:1.8.13-1ubuntu0.1 | 1 |
| libxau6:amd64 | 1:1.0.11-1build2 | libxau / 1:1.0.11-1build2 | 1 |
| libxcb-cursor0:amd64 | 0.1.6-1 | xcb-util-cursor / 0.1.6-1 | 1 |
| libxcb-glx0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-icccm4:amd64 | 0.4.2-1build1 | xcb-util-wm / 0.4.2-1build1 | 1 |
| libxcb-image0:amd64 | 0.4.0-2build2 | xcb-util-image / 0.4.0-2build2 | 1 |
| libxcb-keysyms1:amd64 | 0.4.1-1build1 | xcb-util-keysyms / 0.4.1-1build1 | 1 |
| libxcb-randr0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-render-util0:amd64 | 0.3.10-1build1 | xcb-util-renderutil / 0.3.10-1build1 | 1 |
| libxcb-render0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-shape0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-shm0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-sync1:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-util1:amd64 | 0.4.1-1build1 | xcb-util / 0.4.1-1build1 | 1 |
| libxcb-xfixes0:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcb-xkb1:amd64 | 1.17.0-2ubuntu1 | libxcb / 1.17.0-2ubuntu1 | 1 |
| libxcomposite1:amd64 | 1:0.4.6-1build1 | libxcomposite / 1:0.4.6-1build1 | 1 |
| libxcursor1:amd64 | 1:1.2.3-1build1 | libxcursor / 1:1.2.3-1build1 | 1 |
| libxdamage1:amd64 | 1:1.1.7-1 | libxdamage / 1:1.1.7-1 | 1 |
| libxdmcp6:amd64 | 1:1.1.5-2 | libxdmcp / 1:1.1.5-2 | 1 |
| libxext6:amd64 | 2:1.3.4-1build3 | libxext / 2:1.3.4-1build3 | 1 |
| libxfixes3:amd64 | 1:6.0.0-2build2 | libxfixes / 1:6.0.0-2build2 | 1 |
| libxi6:amd64 | 2:1.8.2-2 | libxi / 2:1.8.2-2 | 1 |
| libxinerama1:amd64 | 2:1.1.4-3build2 | libxinerama / 2:1.1.4-3build2 | 1 |
| libxkbcommon-x11-0:amd64 | 1.13.1-1 | libxkbcommon / 1.13.1-1 | 1 |
| libxkbcommon0:amd64 | 1.13.1-1 | libxkbcommon / 1.13.1-1 | 1 |
| libxrandr2:amd64 | 2:1.5.4-1build1 | libxrandr / 2:1.5.4-1build1 | 1 |
| libxrender1:amd64 | 1:0.9.12-1build1 | libxrender / 1:0.9.12-1build1 | 1 |
| libxres1:amd64 | 2:1.2.1-1build2 | libxres / 2:1.2.1-1build2 | 1 |
| libzstd1:amd64 | 1.5.7+dfsg-3 | libzstd / 1.5.7+dfsg-3 | 1 |
| zlib1g:amd64 | 1:1.3.dfsg+really1.3.1-1ubuntu3.1 | zlib / 1:1.3.dfsg+really1.3.1-1ubuntu3.1 | 1 |
