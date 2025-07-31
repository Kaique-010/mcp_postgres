# Filtros naturais expandidos com sinônimos e variações
FILTROS_NATURAIS = {
    # Valores monetários e totais
    "total faturado": "pedi_tota",
    "faturamento": "pedi_tota",
    "faturamento total": "pedi_tota",
    "valor total": "pedi_tota",
    "receita": "pedi_tota",
    "receita total": "pedi_tota",
    "vendas": "pedi_tota",
    "total de vendas": "pedi_tota",
    "total vendido": "pedi_tota",
    "valor faturado": "pedi_tota",
    "montante": "pedi_tota",
    
    # Valores por item
    "total faturado por item": "iped_tota",
    "valor do item": "iped_tota",
    "total do item": "iped_tota",
    "subtotal": "iped_tota",
    
    # Quantidades
    "total quantidade": "iped_quan",
    "quantidade": "iped_quan",
    "quantidade vendida": "iped_quan",
    "qtd": "iped_quan",
    "qtde": "iped_quan",
    "total itens": "iped_quan",
    "itens vendidos": "iped_quan",
    "unidades": "iped_quan",
    "unidades vendidas": "iped_quan",
    
    # Pedidos
    "total pedidos": "pedi_nume",
    "pedidos": "pedi_nume",
    "número de pedidos": "pedi_nume",
    "qtd pedidos": "pedi_nume",
    "quantidade de pedidos": "pedi_nume",
    "pedidos realizados": "pedi_nume",
    "vendas realizadas": "pedi_nume",
    
    # Clientes
    "total clientes": "enti_tipo_enti = 'CL'",
    "clientes": "enti_nome",
    "cliente": "enti_nome",
    "compradores": "enti_nome",
    "comprador": "enti_nome",
    "nome do cliente": "enti_nome",
    "razão social": "enti_nome",
    
    # Vendedores
    "total vendedores": "enti_tipo_enti = 'VE'",
    "vendedores": "enti_nome",
    "vendedor": "enti_nome",
    "representante": "enti_nome",
    "consultor": "enti_nome",
    "nome do vendedor": "enti_nome",
    
    # Produtos
    "total produtos": "prod_nome",
    "produtos": "prod_nome",
    "produto": "prod_nome",
    "item": "prod_nome",
    "itens": "prod_nome",
    "mercadoria": "prod_nome",
    "mercadorias": "prod_nome",
    "nome do produto": "prod_nome",
    "descrição": "prod_nome",
    "código do produto": "prod_codi",
    "código": "prod_codi",
    
    # Datas e períodos
    "data": "pedi_data",
    "data do pedido": "pedi_data",
    "data da venda": "pedi_data",
    "período": "pedi_data",
    "quando": "pedi_data",
    
    # Preços unitários
    "preço unitário": "iped_unit",
    "valor unitário": "iped_unit",
    "preço": "iped_unit",
    "valor": "iped_unit",
    
    # Descontos
    "desconto": "iped_desc",
    "desconto aplicado": "iped_desc",
    "valor do desconto": "iped_desc",
    "abatimento": "iped_desc",
    
    # Status e tipos
    "status": "pedi_stat",
    "situação": "pedi_stat",
    "estado do pedido": "pedi_stat",
    "cancelado": "pedi_canc = true",
    "cancelados": "pedi_canc = true",
    "ativo": "pedi_canc = false",
    "ativos": "pedi_canc = false",
    
    # Empresas e filiais
    "empresa": "pedi_empr",
    "filial": "pedi_fili",
    "loja": "pedi_fili",
    "unidade": "pedi_fili",
    
    # Custos
    "custo": "iped_cust",
    "custo do produto": "iped_cust",
    "valor de custo": "iped_cust",
    
    # Frete
    "frete": "iped_fret",
    "valor do frete": "iped_fret",
    "custo de frete": "iped_fret",
    
    # Margem e lucro
    "margem": "(iped_tota - iped_cust)",
    "lucro": "(iped_tota - iped_cust)",
    "resultado": "(iped_tota - iped_cust)",
    "ganho": "(iped_tota - iped_cust)",
}

# Filtros de período mais específicos
FILTROS_PERIODO = {
    "hoje": "DATE(pedi_data) = CURRENT_DATE",
    "ontem": "DATE(pedi_data) = CURRENT_DATE - INTERVAL '1 day'",
    "esta semana": "DATE_TRUNC('week', pedi_data) = DATE_TRUNC('week', CURRENT_DATE)",
    "semana passada": "DATE_TRUNC('week', pedi_data) = DATE_TRUNC('week', CURRENT_DATE - INTERVAL '1 week')",
    "este mês": "DATE_TRUNC('month', pedi_data) = DATE_TRUNC('month', CURRENT_DATE)",
    "mês passado": "DATE_TRUNC('month', pedi_data) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')",
    "este ano": "EXTRACT(YEAR FROM pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)",
    "ano passado": "EXTRACT(YEAR FROM pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE) - 1",
    "últimos 7 dias": "pedi_data >= CURRENT_DATE - INTERVAL '7 days'",
    "últimos 30 dias": "pedi_data >= CURRENT_DATE - INTERVAL '30 days'",
    "últimos 90 dias": "pedi_data >= CURRENT_DATE - INTERVAL '90 days'",
    "último trimestre": "pedi_data >= DATE_TRUNC('quarter', CURRENT_DATE - INTERVAL '3 months')",
}

# Filtros de comparação
FILTROS_COMPARACAO = {
    "maior que": ">",
    "menor que": "<",
    "igual a": "=",
    "diferente de": "!=",
    "maior ou igual": ">=",
    "menor ou igual": "<=",
    "acima de": ">",
    "abaixo de": "<",
    "superior a": ">",
    "inferior a": "<",
}
