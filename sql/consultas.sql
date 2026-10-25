-- 1. Os 10 bancos mais baratos no consignado (período mais recente)
SELECT i.nome AS banco, m.segmento, m.modalidade, t.taxa_mes, t.taxa_ano
FROM taxas t
JOIN instituicoes i ON i.cnpj8 = t.cnpj8
JOIN modalidades m ON m.codigo_segmento = t.codigo_segmento AND m.codigo_modalidade = t.codigo_modalidade
WHERE t.inicio_periodo = (SELECT MAX(inicio_periodo) FROM taxas)
  AND m.modalidade LIKE 'Crédito pessoal consignado%'  -- INSS, público e privado (não pega o "não consignado")
ORDER BY t.taxa_mes
LIMIT 10;

-- 2. Diferença entre o banco mais caro e o mais barato em cada modalidade (período mais recente)
SELECT m.segmento, m.modalidade,
       COUNT(*) AS bancos,
       MIN(t.taxa_mes) AS menor_taxa_mes,
       MAX(t.taxa_mes) AS maior_taxa_mes,
       MAX(t.taxa_mes) - MIN(t.taxa_mes) AS diferenca_pontos
FROM taxas t
JOIN modalidades m ON m.codigo_segmento = t.codigo_segmento AND m.codigo_modalidade = t.codigo_modalidade
WHERE t.inicio_periodo = (SELECT MAX(inicio_periodo) FROM taxas)
GROUP BY m.segmento, m.modalidade
ORDER BY diferenca_pontos DESC;

-- 3. Evolução da taxa média do cartão de crédito rotativo
SELECT t.inicio_periodo, ROUND(AVG(t.taxa_mes), 2) AS taxa_media_mes, COUNT(*) AS bancos
FROM taxas t
JOIN modalidades m ON m.codigo_segmento = t.codigo_segmento AND m.codigo_modalidade = t.codigo_modalidade
WHERE LOWER(m.modalidade) LIKE '%rotativo%'
GROUP BY t.inicio_periodo
ORDER BY t.inicio_periodo;

-- 4. Qualidade dos dados: motivos de descarte na última execução
SELECT motivo, COUNT(*) AS quantidade
FROM descartes
WHERE execucao_id = (SELECT MAX(id) FROM execucoes)
GROUP BY motivo
ORDER BY quantidade DESC;

-- 5. Histórico das execuções do pipeline
SELECT id, iniciada_em, desde, linhas_lidas, linhas_validas, linhas_descartadas, linhas_novas, status
FROM execucoes
ORDER BY id DESC;
