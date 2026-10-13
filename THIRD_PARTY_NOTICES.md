# Componentes de terceiros e distribuição

O código original do InstaFollow Analyzer usa a licença MIT (arquivo LICENSE).
Essa licença não substitui as licenças de Python, Qt, PySide6, Shiboken ou das
bibliotecas nativas incluídas no executável.

A auditoria por componente, suas evidências e pendências estão em
[docs/DISTRIBUTION_AUDIT.md](docs/DISTRIBUTION_AUDIT.md).

## Qt, PySide6 e Shiboken

A edição comunitária do Qt for Python oferece LGPLv3/GPL e licença comercial.
Este projeto usa QtCore, QtGui e QtWidgets sob a opção LGPLv3, sem modificar
essas bibliotecas. Não usa módulos exclusivamente GPL como Qt Charts.
O empacotamento onedir preserva as bibliotecas compartilhadas separadas.

Ao redistribuir uma compilação sob LGPLv3:

- Preserve avisos de copyright, atribuições e os textos LGPLv3 e GPLv3.
- Entregue o código-fonte correspondente das bibliotecas LGPL, inclusive alterações
  e instruções necessárias à reconstrução, ou cumpra uma alternativa permitida
  pelas seções 4 da LGPLv3 e 6 da GPLv3. Um link genérico não substitui essas obrigações.
- Permita substituir/revincular as bibliotecas por versões modificadas compatíveis;
  não impeça engenharia reversa para depurar tais modificações.
- Forneça informações de instalação quando exigidas pela licença. Não imponha
  termos, assinatura ou mecanismos que impeçam o exercício desses direitos.
- Confira também as licenças e atribuições dos componentes incorporados ao Qt
  (por exemplo, fontes, codecs de imagem e bibliotecas de compressão).

O script `scripts/package.py` acompanha o pacote com fontes oficiais das versões
instaladas de PySide/Shiboken e módulos Qt incluídos, seus textos de licença e
arquivos de atribuição. Ele também registra versões das dependências e inclui
as fontes deste aplicativo. Esse passo requer internet apenas no computador
de desenvolvimento. O aplicativo distribuído não depende da rede para análise.

O distribuidor deve verificar alterações locais nas bibliotecas: fontes oficiais
não representam patches locais. A distribuição deste projeto não restringe a
substituição de bibliotecas nem a depuração permitida pelas licenças.

Referências oficiais:

- [Qt for Python: licenciamento](https://doc.qt.io/qtforpython-6/commercial/index.html)
- [Obrigações LGPL/GPL](https://www.qt.io/development/open-source-lgpl-obligations)
- [Licenciamento e módulos Qt](https://doc.qt.io/qt-6/licensing.html)
- [Código-fonte do PySide/Shiboken](https://code.qt.io/cgit/pyside/pyside-setup.git/)
- [Código-fonte Qt](https://download.qt.io/official_releases/qt/)

## Python e PyInstaller

Python é distribuído sob PSF License e avisos de componentes incorporados.
O pacote inclui o LICENSE da versão de Python utilizada no build.
PyInstaller usa GPL com exceção que permite distribuir aplicativos empacotados
sob a licença do próprio aplicativo; não altera a MIT deste projeto.
O pacote preserva também os avisos de PyInstaller e altgraph.

## Bibliotecas nativas do sistema

O PyInstaller pode copiar outras bibliotecas do sistema Linux, além de Qt/Python.
Os arquivos efetivamente incorporados variam conforme o runner. O manifesto
registra essa lista para revisão. Em Debian/Ubuntu, o empacotador também copia
os arquivos `copyright` disponíveis dos pacotes identificados pelo inventário
PyInstaller e registra versão e pacote-fonte em `native_packages` no manifesto.
Entradas não resolvidas permanecem explícitas. Copiar avisos não substitui
entregar fontes e patches quando a licença exigir. Os textos de licença
referenciados em `/usr/share/common-licenses` também são copiados. Os textos
SPDX das pastas `LICENSES` de Qt/PySide são extraídos além dos avisos individuais.
As bibliotecas ICU vendorizadas são tratadas separadamente: para o ICU 73.2
identificado localmente, inclui-se o aviso oficial completo, com os avisos de
terceiros, de `docs/licenses/ICU-73.2.license`. Versões principais desconhecidas
interrompem o empacotamento para revisão.

Este software usa FreeType, copyright © 1996–2025 David Turner, Robert Wilhelm
e Werner Lemberg (The FreeType Project, https://freetype.org/).
This software is based in part on the work of the Independent JPEG Group.
Os avisos aplicáveis e os de codecs/fontes incorporados precisam acompanhar o build final.

Copiar esses textos não substitui
entregar fontes e patches quando a licença exigir. Antes de publicar uma release, o distribuidor
deve preservar seus avisos e disponibilizar fontes correspondentes quando a
licença exigir, inclusive patches da distribuição Linux. O download automático
deste projeto cobre Qt, PySide/Shiboken e Python upstream; não cobre fontes de
todos os pacotes nativos da distribuição. Não trate esse script como uma
certificação de conformidade de uma release.

A revisão local identificou, por exemplo, GLib, GTK, ATK, Cairo, libsystemd e
outras bibliotecas nativas no pacote Linux. Portanto, incluir apenas fontes Qt
não encerra a análise das obrigações. A v0.1.0 deve permanecer sem publicação
até revisar o inventário do **build final de cada sistema**, conferir os avisos
e cumprir as obrigações de fontes correspondentes aplicáveis.

Referências de distribuição:

- [Funcionamento do PyInstaller](https://pyinstaller.org/en/stable/operating-mode.html)
- [Licença e exceção do PyInstaller](https://pyinstaller.org/en/stable/license.html)

Ferramentas de desenvolvimento (pytest e Ruff) não são dependências de execução
nem são incorporadas deliberadamente ao aplicativo.
