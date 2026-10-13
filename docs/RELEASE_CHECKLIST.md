# Preparação da release v0.1.0

Revisão local: 12/10/2026 (America/Sao_Paulo).
**Situação: preparação técnica avançada; publicação ainda não aprovada.**
Nenhum commit, push, tag, release ou upload foi realizado nesta revisão.
Complemento desta revisão: [investigação por componente e licenças](DISTRIBUTION_AUDIT.md).

Atualização de **13/10/2026**: repositório preparado para a primeira tentativa
real de CI, sem commit/push. **133 testes** aprovados nos dois Python; checksum
agora conferido antes da extração, uploads identificados como candidatos e
restritos a sucesso do respectivo job. As pendências de release continuam abertas.
Actions atualizadas para checkout v5, setup-python v6 e upload-artifact v6 com
Node 24, após conferir a retirada oficial do Node 20 dos runners em 23/09/2026.
Estado Git, inspeção de capturas/arquivos, comandos manuais e resultados esperados
estão em [FIRST_CI_RUN.md](FIRST_CI_RUN.md). Registros de 12/10 abaixo são históricos.

## Checklist verificado

| Item | Evidência local | Situação |
| --- | --- | --- |
| 1. GitHub Actions | `actionlint` 1.7.7 sem erros. Ubuntu 22.04 e Windows Server 2022 x64, testes Python 3.12/3.14, builds Python 3.12 após testes. Dependências fixadas por constraints; permissões `contents: read`; sem publicação de releases. | Configuração validada; execução no GitHub pendente. |
| 2. Dependências do executável | Pacote local inclui libpython, biblioteca padrão, Shiboken, QtCore/QtGui/QtWidgets, bibliotecas Qt e plugins. Inicialização Qt offscreen aprovada no host. Avisos de pacotes nativos disponíveis são preservados. | Verificado no host Linux; não garante todos os sistemas. |
| 3. Linux sem Python externo | Smoke test parte de pasta temporária com espaços, PATH sem Python e variáveis Python/Qt externas removidas. Contêiner Debian 13 com `/usr/local` mascarado e sem `/usr/bin/python3` carrega o runtime incluído, mas a interface falha por dependências nativas. | Runtime incluído confirmado; execução completa sem Python em sistema de destino pendente. |
| 4. Windows/PyInstaller | Spec sem caminhos Linux fixos, `console=False`/onedir. Checker confere PE AMD64/GUI, runtime, Qt DLLs/plugins e MSVC; smoke offscreen da pasta e ZIP extraído. Parser PE testado com arquivos sintéticos. | Automação preparada; nenhum EXE Windows real testado. Offscreen não equivale a teste interativo. |
| 5. `.gitignore` | Verificados ZIP/JSON e variantes de maiúsculas, TXT/CSV de resultados, logs, temporários, dist/build, `.env`, chaves e configurações locais. `requirements*.txt` pode ser versionado. | Verificado; não substitui revisão de staging nem impede `git add -f`. |
| 6. Dados e segredos no Git | `git ls-files` vazio; HEAD inexistente e sem histórico de commits. Arquivos candidatos do projeto revisados: fixtures/capturas fictícias; busca local por padrões de chaves privadas, AWS, tokens GitHub e JWT sem achados. Valores não são exibidos. | Nenhum dado sensível rastreado. Não há histórico para auditar. A busca não prova ausência universal de segredos. |
| 7. README | Instalação por fonte, uso da interface, estrutura onedir, bibliotecas Linux, localização dos artefatos, hashes e limites de validação descritos. Windows é alvo planejado, não compatibilidade declarada. | Verificado e corrigido. |
| 8. Licenças | 85 binários mapeados a 78 pacotes nativos; inventário completo documentado. Corrigida cópia de LICENSES Qt/PySide, 14 textos comuns e aviso ICU 73.2. Opções de licença e obrigações registradas com fontes oficiais. | Parcial. Fontes/patches nativos, termos Microsoft e substituição real ainda pendentes. |
| 9. Testes e erros | 129 testes aprovados em Python 3.12.3 e 3.14.4, preservando os 118 anteriores. Incluem comparação numérica/falha GLIBC, PE x64/GUI e omissões de avisos. Ruff aprovado; `pip check` aprovado na auditoria anterior. | Verificado localmente; matriz CI ainda pendente. |
| 10. Contribuições | README e CONTRIBUTING.md explicam ambiente, testes, PRs pequenos e reproduções fictícias. SECURITY.md orienta relato privado sem inventar canal de contato. | Documentação preparada; habilitar canal privado no GitHub antes da release. |

