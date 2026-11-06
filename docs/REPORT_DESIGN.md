# Diagramação dos relatórios — referência Farol Estratégico

Referência visual única: arquivo farol-30_v11.html fornecido pelo responsável. Seu conteúdo, dados, metas, integrações e scripts não foram importados para a aplicação.

## HTML

- Cabeçalho azul em degradê horizontal, título do relatório, controles, navegação lateral por seções, barra de contexto e filtros, seguindo a estrutura do Farol.
- Título e subtítulo em página clara, seguidos por síntese executiva, indicadores, gráficos, tabelas e histórico detalhado.
- Síntese em três blocos (situação, atenção e evidência), seis KPIs com borda por significado e valores derivados do recorte autorizado.
- Gráfico de rosca por etapa com legenda numérica; barras de permanência e esforço; sinais operacionais objetivos, sem score subjetivo ou tendências inventadas.
- Sprints, backlog, relação consolidada e históricos individuais em seções próprias; controles reais para expandir/recolher cards e imprimir.
- Figtree normal/negrito e Lato incorporados; funciona offline. Não depende do arquivo Farol nem de bibliotecas/CDNs externas.
- Motion finito de até 500 ms, pausa manual, suporte a movimento reduzido. O logo não é animado. Os dados não são animados para valores intermediários fictícios.
- Layout de 390 px sem vazamento horizontal; tabelas mantêm região de rolagem. Impressão expande os cards e remove navegação/controles.

## PDF

Modelo paginado em A4 paisagem, com cabeçalho/rodapé, logotipo, paginação, título e subtítulo em fundo claro, seguido pela síntese e pelos KPIs, em linha com o modo de impressão do Farol. Gestão de sprints/backlog, carteira, históricos e metodologia são capítulos separados. Tabelas repetem cabeçalhos e referências ao card nas continuações, com quebra por linha. Os detalhes completos podem ocupar várias páginas, conforme volume do histórico.

O PDF usa desenho vetorial dos gráficos, não uma captura de tela: preserva legibilidade e texto pesquisável. HTML e PDF usam o mesmo modelo de leitura executiva em report_layout.py.

## Integridade e revisão

Fórmulas, permissões, filtros e separação financeira permanecem no backend. Textos são escapados, HTML possui CSP restritiva e o PDF não inclui JavaScript. Divisões por zero e ausência de evidência são explícitas. O relatório não é uma certificação de conformidade institucional ou de acessibilidade integral do PDF.

Amostras para revisão usam somente dados fictícios. scripts/preview_report_design.py gera HTML/PDF em artifacts/report-farol sem acessar banco. A pasta artifacts é local e não entra na aplicação. A saída PDF é renderizada para inspeção visual; a revisão visual do HTML depende da abertura em navegador. Os testes automatizados cobrem exportação, escopo, ausência de dados financeiros sem autorização, abertura offline e movimento reduzido.
