from langchain.tools import tool
from .relacionamento_registry import RELACIONAMENTOS_MCP
from .filtros_naturais import FILTROS_NATURAIS

class ModelToolFactory:
    def __init__(self, models, slug, relacionamentos, alias_filtros):
        self.models = models
        self.slug = slug
        self.relacionamentos = relacionamentos
        self.alias_filtros = alias_filtros

    def gerar_tool(self):
        @tool
        def consulta_mcp(query: str) -> str:
            # Aplicar filtros naturais
            for k, v in self.alias_filtros.items():
                query = query.replace(k, v)
            # Montar SQL dinâmico cruzando models com relacionamentos
            sql = self.gerar_sql(query)
            # Aqui chamaria o DB via slug + execução segura
            resultado = f"Executando SQL no slug {self.slug}: {sql}"
            return resultado

        return consulta_mcp

    def gerar_sql(self, query):
        # Exemplo simplificado só pra ilustrar
        # Implementar parser e join conforme relacionamentos
        tabelas = [m.__name__ for m in self.models]
        joins = []
        for (t1, t2), (c1, c2) in self.relacionamentos.items():
            joins.append(f"{t1} JOIN {t2} ON {t1}.{c1} = {t2}.{c2}")
        join_sql = " ".join(joins)
        sql = f"SELECT * FROM {join_sql} WHERE {query}"
        return sql
