# Mídia do README

Capturas reais geradas pela suíte Playwright da aplicação, com SQLite temporário e dados fictícios. Não há captura de credenciais, dados de produção ou sessões de navegador.

O tour `product-tour.gif` usa 40 quadros em loop, com transições entre telas e deslocamento vertical sobre as capturas. É uma apresentação de screenshots, não uma gravação de ações em tempo real. O README também oferece as imagens estáticas para leitura sem movimento.

## Regeneração opcional

1. Execute `scripts/run_e2e.py` com o virtualenv do projeto para produzir os PNGs em `frontend/test-results`.
2. Em um ambiente com Pillow instalado, execute `python scripts/build_readme_media.py` a partir da raiz. Pillow é uma ferramenta de documentação, não uma dependência do sistema.
3. O script usa as fontes Segoe UI disponíveis no Windows. Adapte os caminhos das fontes se usar outro sistema.
4. Confira visualmente o GIF e as imagens antes de versionar. Nunca substitua as capturas por dados reais ou credenciais.

Última origem das capturas: execução local de 05/11/2026, com oito fluxos E2E aprovados. A interface pode evoluir depois desta data.
