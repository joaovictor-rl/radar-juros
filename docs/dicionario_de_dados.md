# Dicionário de dados

Fonte: Banco Central do Brasil, "Taxas de juros de operações de crédito por instituição financeira" (médias de janelas de 5 dias úteis). Os dados são agregados por banco e modalidade e não contêm informação de nenhuma pessoa.

## instituicoes

Bancos e financeiras que informaram taxas ao Banco Central.

| Coluna | Tipo | Descrição |
|---|---|---|
| cnpj8 | texto (8) | Raiz do CNPJ (8 primeiros dígitos). Chave primária. |
| nome | texto | Nome da instituição. Se mudar, fica o mais recente. |

## taxas

Taxa média cobrada por cada banco, em cada modalidade, em cada período. Uma linha por período + segmento + modalidade + banco.

| Coluna | Tipo | Descrição |
|---|---|---|
| inicio_periodo | data | Início da janela de 5 dias úteis. Parte da chave primária. |
| fim_periodo | data | Fim da janela. |
| segmento | texto | PESSOA FÍSICA ou PESSOA JURÍDICA. Parte da chave primária. |
| modalidade | texto | Tipo de crédito (ex.: consignado, rotativo do cartão, veículos). Parte da chave primária. |
| cnpj8 | texto (8) | Banco. Chave estrangeira para `instituicoes`. Parte da chave primária. |
| posicao | inteiro | Posição do banco no ranking da modalidade (1 = menor taxa). |
| taxa_mes | decimal | Taxa média ao mês, em %. |
| taxa_ano | decimal | Taxa média ao ano, em %. |

## Regras de qualidade

Cada linha recebida da API passa pelas regras abaixo, nesta ordem. A linha é descartada na primeira em que falhar, e o resumo dos descartes aparece no final da execução.

1. **Campo obrigatório vazio:** todas as colunas precisam estar preenchidas.
2. **Período inválido:** o fim do período não pode ser anterior ao início.
3. **Taxa negativa:** taxas ao mês e ao ano não podem ser negativas.
4. **Taxa zerada:** 0,00% ao mês não é uma taxa real de crédito; é dado não informado pelo banco.
5. **CNPJ inválido:** a raiz do CNPJ precisa ter 8 dígitos (CNPJs mais curtos são completados com zeros à esquerda antes).
6. **Registro duplicado:** a mesma combinação de período, segmento, modalidade e banco só entra uma vez.

## taxas.csv

Arquivo gerado a cada execução com a junção das duas tabelas (o nome do banco no lugar só do CNPJ). É a base usada no relatório do Power BI. Usa `;` como separador e vírgula decimal.
