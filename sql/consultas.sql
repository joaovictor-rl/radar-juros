-- 1. Os 10 bancos mais baratos no consignado (período mais recente)
SELECT i.nome AS banco, t.modalidade, t.taxa_mes, t.taxa_ano
FROM taxas t
JOIN instituicoes i ON i.cnpj8 = t.cnpj8
WHERE t.inicio_periodo = (SELECT MAX(inicio_periodo) FROM taxas)
  AND t.modalidade LIKE 'Crédito pessoal consignado%'
ORDER BY t.taxa_mes
LIMIT 10;

-- 2. Diferença entre o banco mais caro e o mais barato em cada modalidade (período mais recente)
SELECT segmento, modalidade,
       COUNT(*) AS bancos,
       MIN(taxa_mes) AS menor_taxa_mes,
       MAX(taxa_mes) AS maior_taxa_mes,
       ROUND(MAX(taxa_mes) - MIN(taxa_mes), 2) AS diferenca_pontos
FROM taxas
WHERE inicio_periodo = (SELECT MAX(inicio_periodo) FROM taxas)
GROUP BY segmento, modalidade
ORDER BY diferenca_pontos DESC;

-- 3. Evolução da taxa média do rotativo do cartão
SELECT inicio_periodo, ROUND(AVG(taxa_mes), 2) AS taxa_media_mes, COUNT(*) AS bancos
FROM taxas
WHERE modalidade LIKE 'Cartão de crédito - rotativo%'
GROUP BY inicio_periodo
ORDER BY inicio_periodo;
