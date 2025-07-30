from langchain.tools import tool
from django.db import connection
from .utils import forcar_filtro_empresa, corrigir_group_by_aliases
import re
from .filtros_naturais import FILTROS_NATURAIS
from .relacionamento_registry import RELACIONAMENTOS_MCP

def corrigir_group_by_aliases(sql: str) -> str:
    substituicoes = {
        r"\bmes\b": "TO_CHAR(pedi_data, 'Month')",
        r"\bano\b": "EXTRACT(YEAR FROM pedi_data)",
        r"\bdia\b": "EXTRACT(DAY FROM pedi_data)",
        r"\bnome\b": "enti_nome",
        r"\bempresa\b": "prod_empr",
        r"\bempresas\b": "iped_empr",
        r"\bempr\b": "pedi_empr",
        r"\bempre\b": "enti_empr",
        r"\bproduto\b": "prod_nome",
        r"\bpedido\b": "pedi_nume",
        r"\bquantidade\b": "pedi_quan",
        r"\btotal\b": "pedi_tota",
        r"\bdata\b": "pedi_data",
    }
    for alias, funcao in substituicoes.items():
        sql = re.sub(rf"GROUP BY\s+{alias}", f"GROUP BY {funcao}", sql, flags=re.IGNORECASE)
    return sql
