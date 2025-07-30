import re

def forcar_filtro_empresa(sql: str, coluna: str = "pedi_empr", valor: str = None) -> str:
    """
    Injeta filtro da empresa manualmente no SQL.
    Exemplo: pedi_empr = '1234'
    """
    if not valor:
        raise ValueError("Valor da empresa não pode ser vazio.")

    clausula = f"{coluna} = '{valor}'"
    
    if "WHERE" in sql.upper():
        # Insere depois do WHERE e antes de outras condições
        return re.sub(r"(WHERE\s+)", r"\1" + clausula + " AND ", sql, flags=re.IGNORECASE)
    else:
        return sql.rstrip(" \n;") + f" WHERE {clausula}"

def corrigir_group_by_aliases(sql: str) -> str:
    """
    Corrige o GROUP BY para incluir aliases do SELECT.
    Garante que campos com 'AS nome' estejam no GROUP BY se houver agregações.
    """
    # Pega os aliases do SELECT
    aliases = re.findall(r"\bAS\s+(\w+)", sql, flags=re.IGNORECASE)
    if not aliases:
        return sql

    partes = re.split(r"\bGROUP BY\b", sql, flags=re.IGNORECASE)
    if len(partes) != 2:
        return sql  # Não tem GROUP BY, nada a corrigir

    grupo_atual = partes[1].strip(" ;\n")
    grupo_corrigido = grupo_atual

    for alias in aliases:
        if alias not in grupo_atual:
            grupo_corrigido += f", {alias}"

    return f"{partes[0]} GROUP BY {grupo_corrigido}"
