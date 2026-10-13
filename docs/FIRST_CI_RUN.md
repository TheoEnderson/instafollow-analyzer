# Primeira execução real no GitHub Actions

Revisão local: **13/10/2026**, America/Sao_Paulo.
**Pronto para o primeiro envio e tentativa real de CI; não é aprovação de release.**
Não houve staging, commit, troca de branch, configuração de remote, push, criação
de repositório, acionamento remoto de workflow ou publicação nesta revisão.

## Estado do repositório e arquivos candidatos

- Git já inicializado, branch `master`, sem HEAD/commits, índice vazio e sem remote.
- 43 arquivos candidatos após incluir este documento: 9 na raiz, 1 workflow,
  13 em `src`, 6 em `scripts`, 6 em `tests`, 3 capturas e 5 documentos/licenças em `docs`.
- Nenhum ZIP/JSON real de Instagram, CSV, chave privada ou arquivo de credenciais
  foi identificado entre os candidatos. Busca por padrões de chaves privadas,
  AWS, GitHub e JWT sem achados; isso não é uma prova universal de ausência de segredos.
- Os três PNG foram inspecionados visualmente. Os resultados mostram
  `estudio_demo`, `fotografia_demo` e `jardim_demo`, definidos literalmente em
  `scripts/screenshots.py`, sem leitura de exportação real. Os PNG não contêm
  chunks de texto/EXIF; possuem apenas IHDR, IDAT, IEND e pHYs.
- `tests/conftest.py` gera JSON/ZIP fictícios em diretórios temporários do pytest.
- `.gitignore` conferido para JSON/ZIP/JSONL, CSV/TXT (inclusive maiúsculas),
  `.env`, credenciais, chaves, diretórios locais, build/dist, logs e temporários.
  `requirements-build.txt` permanece versionável. Ignore não impede `git add -f`
  nem protege arquivos já rastreados; revisar staging antes do commit.
- Os arquivos Python de `src` coincidem byte a byte com os do pacote anterior.

## Workflow revisado