class ConsultaTool:
    def __init__(self, factory, llm):
        self.factory = factory
        self.filtros = FILTROS_NATURAIS
        self.relacionamentos = RELACIONAMENTOS_MCP
        self.llm = llm
        self.tool = self._gerar_tool()

    def detectar_campo_empresa(self) -> str:
        for model in self.factory.models:
            for field in model._meta.fields:
                if field.name.endswith("_empr"):
                    return field.name
        return "pedi_empr"  # fallback
    
    def _gerar_sql(self, query: str) -> str:
        # Adiciona relacionamentos
        for rel in self.relacionamentos:
            query = query.replace(rel[0], rel[1])
        return query
    
    def pre_process_query(self, query: str) -> str:
        q_lower = query.lower()
        filtro_tipo = None

        if "vendedor" in q_lower or "vendedores" in q_lower:
            filtro_tipo = "VE"
        elif "cliente" in q_lower or "clientes" in q_lower:
            filtro_tipo = "CL"

        if filtro_tipo and f"enti_tipo_enti = '{filtro_tipo}'" not in query:
            query += f" AND enti_tipo_enti = '{filtro_tipo}'"

        return query
    
    def _gerar_tool(self):
        @tool
        def consulta_mcp(query: str) -> str:
            """
            Executa consultas reais no banco via linguagem natural com MCP tools e suporte a gráficos.
            Recebe pergunta, gera SQL via LLM, executa, pode gerar gráficos e usa MCP tools para melhorar a resposta.
            Retorna resposta formatada em texto natural para o usuário.
            """
            # Pré-processa query pra injetar filtro enti_tipo_enti se precisar
            query = self.pre_process_query(query)


            
            # Substitui aliases tipo "total faturado" → "pedi_tota"
            for k, v in self.factory.alias_filtros.items():
                query = query.replace(k, v)

            # Adiciona relacionamentos
            for rel in self.relacionamentos:
                query = query.replace(rel[0], rel[1])

            # Adiciona filtros naturais
            for filtro in self.filtros:
                query = query.replace(filtro[0], filtro[1])
            
            contexto = f"""
            Você é um agente SQL para PostgreSQL. Gere uma consulta SQL válida com base nos dados abaixo:

            - Use tabelas completas com schema 'public'.
            - Sempre filtre pela empresa usando o campo apropriado que termina com '_empr'.
            - Todos os campos *_empr são do tipo integer e devem ser comparados com um valor numérico (ex: pedi_empr = 1).
            - Nunca compare *_empr com string. Nunca use aspas em valores de empresa.
            - Nunca use variáveis tipo :pedi_empr, use somente o campo diretamente.
            - Nunca use placeholders como :pedi_empr. Sempre escreva diretamente 'pedi_empr' ou similar no WHERE.
            - Nunca use <SUA_EMPRESA> no WHERE. Use o campo 'pedi_empr' diretamente.

            RELACIONAMENTOS CORRETOS (MUITO IMPORTANTE):
            - Para relacionar pedidos com fornecedores, use: PedidosVenda.pedi_forn = Entidades.enti_clie (não pedi_clie!)
            - Para relacionar pedidos com vendedores, use: PedidosVenda.pedi_vend = Entidades.enti_clie AND enti_tipo_enti = 'VE'
            - O nome do vendedor/cliente está em Entidades.enti_nome
            - Relacionamentos principais:
            - Itenspedidovenda.iped_prod = Produtos.prod_codi
            - Itenspedidovenda.iped_pedi = PedidosVenda.pedi_nume
            - PedidosVenda.pedi_forn = Entidades.enti_clie (para clientes)
            - PedidosVenda.pedi_vend = Entidades.enti_clie (para vendedores)
            - Produtos.prod_forn = Entidades.enti_clie
            - Total de Pedidos = pedi_nume
            - Total de Itens = iped_item
            - Total Faturado = pedi_tota

            FILTROS DE DATA:
            - Para mês: EXTRACT(MONTH FROM pedi_data) = 7
            - Para ano: EXTRACT(YEAR FROM pedi_data) = 2024
            - Para mês por nome: TO_CHAR(pedi_data, 'Month') ILIKE '%julho%'

            CAMPOS COMUNS:
            - total faturado → pedi_tota
            - quantidade vendida → iped_quan
            - cliente → enti_nome (via pedi_forn)
            - vendedor → enti_nome (via pedi_vend)
            - data → pedi_data

            Modelos disponíveis: {', '.join(m.__name__ for m in self.factory.models)}

            Pergunta do usuário: {query}

            Gere um SQL correto, com os joins necessários, usando os relacionamentos e filtros acima, para responder a pergunta. 
            Retorne somente o código SQL, nada mais. Dê um alias claro e descritivo para o resultado, como "total_faturado", "quantidade_total" ou similar. Nunca deixe o resultado sem alias.

            """ 

            sql = self.llm.invoke(contexto).content.strip().strip("```sql").strip("```")
             

            # Detectar nome correto do campo de empresa
            empresa_field = self.detectar_campo_empresa()

            # Injetar filtro de empresa
            sql = forcar_filtro_empresa(sql, valor='1', coluna=empresa_field)

            # Corrigir aliases no GROUP BY
            sql = corrigir_group_by_aliases(sql)
                

            with connection.cursor() as cursor:
                cursor.execute(sql)
                colunas = [col[0] for col in cursor.description]
                resultados = [dict(zip(colunas, row)) for row in cursor.fetchall()]

            # Agora gera resposta natural para o usuário com LLM
            resposta_prompt = f"""
            Você é um especialista em análise de dados e precisa responder de forma clara e objetiva com base nos dados abaixo.

            - Pergunta original do usuário: "{query}"
            - Consulta SQL executada: ```sql\n{sql}\n```
            - Resultado obtido da consulta: {resultados}

            Responda SOMENTE com base nos dados retornados. **Não invente nada**.

            **Regras:**
            - Se houver total, diga: "O total foi de R$ X mil" ou "X unidades", conforme o campo.
            - Se for uma contagem, diga: "Foram encontrados X registros."
            - Se for média, diga: "A média foi de X por Y."
            - Nunca diga "parece que..." ou "há indícios...".
            - Se não houver resultados, diga: "Nenhum dado foi encontrado para essa consulta."

           

            Responda agora:
            """

            resposta_texto = self.llm.invoke(resposta_prompt).content.strip()
            print(resposta_texto)
            print(resposta_texto, f"\n\n🧠 _Consulta SQL gerada automaticamente:_\n```sql\n{sql}\n```")
            print('banco de daods passado:',connection.settings_dict['NAME'])
            return resposta_texto

        return consulta_mcp

    def get_tool(self):
        return self.tool

    def invoke(self, query: str) -> str:
            """Método invoke para compatibilidade com LangChain"""
            return self.tool.invoke({"query": query})

    def __call__(self, query: str) -> str:
        return self.tool.invoke({"query": query})


