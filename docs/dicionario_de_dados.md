# Dicionário de dados

Fonte: Banco Central do Brasil, "Taxas de juros de operações de crédito por instituição financeira" (médias dos últimos 5 dias). Os dados são agregados por banco e modalidade e não contêm informação de nenhuma pessoa.

## instituicoes

Bancos e financeiras que informaram taxas ao Banco Central.

| Coluna | Tipo | Descrição |
|---|---|---|
| cnpj8 | texto (8) | Raiz do CNPJ (8 primeiros dígitos). Chave primária. |
| nome | texto | Nome da instituição. Se mudar, fica o mais recente. |

## modalidades

Tipos de crédito, separados por segmento.

| Coluna | Tipo | Descrição |
|---|---|---|
| codigo_segmento | texto | Código do segmento. Parte da chave primária. |
| codigo_modalidade | texto | Código da modalidade. Parte da chave primária. |
| segmento | texto | Pessoa física ou pessoa jurídica. |
| modalidade | texto | Tipo de crédito (ex.: consignado, cartão rotativo, veículos). |

## taxas

Taxa média cobrada por cada banco, em cada modalidade, em cada período. Uma linha por período + modalidade + banco.

| Coluna | Tipo | Descrição |
|---|---|---|
| inicio_periodo | data | Início do período de 5 dias. Parte da chave primária. |
| codigo_segmento | texto | Referência a `modalidades`. Parte da chave primária. |
| codigo_modalidade | texto | Referência a `modalidades`. Parte da chave primária. |
| cnpj8 | texto (8) | Referência a `instituicoes`. Parte da chave primária. |
| fim_periodo | data | Fim do período. |
| posicao | inteiro | Posição do banco no ranking do Banco Central (1 = menor taxa). |
| taxa_mes | decimal | Taxa média ao mês, em %. |
| taxa_ano | decimal | Taxa média ao ano, em %. |

## execucoes

Registro de cada vez que o pipeline rodou.

| Coluna | Tipo | Descrição |
|---|---|---|
| id | inteiro | Identificador da execução. |
| iniciada_em / finalizada_em | data e hora | Início e fim da execução. |
| desde | data | Data a partir da qual os dados foram buscados. |
| linhas_lidas | inteiro | Linhas recebidas da API. |
| linhas_validas | inteiro | Linhas aprovadas nas regras de qualidade. |
| linhas_descartadas | inteiro | Linhas reprovadas (ver `descartes`). |
| linhas_novas | inteiro | Linhas que ainda não existiam no banco. |
| status | texto | `em andamento`, `sucesso` ou `falha`. |
| erro | texto | Mensagem de erro, se houver. |

## descartes

Linhas reprovadas nas regras de qualidade, guardadas para auditoria.

| Coluna | Tipo | Descrição |
|---|---|---|
| id | inteiro | Identificador. |
| execucao_id | inteiro | Execução em que a linha foi descartada. |
| motivo | texto | Primeira regra em que a linha falhou. |
| registro | texto (JSON) | Conteúdo original da linha. |

## Regras de qualidade

Cada linha recebida da API passa pelas regras abaixo, nesta ordem. A linha é descartada na primeira em que falhar.

1. **Campo obrigatório vazio:** datas, códigos, nomes, CNPJ e taxas precisam estar preenchidos.
2. **Período inválido:** o fim do período não pode ser anterior ao início.
3. **Taxa negativa:** taxas ao mês e ao ano não podem ser negativas.
4. **Taxa zerada:** taxa de 0,00% ao mês não é uma taxa real de crédito; costuma ser dado não informado ou arredondado pelo banco (na carga de out/2025 a out/2026 foram 321 linhas, de 21 instituições).
5. **CNPJ inválido:** a raiz do CNPJ precisa ter 8 dígitos (CNPJs com menos dígitos são completados com zeros à esquerda antes da verificação).
6. **Registro duplicado:** a mesma combinação de período, modalidade e banco só entra uma vez.
