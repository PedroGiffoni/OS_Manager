# Estratégia de banco e migração futura

SQLite local e persistente é a solução temporária para desenvolvimento/testes, sem serviço externo, conta ou custo de contratação. Não é uma escolha definitiva para implantação institucional multiusuário. Quando a TI informar o SGBD, realizar avaliação própria; mudar DATABASE_URL não garante compatibilidade funcional, operacional ou de dados.

## Contrato atual

DATABASE_URL tem padrão sqlite:///./data/os_manager.db. Conexões e sessões ficam em app/db.py. Apenas infraestrutura habilita foreign_keys, WAL e busy_timeout. Alembic controla o esquema, com histórico de revisões. Integração/E2E usam arquivos temporários separados. Dinheiro e duração são inteiros; JSON é validado no serviço; booleanos usam SQLAlchemy Boolean; IDs são inteiros; timestamps ISO 8601 UTC são String por opção portável desta fase. A avaliação de destino pode recomendar DateTime com timezone e tipos JSON específicos.

SQLite serializa escritores. Versões otimistas e constraints compostas protegem vínculos, snapshots e aprovações, mas contenção/desempenho dependem de testes. UNIQUE com colunas NULL permite múltiplos vínculos históricos inativos em SQLite; outros SGBDs podem ter semântica diferente e exigir índice filtrado ou mudança de modelo. Verificar também índices, tamanho de texto, JSON, BLOB, sequências/identity, collation, limites, transações, isolamento e constraints em batch.

## Roteiro obrigatório

1. Confirmar com TI: SGBD/versão, drivers homologados, ambiente, identidade, TLS, segregação, backups, LGPD, integrações, permissões, observabilidade, volume e concorrência esperados.
2. Fazer backup consistente do SQLite pela API de backup SQLite com escritas pausadas. Não copiar apenas o .db enquanto WAL estiver ativo. Gerar checksum, inventário por tabela, totais de minutos/centavos, aprovações e snapshots; incluir BLOBs e hashes de anexos.
3. Criar ambiente de homologação separado, sem tocar no banco local original. Instalar driver, configurar credenciais por ambiente e adaptar tipos/migrações SQLAlchemy/Alembic. Inspecionar DDL gerado e reversões.
4. Preparar ETL explícito em ordem de chaves estrangeiras; preservar IDs, UTC, hashes de senha/sessão conforme política, referências de tarifas/aprovações, precisão e versões. Invalidar sessões no corte se essa for a política aprovada.
5. Exportar dados por tabela em formato tipado, documentando JSON, booleanos e BLOBs. Aplicar criptografia e acesso restrito aos arquivos financeiros; não usar o export operacional XLSX/PDF como mecanismo de migração.
6. Validar contagens, FKs, duplicidades ativas, checksums de anexos, valores exatos, custo por aprovação/tarefa/fornecedor/sprint, histórias de reabertura, snapshots e propriedades de idempotência.
7. Executar toda a suíte da API, autorização horizontal/vertical, E2E, regressão de relatórios e testes de carga/concorrência no SGBD destino. Validar transações sob falha, locks e índices reais.
8. Homologar com usuários/TI, definir janela de corte, congelar escritas, fazer backup final, repetir ETL e reconciliação e liberar somente após aceite formal.

## Rollback

Preservar SQLite e exportação de origem imutáveis e com acesso restrito. Definir prazo e gatilhos de retorno, RPO/RTO e responsável. Se o destino ainda não recebeu escritas institucionais, reverter configuração e retomar a origem após checagem. Se recebeu escritas, reconciliar explicitamente antes do retorno: não sobrescrever o SQLite nem executar downgrade destrutivo como substituto de recuperação. Testar restauração antes do corte e documentar a decisão.