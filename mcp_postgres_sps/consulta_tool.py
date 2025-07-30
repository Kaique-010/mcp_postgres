from langchain.tools import tool
from django.db import connection, models
from .filtros_naturais import FILTROS_NATURAIS
from django.db.models import Sum, Count, F
from .relacionamento_registry import RELACIONAMENTOS_MCP

class ConsultaTool:
    def __init__(self, factory, llm):
        self.factory = factory
        self.filtros = FILTROS_NATURAIS
        self.relacionamentos = RELACIONAMENTOS_MCP
        self.llm = llm
        self.tool = self._gerar_tool()

    def _gerar_tool(self):
        @tool
        def consulta_mcp(query: str) -> str:
            """
            Executa consultas reais no banco via linguagem natural.
            Recebe pergunta, gera SQL via LLM e executa.
            Retorna resposta formatada em texto natural para o usuário.
            """
            # Substitui aliases tipo "total faturado" → "pedi_tota"
            for k, v in self.factory.alias_filtros.items():
                query = query.replace(k, v)

            # Prompt pro LLM gerar SQL
            contexto = f"""
Você é um agente SQL para PostgreSQL. Gere uma consulta SQL válida com base nos dados abaixo:

- Use tabelas completas com schema 'public'.
- Sempre filtre pela empresa usando o campo 'pedi_empr' ou equivalente.
- Modelos disponíveis: {', '.join(m.__name__ for m in self.factory.models)}.
- Relacionamentos (JOINs) entre tabelas:
  Itenspedidovenda.iped_prod = Produtos.prod_codi
  Itenspedidovenda.iped_pedi = PedidosVenda.pedi_nume
  PedidosVenda.pedi_forn = Entidades.enti_clie
  Produtos.prod_forn = Entidades.enti_clie
  Itenspedidovenda.iped_forn = Entidades.enti_clie
  Produtos.prod_pedi = PedidosVenda.pedi_nume

- Filtros naturais para facilitar a consulta:
  total faturado → pedi_tota
  quantidade vendida → iped_quan
  cliente → enti_nome
  produto → prod_nome
  vendedor → pedi_vend
  data → pedi_data

Pergunta do usuário: {query}

Gere um SQL correto, com os joins necessários, usando os relacionamentos e filtros acima, para responder a pergunta. 
Retorne somente o código SQL, nada mais.
"""

            sql = self.llm.invoke(contexto).content.strip().strip("```sql").strip("```")

            with connection.cursor() as cursor:
                cursor.execute(sql)
                colunas = [col[0] for col in cursor.description]
                resultados = [dict(zip(colunas, row)) for row in cursor.fetchall()]

            # Agora gera resposta natural para o usuário com LLM
            resposta_prompt = f"""
Considere a pergunta: "{query}"
E o resultado SQL: {sql}
Resultados: {resultados}

Responda de forma clara e resumida, em linguagem natural, para um usuário final.
"""
            resposta = self.llm.invoke(resposta_prompt).content.strip()

            return resposta

        return consulta_mcp

    def get_tool(self):
        return self.tool

    def __call__(self, query: str) -> str:
        return self.tool(query)
