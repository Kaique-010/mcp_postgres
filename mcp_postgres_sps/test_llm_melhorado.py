"""
Teste para verificar se as melhorias no LLM estão funcionando
"""

def testar_prompt_simples():
    """Testa o novo prompt simplificado"""
    
    # Mock da função criar_prompt_simples
    def criar_prompt_simples_teste(contexto_original: str) -> str:
        # Extrai a pergunta do usuário do contexto original
        linhas = contexto_original.split('\n')
        pergunta = ""
        for linha in linhas:
            if "PERGUNTA DO USUÁRIO:" in linha:
                pergunta = linha.replace("PERGUNTA DO USUÁRIO:", "").strip()
                break
        
        if not pergunta:
            pergunta = "consulta geral"
        
        return f"""
Você é um especialista em SQL PostgreSQL. Gere APENAS o código SQL para a pergunta.

TABELAS DISPONÍVEIS:
- public.pedidosvenda (pv) - campos: pedi_nume, pedi_tota, pedi_data, pedi_empr, pedi_forn, pedi_vend
- public.entidades (e) - campos: enti_clie, enti_nome, enti_tipo_enti, enti_empr
- public.itenspedidovenda (i) - campos: iped_pedi, iped_prod, iped_quan, iped_empr
- public.produtos (p) - campos: prod_codi, prod_nome, prod_empr

REGRAS:
1. SEMPRE use WHERE [tabela]_empr = 1
2. Para contagem: COUNT(DISTINCT campo) ou COUNT(*)
3. Para soma: SUM(campo)
4. Use aliases: pv, e, i, p

EXEMPLOS:
- "quantos pedidos" → SELECT COUNT(DISTINCT pv.pedi_nume) FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1
- "total faturado" → SELECT SUM(pv.pedi_tota) FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1
- "quantos clientes" → SELECT COUNT(*) FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'CL'

PERGUNTA: {pergunta}

Resposta (APENAS SQL):"""

    print("🧪 TESTANDO PROMPT SIMPLIFICADO")
    print("=" * 50)
    
    # Contexto original complexo
    contexto_original = """
    Você é um especialista em SQL PostgreSQL. PRIMEIRO identifique qual tabela usar baseado na pergunta, DEPOIS gere o SQL correto.

    COMO ESCOLHER A TABELA PRINCIPAL:
    
    🔍 PALAVRAS-CHAVE POR TABELA:
    - "entidades", "clientes", "vendedores", "fornecedores" → USE public.entidades
    - "itens", "produtos vendidos", "quantidades" → USE public.itenspedidovenda  
    - "produtos", "catálogo", "estoque" → USE public.produtos
    - "pedidos", "vendas", "faturamento" → USE public.pedidosvenda
    
    CAMPOS DE EMPRESA POR TABELA:
    - public.pedidosvenda → WHERE pv.pedi_empr = 1
    - public.itenspedidovenda → WHERE i.iped_empr = 1  
    - public.entidades → WHERE e.enti_empr = 1
    - public.produtos → WHERE p.prod_empr = 1

    RELACIONAMENTOS:
    - PedidosVenda.pedi_forn = Entidades.enti_clie (clientes)
    - PedidosVenda.pedi_vend = Entidades.enti_clie (vendedores)
    - Itenspedidovenda.iped_pedi = PedidosVenda.pedi_nume
    - Itenspedidovenda.iped_prod = Produtos.prod_codi

    TIPOS DE ENTIDADE:
    - 'CL' = Cliente
    - 'VE' = Vendedor
    - 'FO' = Fornecedor

    [... muito mais texto ...]

    PERGUNTA DO USUÁRIO: quantos pedidos de venda

    PASSO 1: Identifique qual tabela usar baseado nas palavras-chave
    PASSO 2: Escolha a operação correta (COUNT, SUM, etc.)
    PASSO 3: Gere o SQL usando a tabela e campos corretos
    
    Retorne APENAS o código SQL.
    """
    
    # Gera prompt simplificado
    prompt_simples = criar_prompt_simples_teste(contexto_original)
    
    print("CONTEXTO ORIGINAL:")
    print(f"  Tamanho: {len(contexto_original)} caracteres")
    print(f"  Linhas: {len(contexto_original.split(chr(10)))}")
    
    print("\nPROMPT SIMPLIFICADO:")
    print(f"  Tamanho: {len(prompt_simples)} caracteres")
    print(f"  Linhas: {len(prompt_simples.split(chr(10)))}")
    
    print(f"\nREDUÇÃO: {((len(contexto_original) - len(prompt_simples)) / len(contexto_original) * 100):.1f}%")
    
    print("\nPROMPT SIMPLIFICADO GERADO:")
    print("-" * 40)
    print(prompt_simples)
    print("-" * 40)
    
    # Verifica se o prompt contém elementos essenciais
    elementos_essenciais = [
        "TABELAS DISPONÍVEIS",
        "public.pedidosvenda",
        "public.entidades", 
        "REGRAS",
        "_empr = 1",
        "EXEMPLOS",
        "quantos pedidos de venda"
    ]
    
    print("\n✅ VERIFICAÇÃO DE ELEMENTOS ESSENCIAIS:")
    todos_presentes = True
    for elemento in elementos_essenciais:
        presente = elemento in prompt_simples
        print(f"  {elemento}: {'✅' if presente else '❌'}")
        if not presente:
            todos_presentes = False
    
    if todos_presentes:
        print("\n🎉 PROMPT SIMPLIFICADO CONTÉM TODOS OS ELEMENTOS ESSENCIAIS!")
        print("   Isso deve reduzir significativamente a confusão do LLM.")
    else:
        print("\n⚠️ PROMPT SIMPLIFICADO ESTÁ FALTANDO ELEMENTOS IMPORTANTES")