## Correções concretas nesta revisão

- O empacotador deixou de copiar todo o conteúdo de `src`, `tests`, `scripts`,
  `assets` e `docs`: só copia os tipos previstos e exclui arquivos ocultos,
  caches e links. As cópias geradas são recriadas para eliminar sobras anteriores.
- O inventário `COLLECT-00.toc` é conferido antes de empacotar. Arquivos pessoais
  extras na pasta do executável ou arquivos de runtime ausentes interrompem a
  operação sem apagá-los. Um inventário ausente exige refazer o build.
- Pacotes são identificados como `InstaFollowAnalyzer-0.1.0-<sistema>-x86_64`
  e recebem checksum `.sha256`. Hash não substitui assinatura/autenticidade.
- O teste de distribuição verifica arquivos do runtime, roda fora do projeto,
  remove influências do ambiente Python/Qt e também pode testar o arquivo final
  extraído (`python scripts/check_bundle.py --archive`).
- Avisos `copyright` de bibliotecas Debian/Ubuntu encontrados pelo inventário são
  copiados; `native_packages` registra versões, pacotes-fonte e itens não resolvidos.
  `sources_review_required` continua verdadeiro: os avisos não encerram a revisão.
- README deixou de tratar Windows como compatibilidade comprovada e distingue
  os módulos Python Qt excluídos de bibliotecas nativas que podem acompanhá-los.
- O mínimo de setuptools foi corrigido para o suporte a `license = "MIT"` em SPDX,
  e os arquivos MIT/avisos foram explicitados nos metadados. Wheel 0.1.0 construído
  localmente, sem publicar no PyPI.

## Teste de isolamento Linux e bloqueio de portabilidade

O pacote local foi construído com Python 3.14.4 no host com glibc 2.43.
Foi testado em contêiner descartável baseado na imagem local `python:3.12-slim`
(ID `423ed6ab25b1`), cujo sistema é Debian 13.5 com glibc 2.41.
`/usr/local` foi mascarado por um filesystem vazio e não havia Python em
`/usr/bin`; o pacote estava montado somente para leitura.

1. Sem bibliotecas gráficas adicionais: falhou por ausência de `libGL.so.1`.
2. Após instalar `libgl1` e `libegl1` **somente no contêiner descartável**:
   falhou porque a `libglib-2.0.so.0` incluída exige `GLIBC_2.43`.

Portanto, **o pacote local não deve ser usado como artefato público portátil**.
Esse teste comprova uma incompatibilidade concreta, não uma falha de Python
externo. O workflow configurado no Ubuntu 22.04 é o caminho de build previsto;
é necessário executar e testar seu artefato antes de aprová-lo.
Nenhuma configuração global do host foi alterada.

## Pendências para aprovação pública

- [ ] Executar o workflow no GitHub e conferir todos os jobs, artefatos, relatório ABI e checksums.
- [ ] Testar o ZIP Windows em Windows 10 e 11 x86_64 **sem Python instalado**.
      Confirmar ausência de console, inicialização, importação ZIP/pasta, busca,
      ordenação, cópia, abertura explícita de perfil, TXT/CSV, erros e temas.
