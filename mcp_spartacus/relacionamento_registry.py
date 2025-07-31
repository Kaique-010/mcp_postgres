# relacionamento_registry.py
TABELAS_CONHECIDAS = """
- pedidosvenda (pedi_nume INTEGER, pedi_data DATE, pedi_empr INTEGER, pedi_fili INTEGER, pedi_clie INTEGER, pedi_tota DECIMAL)
- itenspedidovenda (item_pedi INTEGER, item_prod INTEGER, item_qtd DECIMAL, item_valo DECIMAL)
- produtos (prod_codi INTEGER, prod_nome VARCHAR)
- entidades (enti_clie INTEGER, enti_nome VARCHAR, enti_tipo_enti VARCHAR, enti_cnpj VARCHAR, enti_tele VARCHAR, enti_email VARCHAR)

Relacionamentos:
- pedidosvenda.pedi_forn = entidades.enti_clie (cliente do pedido)
- itenspedidovenda.item_pedi = pedidosvenda.pedi_nume (itens do pedido)
- itenspedidovenda.item_prod = produtos.prod_codi (produto do item)
"""