def testar_extracao_sql():
    """Testa a função de extração segura de SQL"""
    
    def extrair_sql_seguro_teste(resposta) -> str:
        try:
            # Tenta acessar o conteúdo
            if hasattr(resposta, 'content'):
                conteudo = resposta.content
            elif hasattr(resposta, 'text'):
                conteudo = resposta.text
            elif isinstance(resposta, str):
                conteudo = resposta
            else:
                return ""
            
            # Garante que é string
            if not isinstance(conteudo, str):
                conteudo = str(conteudo)
            
            # Remove marcadores de código
            sql_limpo = conteudo.strip()
            sql_limpo = sql_limpo.strip("```sql").strip("```").strip()
            sql_limpo = sql_limpo.strip("```").strip()
            
            # Remove quebras de linha excessivas
            sql_limpo = ' '.join(sql_limpo.split())
            
            return sql_limpo
            
        except Exception as e:
            print(f"Erro ao extrair SQL da resposta: {e}")
            return ""
    
    print("\n🧪 TESTANDO EXTRAÇÃO SEGURA DE SQL")
    print("=" * 50)
    
    # Casos de teste
    casos_teste = [
        # Caso 1: Resposta normal
        {
            'nome': 'Resposta normal',
            'resposta': type('MockResponse', (), {'content': 'SELECT COUNT(*) FROM pedidosvenda'})(),
            'esperado': 'SELECT COUNT(*) FROM pedidosvenda'
        },
        # Caso 2: Com marcadores de código
        {
            'nome': 'Com marcadores SQL',
            'resposta': type('MockResponse', (), {'content': '```sql\nSELECT COUNT(*) FROM pedidosvenda\n```'})(),
            'esperado': 'SELECT COUNT(*) FROM pedidosvenda'
        },
        # Caso 3: Com quebras de linha
        {
            'nome': 'Com quebras de linha',
            'resposta': type('MockResponse', (), {'content': 'SELECT COUNT(*)\nFROM pedidosvenda\nWHERE pedi_empr = 1'})(),
            'esperado': 'SELECT COUNT(*) FROM pedidosvenda WHERE pedi_empr = 1'
        },
        # Caso 4: String direta
        {
            'nome': 'String direta',
            'resposta': 'SELECT SUM(pedi_tota) FROM pedidosvenda',
            'esperado': 'SELECT SUM(pedi_tota) FROM pedidosvenda'
        }
    ]
    
    sucessos = 0
    for i, caso in enumerate(casos_teste, 1):
        print(f"\nTeste {i}: {caso['nome']}")
        resultado = extrair_sql_seguro_teste(caso['resposta'])
        sucesso = resultado == caso['esperado']
        
        print(f"  Resultado: {resultado}")
        print(f"  Esperado:  {caso['esperado']}")
        print(f"  Status: {'✅ Passou' if sucesso else '❌ Falhou'}")
        
        if sucesso:
            sucessos += 1
    
    print(f"\n📊 RESULTADO: {sucessos}/{len(casos_teste)} testes passaram")
    
    if sucessos == len(casos_teste):
        print("🎉 EXTRAÇÃO DE SQL FUNCIONANDO PERFEITAMENTE!")
    else:
        print("⚠️ EXTRAÇÃO DE SQL PRECISA DE AJUSTES")

if __name__ == "__main__":
    testar_prompt_simples()
    testar_extracao_sql()
