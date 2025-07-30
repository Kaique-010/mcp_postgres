RELACIONAMENTOS_MCP = {
    ("Itenspedidovenda", "Produtos"): ("iped_prod", "prod_codi"),
    ("Itenspedidovenda", "PedidosVenda"): ("iped_pedi", "pedi_nume"),
    ("PedidosVenda", "Entidades"): ("pedi_forn", "enti_clie"),
    ("Produtos", "Entidades"): ("prod_forn", "enti_clie"),
    ("Itenspedidovenda", "Entidades"): ("iped_forn", "enti_clie"),
    ("Produtos", "PedidosVenda"): ("prod_pedi", "pedi_nume"),
}