`desktop.yml` está em `.github/workflows`, com `push`, `pull_request` e
`workflow_dispatch`, sem filtro de branch ou de caminhos. O primeiro push que
incluir esse arquivo pode disparar o workflow, desde que Actions esteja habilitado
e as políticas da conta/organização permitam as actions utilizadas.
[Eventos GitHub](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#push).

| Parte | Configuração |
| --- | --- |
| Testes | Ubuntu 22.04 e Windows Server 2022 x64, Python 3.12/3.14: quatro combinações |
| Builds | Ubuntu 22.04 e Windows Server 2022 x64, Python 3.12: dois jobs após todos os testes |
| Dependências | Backend e instalação `.[dev]` em passos separados, constraints em requirements-build.txt; não é lock completo de sistema |
| Linux | Bibliotecas gráficas/binutils, asserção Ubuntu 22.04/glibc 2.35 e auditoria de símbolos ELF |
| Windows | PyInstaller nativo, PE x64/GUI, DLLs Qt/MSVC, plugins e runtime Python |
| Inicialização | Smoke offscreen fora do projeto e com PATH isolado, antes e depois da extração |
| Integridade | SHA-256 gerado pelo empacotador e conferido antes da extração no checker |
| Permissões | Apenas `contents: read`, sem secrets personalizados ou publicação de releases |

Rótulos conferidos na [documentação dos runners](https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
Nada foi executado no GitHub. `actionlint` valida configuração, não a instalação,
o ambiente ou o resultado dos jobs remotos.

Correção necessária identificada nesta revisão: as versões anteriores das actions
declaravam Node 20, retirado dos runners em 23/09/2026. Atualizadas para
`checkout@v5`, `setup-python@v6` e `upload-artifact@v6`, cujos metadados oficiais
declaram `node24`. Não foi usada variável para reativar runtime inseguro.
[Aviso oficial de retirada](https://github.blog/changelog/2026-09-23-node-20-is-no-longer-available-in-github-actions/).
Evidências: [checkout](https://raw.githubusercontent.com/actions/checkout/v5/action.yml),
[setup-python](https://raw.githubusercontent.com/actions/setup-python/v6/action.yml) e
[upload-artifact](https://raw.githubusercontent.com/actions/upload-artifact/v6/action.yml).

## Artefatos e tratamento de falhas

O upload de candidatos exige `success()` no respectivo job. Não há
`continue-on-error` nas verificações. Falhas de testes impedem os builds; falhas
de ABI, inventário, empacotamento, avisos obrigatórios, checksum ou smoke test
impedem o upload do pacote daquele sistema.

Há uma exceção deliberada para diagnóstico: `Linux-ABI-audit` usa `always()`
para guardar somente `build/linux-abi.json` quando disponível. Não contém um
executável e não deve ser confundido com um pacote aprovado. Ausência desse
relatório gera aviso, sem esconder a falha original.

Os builds são independentes: um candidato Windows pode existir mesmo com o job
Linux vermelho. Candidatos são destinados a testes manuais, **não** certificam
conformidade de licenças, funcionamento em todos os sistemas ou aprovação pública.
As pendências de fontes/patches nativos continuam registradas em
[DISTRIBUTION_AUDIT.md](DISTRIBUTION_AUDIT.md).

Após sucesso, em **Actions → Tests and desktop builds → execução → Artifacts**:

- `InstaFollowAnalyzer-Linux-x86_64-candidate`: TAR.GZ interno + `.sha256`.
- `InstaFollowAnalyzer-Windows-x86_64-candidate`: ZIP interno + `.sha256`.
- `Linux-ABI-audit`: relatório diagnóstico, se produzido.

Retenção configurada em 14 dias. Faça download antes da expiração. O GitHub
entrega o artifact em um ZIP externo: extraia esse invólucro primeiro, depois
confira o checksum do TAR.GZ/ZIP **interno**. Para baixar é preciso acesso de
leitura à execução e estar autenticado.
[Download de artefatos](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/download-workflow-artifacts).

O pacote deve conter executável, `_internal` com runtime/Qt/plugins, README,
LICENSE/THIRD_PARTY_NOTICES, CONTRIBUTING/SECURITY, fontes do aplicativo, capturas
fictícias, fontes/avisos de terceiros e manifesto. No Linux, inclui também o
relatório ABI. Os JSON de manifesto/atribuições de terceiros e ZIP da biblioteca
padrão Python são arquivos de distribuição, não exportações do Instagram.

## Evidências locais desta revisão

- **133 testes aprovados** em Python 3.12.3 e 3.14.4; preservados os 129 anteriores.
  Quatro regressões novas cobrem alteração do pacote e checksum ausente/malformado
  ou associado ao nome errado.
- Ruff (lint/formatação), `actionlint` 1.7.7 e `pip check` aprovados.
- No arquivo Linux **anterior**, conferidos checksum, documentos/runtime/fontes,
  tipos permitidos nas fontes da aplicação e seis hashes de fontes de terceiros.
  Nenhuma exportação pessoal foi identificada nessa inspeção.
- Smoke desse arquivo anterior extraído passou no host com PATH isolado. Não
  comprova execução em máquina sem Python instalado nem interação gráfica.
- Empacotamento real local recusado: 37 de 168 ELF exigem mais que glibc 2.35,
  chegando a GLIBC_2.43. Arquivo anterior preservado; nenhum pacote novo criado.
  Não usamos esse pacote local como candidato. Não se desativou a auditoria.

## Primeiro commit e push — execução manual pelo mantenedor

Crie manualmente um repositório GitHub **vazio**, sem inicializar README, licença
ou gitignore, e escolha sua visibilidade. Habilite Actions, se necessário.
Substitua `SEU_USUARIO` pela conta/organização e ajuste o nome do repositório.
Use a autenticação normal do Git; não coloque tokens na URL ou nos arquivos.

Na pasta do projeto, prepare e **revise** o staging:

```bash
git status --short
git add --dry-run -- .
git add -- .github .gitignore CONTRIBUTING.md InstaFollowAnalyzer.spec LICENSE README.md SECURITY.md THIRD_PARTY_NOTICES.md assets docs pyproject.toml requirements-build.txt scripts src tests
git diff --cached --stat
git diff --cached --check
git diff --cached
```

Se a revisão revelar dados pessoais ou arquivos inesperados, corrija antes de
continuar. O comando `git add` acima é uma instrução para execução humana e não
foi executado nesta revisão. Se Git pedir identidade, configure nome/email locais;
você pode usar o endereço privado `noreply` fornecido pelo GitHub.

Depois de revisar, execute:

```bash
git commit -m "Prepare v0.1.0 for initial CI validation"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO/instafollow-analyzer.git
git remote -v
git push -u origin main
```

O remote não existe atualmente. Se você já o tiver configurado quando executar
estas instruções, confira-o em vez de repetir `remote add`. Se o destino tiver
histórico, resolva essa diferença; não use force push para contorná-la.

## Resultados a analisar após o push

- [ ] Workflow iniciado no SHA do primeiro commit, sem falha de política/permissão.
- [ ] Quatro combinações de testes aprovadas, observando skips no Windows.
- [ ] Instalação das versões fixadas e downloads oficiais de fontes concluídos.
- [ ] Build Linux realmente em Ubuntu 22.04/glibc 2.35 e relatório ABI aprovado.
- [ ] Build Windows realmente produzido; PE/DLLs e smoke da pasta/ZIP aprovados.
- [ ] Os dois candidatos e checksums estão disponíveis para download e conferem.
- [ ] Manifestos dos builds finais revisados quanto a dependências, fontes,
      avisos e ausência de dados pessoais; licenciamento nativo ainda precisa
      cumprir as obrigações de fontes/patches aplicáveis.
- [ ] Testes Windows 10/11 e Linux de destino sem Python, com interação gráfica,
      importação fictícia, busca, ordenação, cópia, exportação, temas e erros.

Somente após essas evidências será possível avaliar aprovação de release.
Nenhuma release é criada pelo workflow.
