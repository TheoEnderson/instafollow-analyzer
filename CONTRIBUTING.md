# Como contribuir

Use Python 3.12+ de 64 bits. Siga a instalação pelo código-fonte no README,
instalando `.[dev]` em um ambiente virtual. Abra uma issue para discutir mudanças
maiores antes de implementá-las. Envie pull requests pequenos, com descrição do
problema, mudança feita e verificações executadas.

Antes de enviar:

```bash
python -m pytest -q
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
```

Use o Python do ambiente virtual caso não o tenha ativado. Testes de interface
usam Qt offscreen; alterações visuais também precisam de revisão manual nos dois
temas e em janelas pequenas. Explique o que não conseguiu testar.

Mantenha o domínio independente de Qt. Não introduza rede, telemetria, login,
scraping ou automação de relações. Novos formatos de exportação precisam de
fixtures sintéticas que reproduzam a estrutura e de testes contra análise parcial.

Nunca anexe dados reais de usuários, ZIP/JSON exportados, credenciais ou tokens a
issues, pull requests, capturas ou logs. Crie uma reprodução mínima com nomes
fictícios. Confira `git diff --cached` e `git status` antes de enviar; `.gitignore`
não protege arquivos adicionados com `git add -f` nem remove arquivos já rastreados.

Contribuições ao código original são disponibilizadas sob a MIT do projeto.
Preserve avisos e licenças de terceiros. Para vulnerabilidades, consulte SECURITY.md.

Os workflows verificam Windows e Linux separadamente. Um teste offscreen ou uma
compilação bem-sucedida não substitui testes nos sistemas de destino da release.