- [ ] Testar o artefato Linux produzido no Ubuntu 22.04 em máquinas/VMs de destino
      sem Python, com bibliotecas gráficas documentadas. Registrar distribuição,
      versão da glibc, arquitetura e resultado. Não usar o pacote local glibc 2.43.
- [ ] Testar sessões gráficas reais X11/Wayland, seleção de arquivos, drag and drop,
      teclado, redimensionamento e pastas com espaços/caracteres não ASCII.
- [ ] Revisar o manifesto **dos builds finais** de cada sistema. Entregar avisos,
      fontes correspondentes e patches quando exigidos, inclusive de bibliotecas
      nativas do sistema. Conferir também componentes de runtime Microsoft no Windows.
- [ ] Confirmar substituição de bibliotecas LGPL por builds modificados de ABI compatível.
- [ ] Habilitar relato privado de vulnerabilidades no GitHub ou definir canal privado.
- [ ] Antes de um commit autorizado, revisar `git status`/staging e repetir busca de
      dados sensíveis. Atualmente todos os arquivos de projeto estão sem rastreamento.
- [ ] Após aprovação humana, decidir publicação/tag `v0.1.0` e anexar apenas os
      artefatos aprovados e seus checksums. Nenhuma dessas ações foi automatizada.

## Referências primárias consultadas

- [PyInstaller: runtime e builds por sistema](https://pyinstaller.org/en/stable/operating-mode.html)
- [PyInstaller: licença e exceção](https://pyinstaller.org/en/stable/license.html)
- [Qt: obrigações LGPL/GPL](https://www.qt.io/development/open-source-lgpl-obligations)
- [Setuptools: configuração e suporte SPDX](https://setuptools.pypa.io/en/latest/userguide/pyproject_config.html)
- [setup-python: cache pip](https://github.com/actions/setup-python/blob/v5/src/cache-distributions/pip-cache.ts)

## Resultado das quatro etapas complementares

- [x] Linux: confirmados `ubuntu-22.04` e baseline glibc 2.35 no workflow;
      acrescentada asserção do host e auditoria ELF automática, preservada mesmo
      em falha. O empacotador recusa requisitos acima da baseline antes de downloads.
- [x] Causa local medida: libglib e liblcms2 exigem GLIBC_2.43; Python 3.14 e outras
      bibliotecas exigem 2.38; 37 dos 168 ELF excedem 2.35. Bootloader exige 2.14;
      QtCore/Gui exigem 2.34. O relatório por arquivo está em `build/linux-abi.json`.
- [x] Bloqueio de empacotamento exercitado no pacote real; o arquivo antigo não
      foi substituído. Ele continua incompatível e sem os novos avisos integrados.
- [x] Windows: paths/hook revisados, runner fixado em Windows Server 2022 x64,
      checagens PE/DLLs/plugins e smoke offscreen preparados. Nenhum job acionado.
- [x] Licenciamento: preparação local separada confirmou 38 textos SPDX Qt, 8 PySide,
      14 textos comuns e aviso oficial ICU. Inventário e limites documentados em
      DISTRIBUTION_AUDIT.md; não se concluiu conformidade apenas pelos avisos.
- [x] Validação: 129 testes nos dois Python, lint/formatação e actionlint aprovados.
      Smoke do arquivo Linux **anterior** passou no host; não é um novo artefato
      da baseline. Todos os arquivos Python de `src` coincidem com os do pacote anterior.
- [ ] Novo artefato Linux Ubuntu 22.04 aprovado por ABI e execução em sistemas de destino.
- [ ] EXE Windows realmente produzido e testado no runner, seguido por testes interativos.
- [ ] Fontes/patches nativos e revisão de licenciamento dos dois artefatos finais.

Nesta etapa não foram alterados a glibc, a interface ou a lógica de análise,
nem executadas ações remotas de build/publicação. A consulta externa realizada
foi de documentação e avisos oficiais de licença.
