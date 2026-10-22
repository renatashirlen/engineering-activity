# Engineering Activity — Renata Shirlen

Atividade de desenvolvimento no **Portal RSC**, sistema web de gestão do processo de Reconhecimento de Saberes e Competências (RSC) da Universidade de Brasília, hospedado no GitLab institucional da UnB.

![Commits por mês no Portal RSC](assets/activity-chart.svg)

## Indicadores

<!-- stats:start -->
| Mês | Commits | Com assistência de IA registrada |
|---|---:|---:|
| 2026-07 | 15 | 0 |
| 2026-08 | 142 | 1 |
| 2026-09 | 183 | 40 |
| 2026-10 | 239 | 110 |
| **Total** | **579** | **151** |
<!-- stats:end -->

- Commits de autoria própria, de todos os ramos, contados uma vez por hash.
- **Excluídos:** commits de merge e de bump de versão.
- **"Assistência de IA registrada":** o desenvolvimento do projeto conta com ferramentas de IA (*AI-assisted*). Esta coluna mostra apenas os commits que registraram isso explicitamente no histórico, portanto é um piso, não o total de uso.
- O último mês é **parcial**. O histórico disponível começa em julho/2026.

## Tecnologias

Java 21, Spring Boot 3, PostgreSQL, Flyway, Testcontainers, Angular 21 (signals, standalone), Vitest, Playwright, GitLab CI.

## Sobre estes dados

- São estatísticas de atividade **externa ao GitHub**; não aparecem no gráfico de contribuições daqui.
- **Nenhum código, mensagem de commit, nome de arquivo ou dado de outras pessoas** do repositório institucional foi copiado. Só contagens mensais.
- Geração local e manual: `python3 scripts/aggregate_activity.py --repo <caminho> --author <e-mail> --write` (sem `--write` é só simulação).
