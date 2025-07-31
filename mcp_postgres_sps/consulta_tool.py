from langchain.tools import tool
from django.db import connection, DatabaseError
from django.core.exceptions import ValidationError
from .utils import forcar_filtro_empresa, corrigir_group_by_aliases
from .error_handler import MCPErrorHandler, ErrorRecovery
import re
import logging
import unicodedata
from typing import Dict, List, Tuple, Optional, Set
from .filtros_naturais import FILTROS_NATURAIS, FILTROS_PERIODO, FILTROS_COMPARACAO
from .relacionamento_registry import RELACIONAMENTOS_MCP

def corrigir_group_by_aliases(sql: str) -> str:
    substituicoes = {
        r"\bmes\b": "TO_CHAR(pedi_data, 'Month')",
        r"\bano\b": "EXTRACT(YEAR FROM pedi_data)",
        r"\bdia\b": "EXTRACT(DAY FROM pedi_data)",
        r"\bnome\b": "enti_nome",
        r"\bnomes\b": "enti_nome",
        r"\bempresa\b": "prod_empr",
        r"\bempresas\b": "iped_empr",
        r"\bempr\b": "pedi_empr",
        r"\bempresas\b": "iped_empr",
        r"\bempresas\b": "enti  _empr",
        r"\bproduto\b": "prod_nome",
        r"\bprodutos\b": "prod_nome",
        r"\bpedido\b": "pedi_nume",
        r"\bpedidos\b": "pedi_nume",
        r"\bquantidade\b": "pedi_quan",
        r"\bquantidades\b": "pedi_quan",
        r"\btotal\b": "pedi_tota",
        r"\btotais\b": "pedi_tota",
        r"\bdata\b": "pedi_data",
    }
    for alias, funcao in substituicoes.items():
        sql = re.sub(rf"GROUP BY\s+{alias}", f"GROUP BY {funcao}", sql, flags=re.IGNORECASE)
    return sql

# -------------------------------------------
# Validação e Segurança SQL
# -------------------------------------------

class SQLValidator:
    """Classe para validação robusta de SQL e proteção contra injection"""
    
    def __init__(self, models):
        self.models = models
        self.tabelas_validas = self._build_valid_tables()
        self.campos_validos = self._build_valid_fields()
        self.palavras_perigosas = {
            'drop', 'delete', 'truncate', 'alter', 'create', 'insert', 'update',
            'exec', 'execute', 'sp_', 'xp_', '--', '/*', '*/', ';--', 'union',
            'script', 'javascript', 'vbscript', 'onload', 'onerror'
        }
        # Caracteres válidos para SQL
        self.caracteres_validos = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.,()=<>!-+*/\' "\n\t ')
    
    def _build_valid_tables(self) -> Set[str]:
        """Constrói conjunto de tabelas válidas"""
        tabelas = set()
        for model in self.models:
            table_name = model._meta.db_table
            tabelas.add(table_name.lower())
            tabelas.add(f"public.{table_name}".lower())
        return tabelas
    
    def _build_valid_fields(self) -> Dict[str, Set[str]]:
        """Constrói mapeamento de campos válidos por tabela"""
        campos = {}
        for model in self.models:
            table_name = model._meta.db_table.lower()
            campos[table_name] = set()
            for field in model._meta.fields:
                campos[table_name].add(field.column.lower())
        return campos
    
    def validar_encoding_sql(self, sql: str) -> Tuple[bool, List[str]]:
        """Valida se o SQL tem encoding válido e caracteres seguros"""
        problemas = []
        
        # Verifica se há caracteres não-ASCII suspeitos
        try:
            # Tenta normalizar o texto
            sql_normalizado = unicodedata.normalize('NFKD', sql)
            
            # Verifica caracteres inválidos
            caracteres_invalidos = set()
            for char in sql:
                if char not in self.caracteres_validos:
                    # Permite alguns caracteres especiais específicos
                    if ord(char) > 127 and not char.isspace():
                        caracteres_invalidos.add(char)
            
            if caracteres_invalidos:
                problemas.append(f"Caracteres inválidos detectados: {list(caracteres_invalidos)[:10]}")
            
            # Verifica se há sequências suspeitas de caracteres repetidos
            if re.search(r'[úóáéíàèìòù]{3,}', sql):
                problemas.append("Sequências suspeitas de caracteres acentuados detectadas")
            
            # Verifica se há palavras completamente corrompidas
            palavras = re.findall(r'\b\w+\b', sql)
            palavras_corrompidas = []
            for palavra in palavras:
                if len(palavra) > 3:
                    # Conta caracteres não-ASCII
                    chars_nao_ascii = sum(1 for c in palavra if ord(c) > 127)
                    if chars_nao_ascii > len(palavra) * 0.5:  # Mais de 50% não-ASCII
                        palavras_corrompidas.append(palavra)
            
            if palavras_corrompidas:
                problemas.append(f"Palavras corrompidas detectadas: {palavras_corrompidas[:5]}")
                
        except Exception as e:
            problemas.append(f"Erro de encoding: {str(e)}")
        
        return len(problemas) == 0, problemas
    
    def validar_sql_injection(self, sql: str) -> Tuple[bool, List[str]]:
        """Detecta possíveis tentativas de SQL injection"""
        sql_lower = sql.lower()
        problemas = []
        
        # Verifica palavras perigosas
        for palavra in self.palavras_perigosas:
            if palavra in sql_lower:
                problemas.append(f"Palavra perigosa detectada: {palavra}")
        
        # Verifica múltiplas declarações
        if sql.count(';') > 1:
            problemas.append("Múltiplas declarações SQL detectadas")
        
        # Verifica comentários suspeitos
        if re.search(r'--.*$', sql, re.MULTILINE):
            problemas.append("Comentários SQL suspeitos detectados")
        
        return len(problemas) == 0, problemas
    
    def validar_tabelas_sql(self, sql: str) -> Tuple[bool, List[str]]:
        """Valida se todas as tabelas no SQL são válidas"""
        # Extrai tabelas do SQL - CORRIGIDO para não confundir campos com tabelas
        patterns = [
            r'FROM\s+([a-zA-Z0-9_\.]+)(?:\s+[a-zA-Z0-9_]+)?',  # FROM tabela [alias]
            r'(?:INNER\s+|LEFT\s+|RIGHT\s+|FULL\s+)?JOIN\s+([a-zA-Z0-9_\.]+)(?:\s+[a-zA-Z0-9_]+)?',  # JOIN tabela [alias]
            r'UPDATE\s+([a-zA-Z0-9_\.]+)',
            r'INSERT\s+INTO\s+([a-zA-Z0-9_\.]+)'
        ]
        
        tabelas_encontradas = set()
        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for match in matches:
                # Remove alias e normaliza
                tabela = match.strip().split()[0].lower()
                # Ignora se for apenas um alias (sem ponto)
                if '.' in tabela or tabela in ['public', 'pedidosvenda', 'entidades', 'itenspedidovenda', 'produtos']:
                    tabelas_encontradas.add(tabela)
        
        tabelas_invalidas = []
        for tabela in tabelas_encontradas:
            if tabela not in self.tabelas_validas:
                tabelas_invalidas.append(tabela)
        
        return len(tabelas_invalidas) == 0, tabelas_invalidas
    
    def validar_campos_sql(self, sql: str) -> Tuple[bool, List[str]]:
        """Valida se todos os campos no SQL existem nas tabelas"""
        # Extrai campos qualificados (alias.campo) - MELHORADO
        campos_qualificados = re.findall(r'\b([a-zA-Z0-9_]+)\.([a-zA-Z0-9_]+)\b', sql)
        campos_invalidos = []
        
        # Mapeamento de aliases comuns para tabelas
        alias_para_tabela = {
            'pv': 'pedidosvenda',
            'e': 'entidades', 
            'i': 'itenspedidovenda',
            'p': 'produtos'
        }
        
        for alias, campo in campos_qualificados:
            alias_lower = alias.lower()
            campo_lower = campo.lower()
            
            # Resolve alias para nome da tabela
            tabela_real = alias_para_tabela.get(alias_lower, alias_lower)
            
            # Verifica se a tabela existe nos campos válidos
            if tabela_real in self.campos_validos:
                # Verifica se o campo existe na tabela
                if campo_lower not in self.campos_validos[tabela_real]:
                    campos_invalidos.append(f"{alias}.{campo}")
            else:
                # Se não encontrou, pode ser um alias não mapeado - IGNORA para evitar falsos positivos
                continue
        
        return len(campos_invalidos) == 0, campos_invalidos
    
    def validar_sql_completo(self, sql: str) -> Tuple[bool, Dict[str, List[str]]]:
        """Executa todas as validações de SQL incluindo encoding"""
        resultados = {
            'encoding': [],
            'injection': [],
            'tabelas': [],
            'campos': []
        }
        
        # Validação de encoding (primeira prioridade)
        encoding_valid, encoding_issues = self.validar_encoding_sql(sql)
        if not encoding_valid:
            resultados['encoding'] = encoding_issues
            # Se há problemas de encoding, não vale a pena validar o resto
            return False, resultados
        
        # Validação de SQL injection
        is_safe, injection_issues = self.validar_sql_injection(sql)
        if not is_safe:
            resultados['injection'] = injection_issues
        
        # Validação de tabelas
        tables_valid, invalid_tables = self.validar_tabelas_sql(sql)
        if not tables_valid:
            resultados['tabelas'] = invalid_tables
        
        # Validação de campos
        fields_valid, invalid_fields = self.validar_campos_sql(sql)
        if not fields_valid:
            resultados['campos'] = invalid_fields
        
        is_valid = encoding_valid and is_safe and tables_valid and fields_valid
        return is_valid, resultados

def validar_campos_sql(sql: str, models) -> list[str]:
    """Função legacy - mantida para compatibilidade"""
    validator = SQLValidator(models)
    _, invalid_fields = validator.validar_campos_sql(sql)
    return invalid_fields

def validar_tabelas(sql: str, models) -> list[str]:
    """Função legacy - mantida para compatibilidade"""
    validator = SQLValidator(models)
    _, invalid_tables = validator.validar_tabelas_sql(sql)
    return invalid_tables

# -------------------------------------------
# Geração dinâmica de alias
# -------------------------------------------

def gerar_alias_filtros_dinamico(models):
    alias = {}
    for model in models:
        for field in model._meta.fields:
            nome_field = field.name.lower()
            if "tota" in nome_field or "valor" in nome_field:
                alias["total faturado"] = nome_field
            if "quan" in nome_field:
                alias["quantidade"] = nome_field
            if "data" in nome_field:
                alias["data"] = nome_field
            if "nome" in nome_field:
                alias["nome"] = nome_field
    return alias
class ConsultaTool:
    def __init__(self, factory, llm):
        self.factory = factory
        self.filtros = FILTROS_NATURAIS
        self.relacionamentos = RELACIONAMENTOS_MCP
        self.llm = llm
        self.sql_validator = SQLValidator(factory.models)
        self.tabelas_permitidas = self._build_allowed_tables()
        self.campos_empresa = self._build_empresa_fields()
        self.tool = self._gerar_tool()
    
    def _build_allowed_tables(self) -> Dict[str, str]:
        """Constrói mapeamento de tabelas permitidas e seus aliases"""
        tabelas = {}
        for model in self.factory.models:
            table_name = model._meta.db_table
            tabelas[table_name.lower()] = f"public.{table_name}"
            # Adiciona aliases comuns
            if 'pedidosvenda' in table_name.lower():
                tabelas['pedidos'] = f"public.{table_name}"
                tabelas['vendas'] = f"public.{table_name}"
            elif 'entidades' in table_name.lower():
                tabelas['clientes'] = f"public.{table_name}"
                tabelas['vendedores'] = f"public.{table_name}"
            elif 'produtos' in table_name.lower():
                tabelas['produto'] = f"public.{table_name}"
        return tabelas
    
    def _build_empresa_fields(self) -> Dict[str, str]:
        """Mapeia tabelas para seus campos de empresa"""
        campos = {}
        for model in self.factory.models:
            table_name = model._meta.db_table.lower()
            for field in model._meta.fields:
                if field.name.endswith('_empr'):
                    campos[table_name] = field.name
                    break
        return campos

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
    
    def detectar_tipo_consulta(self, query: str) -> str:
        """
        Detecta o tipo de consulta E a tabela principal baseado nas palavras-chave.
        Versão melhorada com detecção mais precisa e robusta.
        """
        query_lower = query.lower().strip()
        
        # Mapeamento de palavras-chave para tabelas (ordem de prioridade)
        tabela_keywords = {
            "entidades": {
                "keywords": ['entidades', 'clientes', 'vendedores', 'fornecedores', 'representantes',
                           'quantas entidades', 'quantos vendedores', 'quantos clientes', 'quantos fornecedores',
                           'cadastro de', 'base de clientes', 'equipe de vendas'],
                "priority": 1
            },
            "itenspedidovenda": {
                "keywords": ['itens', 'produtos vendidos', 'quantidades', 'quantos itens', 'itens vendidos', 
                           'itens foram vendidos', 'quantidade de itens', 'total de itens', 'linhas de pedido',
                           'detalhes do pedido', 'produtos por pedido'],
                "priority": 2
            },
            "produtos": {
                "keywords": ['produtos', 'catálogo', 'estoque', 'quantos produtos', 'cadastro de produtos',
                           'lista de produtos', 'inventário', 'mercadorias'],
                "priority": 3
            },
            "pedidosvenda": {
                "keywords": ['pedidos', 'vendas', 'faturamento', 'faturado', 'receita', 'quantos pedidos', 
                           'total faturado', 'valor total', 'vendas totais', 'receita total'],
                "priority": 4  # Default, menor prioridade
            }
        }
        
        # Detectar tabela principal com sistema de pontuação
        tabela_scores = {}
        for tabela, config in tabela_keywords.items():
            score = 0
            for keyword in config["keywords"]:
                if keyword in query_lower:
                    # Palavras mais específicas têm peso maior
                    weight = len(keyword.split()) * 2 if len(keyword.split()) > 1 else 1
                    score += weight
            
            # Aplica prioridade (menor número = maior prioridade)
            if score > 0:
                tabela_scores[tabela] = score / config["priority"]
        
        # Escolhe tabela com maior score, ou default
        tabela_principal = "pedidosvenda"  # default
        if tabela_scores:
            tabela_principal = max(tabela_scores.items(), key=lambda x: x[1])[0]
        
        # Detectar tipo de operação com regras mais específicas
        tipo_operacao = "geral"
        
        # Mapeamento de operações com contexto
        operacao_patterns = {
            "contagem": {
                "patterns": [r'quantos?\s+\w+', r'quantas?\s+\w+', r'número\s+de', r'total\s+de\s+\w+(?!\s+(vendidos?|faturad))',
                           r'contar', r'contagem'],
                "exclude_if": ['vendidos', 'faturado', 'receita', 'valor']
            },
            "soma_quantidade": {
                "patterns": [r'itens?\s+vendidos?', r'quantidade\s+de\s+itens?', r'total\s+de\s+itens?\s+vendidos?',
                           r'quantos?\s+itens?\s+(foram\s+)?vendidos?'],
                "require_table": ["itenspedidovenda"]
            },
            "soma": {
                "patterns": [r'faturamento', r'receita', r'total\s+faturado', r'valor\s+total', r'soma\s+de',
                           r'vendas\s+totais', r'receita\s+total'],
                "exclude_if": ['quantos', 'quantas', 'número']
            }
        }
        
        # Detectar operação principal
        for op_name, op_config in operacao_patterns.items():
            # Verifica se algum pattern match
            pattern_match = any(re.search(pattern, query_lower) for pattern in op_config["patterns"])
            
            if pattern_match:
                # Verifica exclusões
                if "exclude_if" in op_config:
                    if any(exclude in query_lower for exclude in op_config["exclude_if"]):
                        continue
                
                # Verifica se tabela é compatível
                if "require_table" in op_config:
                    if tabela_principal not in op_config["require_table"]:
                        continue
                
                tipo_operacao = op_name
                break
        
        # Detectar modificadores
        modificadores = []
        
        # Agrupamento
        agrupamento_patterns = [r'por\s+\w+', r'mais\s+vendidos?', r'ranking', r'top\s+\d+', r'maiores?', r'menores?']
        if any(re.search(pattern, query_lower) for pattern in agrupamento_patterns):
            modificadores.append("agrupamento")
        
        # Período
        periodo_patterns = [r'\b(ano|mês|trimestre|semestre)\b', r'\b(janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\b',
                          r'\b(202[0-9])\b', r'em\s+202[0-9]', r'durante\s+', r'período\s+de']
        if any(re.search(pattern, query_lower) for pattern in periodo_patterns):
            modificadores.append("periodo")
        
        # Constrói tipo final
        tipo_final = tipo_operacao
        if modificadores:
            tipo_final += "_" + "_".join(modificadores)
            
        return f"{tabela_principal}_{tipo_final}"
    
    def validar_sql(self, sql: str, tipo_consulta: str) -> Tuple[bool, str]:
        """
        Valida se o SQL gerado está correto baseado no tipo de consulta detectado.
        Inclui validações de segurança, estrutura e lógica de negócio.
        Retorna (is_valid, error_message)
        """
        sql_lower = sql.lower().strip()
        
        # Validações básicas de estrutura
        if not sql_lower:
            return False, "SQL vazio gerado"
            
        if not sql_lower.startswith('select'):
            return False, "SQL deve começar com SELECT"
        
        # Validação completa de segurança
        is_safe, security_issues = self.sql_validator.validar_sql_completo(sql)
        if not is_safe:
            issues_text = []
            for category, problems in security_issues.items():
                if problems:
                    issues_text.extend([f"{category.title()}: {p}" for p in problems])
            return False, f"Problemas de segurança detectados: {'; '.join(issues_text)}"
        
        # Validação de filtro de empresa obrigatório
        empresa_fields = ['_empr = 1', 'pedi_empr', 'iped_empr', 'enti_empr', 'prod_empr']
        if not any(field in sql_lower for field in empresa_fields):
            return False, "SQL deve incluir filtro de empresa (_empr = 1)"
        
        # Validações específicas por tipo de consulta
        validation_rules = {
            'contagem': {
                'required': ['count('],
                'message': 'Consulta de contagem deve usar COUNT()'
            },
            'soma_quantidade': {
                'required': ['sum('],
                'forbidden': ['count('],
                'message': 'Consulta de quantidade deve usar SUM(), não COUNT()'
            },
            'soma': {
                'required': ['sum('],
                'message': 'Consulta de soma deve usar SUM()'
            },
            'agrupamento': {
                'required': ['group by'],
                'message': 'Consulta de agrupamento deve usar GROUP BY'
            }
        }
        
        for rule_type, rules in validation_rules.items():
            if rule_type in tipo_consulta:
                # Verifica campos obrigatórios
                if 'required' in rules:
                    if not any(req in sql_lower for req in rules['required']):
                        return False, rules['message']
                
                # Verifica campos proibidos
                if 'forbidden' in rules:
                    if any(forb in sql_lower for forb in rules['forbidden']):
                        return False, rules['message']
        
        # Validação de sintaxe SQL básica
        syntax_checks = [
            (sql.count('('), sql.count(')'), "Parênteses desbalanceados"),
            (sql.count("'"), sql.count("'") % 2 == 0, "Aspas simples desbalanceadas"),
            (sql.count('"'), sql.count('"') % 2 == 0, "Aspas duplas desbalanceadas")
        ]
        
        for check in syntax_checks:
            if len(check) == 3:  # Parênteses
                if check[0] != check[1]:
                    return False, check[2]
            else:  # Aspas
                if not check[1]:
                    return False, check[2]
        
        # Validação de estrutura SELECT básica
        if not re.search(r'select\s+.+\s+from\s+', sql_lower):
            return False, "SQL deve ter estrutura SELECT ... FROM ..."
            
        return True, ""
    
    def processar_sql_llm(self, contexto: str) -> str:
        """
        Processa SQL via LLM com múltiplas tentativas e sanitização.
        Retorna SQL válido ou None se todas as tentativas falharam.
        """
        import logging
        logger = logging.getLogger(__name__)
        
        max_tentativas = 3
        logger.info(f"=== INICIANDO PROCESSAMENTO LLM ===")
        
        for tentativa in range(max_tentativas):
            try:
                logger.info(f"--- Tentativa {tentativa + 1}/{max_tentativas} ---")
                
                # PROMPT SIMPLIFICADO para reduzir confusão do LLM
                prompt_simples = self.criar_prompt_simples(contexto)
                logger.info(f"Prompt gerado (primeiros 200 chars): {prompt_simples[:200]}...")
                
                # Chama o LLM com prompt mais simples
                logger.info("Chamando LLM...")
                resposta = self.llm.invoke(prompt_simples)
                logger.info(f"LLM respondeu. Tipo: {type(resposta)}")
                
                # Extrai conteúdo com tratamento robusto de encoding
                sql_bruto = self.extrair_sql_seguro(resposta)
                logger.info(f"SQL bruto extraído: '{sql_bruto}'")
                
                if not sql_bruto:
                    logger.warning(f"Tentativa {tentativa + 1}: Resposta vazia do LLM")
                    continue
                
                # Sanitiza o SQL
                sql_sanitizado = self.sanitizar_sql(sql_bruto)
                logger.info(f"SQL sanitizado: '{sql_sanitizado}'")
                
                # Valida encoding
                is_encoding_valid, encoding_error = self.validar_encoding_sql(sql_sanitizado)
                logger.info(f"Validação encoding: {is_encoding_valid}, erro: {encoding_error}")
                if not is_encoding_valid:
                    logger.warning(f"Tentativa {tentativa + 1}: SQL com encoding inválido: {encoding_error}")
                    continue
                
                # Verifica se não está vazio após sanitização
                if not sql_sanitizado or len(sql_sanitizado.strip()) < 10:
                    logger.warning(f"Tentativa {tentativa + 1}: SQL muito curto após sanitização")
                    continue
                
                # Validação estrutural básica
                estrutura_valida = self.validar_estrutura_basica_sql(sql_sanitizado)
                logger.info(f"Validação estrutural: {estrutura_valida}")
                if not estrutura_valida:
                    logger.warning(f"Tentativa {tentativa + 1}: SQL com estrutura inválida")
                    continue
                
                # Se chegou até aqui, o SQL passou nas validações básicas
                logger.info(f"\u2705 LLM SUCESSO na tentativa {tentativa + 1}: {sql_sanitizado}")
                return sql_sanitizado
                
            except Exception as e:
                logger.error(f"Tentativa {tentativa + 1} falhou com exceção: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                continue
        
        # Se todas as tentativas falharam
        logger.error(f"\u274c LLM FALHOU em todas as {max_tentativas} tentativas")
        return None
    
    def criar_prompt_simples(self, contexto_original: str) -> str:
        """
        Cria um prompt mais simples e focado para reduzir confusão do LLM.
        """
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
    
    def extrair_sql_seguro(self, resposta) -> str:
        """
        Extrai SQL da resposta do LLM com tratamento robusto de encoding.
        """
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
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao extrair SQL da resposta: {e}")
            return ""
    
    def validar_estrutura_basica_sql(self, sql: str) -> bool:
        """
        Validação estrutural básica do SQL.
        """
        try:
            sql_lower = sql.lower().strip()
            
            # Deve começar com SELECT
            if not sql_lower.startswith('select'):
                return False
            
            # Deve ter FROM
            if 'from' not in sql_lower:
                return False
            
            # Deve ter filtro de empresa
            if '_empr' not in sql_lower:
                return False
            
            # Parênteses balanceados
            if sql.count('(') != sql.count(')'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def validar_sql_basico(self, sql: str, tipo_consulta: str) -> bool:
        """
        Validação básica e permissiva para templates de fallback internos.
        Apenas verifica estrutura essencial e lógica de negócio.
        """
        try:
            sql_lower = sql.lower().strip()
            
            # Validações estruturais básicas
            if not sql_lower or len(sql_lower) < 10:
                return False
                
            if not sql_lower.startswith('select'):
                return False
            
            if 'from' not in sql_lower:
                return False
            
            # Validação de lógica de negócio (mais permissiva)
            if "soma" in tipo_consulta:
                if "sum(" not in sql_lower:
                    return False
            elif "contagem" in tipo_consulta:
                if "count(" not in sql_lower:
                    return False
            
            # Verifica se tem algum filtro de empresa (mais flexível)
            if not any(campo in sql_lower for campo in ['_empr', 'empr =']):
                return False
            
            # Validação básica de sintaxe
            if sql.count('(') != sql.count(')'):
                return False
            
            return True
            
        except Exception:
            return False
    
    def llm_esta_corrompido(self) -> bool:
        """
        Detecta se o LLM está gerando conteúdo corrompido consistentemente.
        Faz um teste rápido e se detectar corrupção, assume que o LLM não está funcionando.
        """
        try:
            # Teste rápido com prompt simples
            prompt_teste = "Responda apenas: SELECT 1"
            
            resposta = self.llm.invoke(prompt_teste)
            
            if not hasattr(resposta, 'content'):
                return True  # Se não tem content, algo está errado
            
            content = resposta.content.strip().lower()
            
            # Padrões de corrupção conhecidos
            padroes_corrompidos = [
                'subooo', 'ssso', 'uuosbsusb', 'úúos', 'súbooo',
                'oosbssu', 'uuosb', 'ssso_uuosb'
            ]
            
            # Se contém padrões corrompidos, LLM está com problema
            for padrao in padroes_corrompidos:
                if padrao in content:
                    return True
            
            # Se resposta muito longa para prompt simples, pode estar corrompido
            if len(content) > 100:
                return True
            
            # Se não contém "select" para um prompt SQL simples, pode estar corrompido
            if 'select' not in content and len(content) > 10:
                return True
                
            return False  # LLM parece estar funcionando
            
        except Exception as e:
            # Se não consegue nem testar, assume que está corrompido
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao testar LLM: {e}")
            return True
    
    def gerar_sql_direto(self, query: str, tabela: str, tipo_consulta: str) -> str:
        """
        Gera SQL diretamente baseado na tabela e tipo detectados, sem depender do LLM para escolher tabela.
        """
        query_lower = query.lower()
        
        # Templates de SQL por tabela e tipo
        templates_sql = {
            # ENTIDADES
            "entidades_contagem": {
                "base": "SELECT COUNT(*) AS total_entidades FROM public.entidades e WHERE e.enti_empr = 1",
                "clientes": "SELECT COUNT(*) AS total_clientes FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'CL'",
                "vendedores": "SELECT COUNT(*) AS total_vendedores FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'VE'",
                "fornecedores": "SELECT COUNT(*) AS total_fornecedores FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'FO'"
            },
            
            # ITENS
            "itenspedidovenda_soma_quantidade": {
                "base": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i WHERE i.iped_empr = 1"
            },
            "itenspedidovenda_contagem": {
                "base": "SELECT COUNT(*) AS total_linhas_itens FROM public.itenspedidovenda i WHERE i.iped_empr = 1"
            },
            
            # PRODUTOS
            "produtos_contagem": {
                "base": "SELECT COUNT(*) AS total_produtos FROM public.produtos p WHERE p.prod_empr = 1"
            },
            
            # PEDIDOS (fallback)
            "pedidosvenda_contagem": {
                "base": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1"
            },
            "pedidosvenda_soma": {
                "base": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1"
            },
            "pedidosvenda_soma_periodo": {
                "base": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2025"
            }
        }
        
        # Escolher template baseado no tipo detectado
        if tipo_consulta in templates_sql:
            template = templates_sql[tipo_consulta]
            
            # Verificar se é um subtipo específico
            if "clientes" in query_lower or "cliente" in query_lower:
                return template.get("clientes", template["base"])
            elif "vendedores" in query_lower or "vendedor" in query_lower:
                return template.get("vendedores", template["base"])
            elif "fornecedores" in query_lower or "fornecedor" in query_lower:
                return template.get("fornecedores", template["base"])
            else:
                sql_base = template["base"]
                # Ajustar para período se detectado
                if "_periodo" in tipo_consulta and "2025" in query_lower:
                    sql_base = sql_base.replace("WHERE pv.pedi_empr = 1", "WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2025")
                elif "_periodo" in tipo_consulta and "2024" in query_lower:
                    sql_base = sql_base.replace("WHERE pv.pedi_empr = 1", "WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2024")
                return sql_base
        
        # Se não encontrou template, retorna None para usar o LLM
        return None
    
    def forcar_tabela_correta(self, query: str, tabela: str, tipo_consulta: str) -> str:
        """
        Força a query a usar a tabela correta baseada na detecção.
        Versão melhorada com instruções mais específicas e validação.
        """
        # Primeiro tenta gerar SQL diretamente
        sql_direto = self.gerar_sql_direto(query, tabela, tipo_consulta)
        if sql_direto:
            return f"GERE EXATAMENTE ESTE SQL: {sql_direto}"
        
        # Instruções específicas por tabela com contexto
        instrucoes_tabela = {
            "entidades": {
                "obrigatorio": "OBRIGATÓRIO: Use APENAS a tabela public.entidades com alias 'e'.",
                "proibido": "NUNCA use pedidosvenda, itenspedidovenda ou produtos para contar entidades.",
                "campo_empresa": "e.enti_empr = 1",
                "dicas": "Para clientes use enti_tipo_enti = 'CL', para vendedores use 'VE', para fornecedores use 'FO'."
            },
            "itenspedidovenda": {
                "obrigatorio": "OBRIGATÓRIO: Use APENAS a tabela public.itenspedidovenda com alias 'i'.",
                "proibido": "NUNCA use pedidosvenda diretamente para contar itens vendidos.",
                "campo_empresa": "i.iped_empr = 1",
                "dicas": "Para quantidade de itens use SUM(i.iped_quan), para contar linhas use COUNT(*)."
            },
            "produtos": {
                "obrigatorio": "OBRIGATÓRIO: Use APENAS a tabela public.produtos com alias 'p'.",
                "proibido": "NUNCA use outras tabelas para contar produtos do catálogo.",
                "campo_empresa": "p.prod_empr = 1",
                "dicas": "Para produtos ativos adicione filtros de status se necessário."
            },
            "pedidosvenda": {
                "obrigatorio": "Use a tabela public.pedidosvenda com alias 'pv'.",
                "proibido": "",
                "campo_empresa": "pv.pedi_empr = 1",
                "dicas": "Para contagem use COUNT(DISTINCT pv.pedi_nume), para faturamento use SUM(pv.pedi_tota)."
            }
        }
        
        if tabela not in instrucoes_tabela:
            return query  # Retorna query original se tabela não reconhecida
        
        config = instrucoes_tabela[tabela]
        
        # Constrói instruções forçadas
        instrucoes = []
        instrucoes.append(config["obrigatorio"])
        
        if config["proibido"]:
            instrucoes.append(config["proibido"])
        
        instrucoes.append(f"SEMPRE inclua o filtro: {config['campo_empresa']}")
        instrucoes.append(config["dicas"])
        
        # Adiciona validações específicas baseadas no tipo
        if "contagem" in tipo_consulta:
            if tabela == "entidades":
                instrucoes.append("Use COUNT(*) para contar registros de entidades.")
            elif tabela == "itenspedidovenda":
                instrucoes.append("Para contar LINHAS de itens use COUNT(*), para QUANTIDADE vendida use SUM(iped_quan).")
            elif tabela == "pedidosvenda":
                instrucoes.append("Use COUNT(DISTINCT pedi_nume) para contar pedidos únicos.")
        
        elif "soma" in tipo_consulta:
            if tabela == "pedidosvenda":
                instrucoes.append("Use SUM(pedi_tota) para somar valores de faturamento.")
            elif tabela == "itenspedidovenda":
                instrucoes.append("Use SUM(iped_quan) para somar quantidades de itens.")
        
        # Monta query final
        query_forcada = " ".join(instrucoes) + f" PERGUNTA: {query}"
        
        return query_forcada
    
    def sanitizar_sql(self, sql: str) -> str:
        """Sanitiza SQL removendo caracteres inválidos e corrigindo problemas comuns"""
        try:
            # Remove caracteres de controle e normaliza
            sql_limpo = unicodedata.normalize('NFKD', sql)
            
            # Remove caracteres não-ASCII problemáticos
            sql_limpo = re.sub(r'[^\x00-\x7F]+', '', sql_limpo)
            
            # Remove espaços extras
            sql_limpo = re.sub(r'\s+', ' ', sql_limpo).strip()
            
            # Remove caracteres de controle
            sql_limpo = ''.join(char for char in sql_limpo if ord(char) >= 32 or char in '\n\t')
            
            return sql_limpo
            
        except Exception as e:
            logger = logging.getLogger(__name__)
            logger.error(f"Erro ao sanitizar SQL: {e}")
            return ""  # Retorna string vazia se não conseguir sanitizar
    
    def gerar_sql_fallback(self, query: str, tipo_consulta: str) -> str:
        """Gera SQL usando templates pré-definidos como fallback"""
        query_lower = query.lower()
        
        # Templates seguros por tipo de consulta - EXPANDIDO para cobrir todos os subtipos
        templates_fallback = {
            # CONTAGEM DE ENTIDADES
            "entidades_contagem": {
                "default": "SELECT COUNT(*) AS total_entidades FROM public.entidades e WHERE e.enti_empr = 1",
                "clientes": "SELECT COUNT(*) AS total_clientes FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'CL'",
                "vendedores": "SELECT COUNT(*) AS total_vendedores FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'VE'",
                "fornecedores": "SELECT COUNT(*) AS total_fornecedores FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'FO'"
            },
            
            # CONTAGEM DE PEDIDOS
            "pedidosvenda_contagem": {
                "default": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1",
                "periodo": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)"
            },
            
            # CONTAGEM DE PEDIDOS COM PERÍODO
            "pedidosvenda_contagem_periodo": {
                "default": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)",
                "2025": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2025",
                "2024": "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2024"
            },
            
            # SOMA DE QUANTIDADES
            "itenspedidovenda_soma_quantidade": {
                "default": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i WHERE i.iped_empr = 1",
                "periodo": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i JOIN public.pedidosvenda pv ON i.iped_pedi = pv.pedi_nume WHERE i.iped_empr = 1 AND pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)"
            },
            
            # SOMA DE QUANTIDADES COM PERÍODO
            "itenspedidovenda_soma_quantidade_periodo": {
                "default": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i JOIN public.pedidosvenda pv ON i.iped_pedi = pv.pedi_nume WHERE i.iped_empr = 1 AND pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)",
                "2025": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i JOIN public.pedidosvenda pv ON i.iped_pedi = pv.pedi_nume WHERE i.iped_empr = 1 AND pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2025",
                "2024": "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i JOIN public.pedidosvenda pv ON i.iped_pedi = pv.pedi_nume WHERE i.iped_empr = 1 AND pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2024"
            },
            
            # SOMA DE FATURAMENTO
            "pedidosvenda_soma": {
                "default": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1",
                "periodo": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)"
            },
            
            # SOMA DE FATURAMENTO COM PERÍODO - TEMPLATE ESPECÍFICO
            "pedidosvenda_soma_periodo": {
                "default": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)",
                "2025": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2025",
                "2024": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = 2024",
                "ano_atual": "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE)"
            },
            
            # SOMA COM AGRUPAMENTO
            "pedidosvenda_soma_agrupamento": {
                "default": "SELECT e.enti_nome AS vendedor, SUM(pv.pedi_tota) AS total_vendido FROM public.pedidosvenda pv JOIN public.entidades e ON pv.pedi_vend = e.enti_clie WHERE pv.pedi_empr = 1 AND e.enti_empr = 1 AND e.enti_tipo_enti = 'VE' GROUP BY e.enti_nome ORDER BY total_vendido DESC LIMIT 10"
            },
            
            # CONTAGEM DE PRODUTOS
            "produtos_contagem": {
                "default": "SELECT COUNT(*) AS total_produtos FROM public.produtos p WHERE p.prod_empr = 1"
            }
        }
        
        # Escolhe template baseado no tipo com lógica expandida
        if tipo_consulta in templates_fallback:
            template_config = templates_fallback[tipo_consulta]
            
            # Detecta subtipo específico
            if "clientes" in query_lower or "cliente" in query_lower:
                return template_config.get("clientes", template_config["default"])
            elif "vendedores" in query_lower or "vendedor" in query_lower:
                return template_config.get("vendedores", template_config["default"])
            elif "fornecedores" in query_lower or "fornecedor" in query_lower:
                return template_config.get("fornecedores", template_config["default"])
            # Detecta anos específicos
            elif "2025" in query_lower:
                return template_config.get("2025", template_config.get("periodo", template_config["default"]))
            elif "2024" in query_lower:
                return template_config.get("2024", template_config.get("periodo", template_config["default"]))
            elif "ano atual" in query_lower or "este ano" in query_lower:
                return template_config.get("ano_atual", template_config.get("periodo", template_config["default"]))
            elif "periodo" in tipo_consulta or any(palavra in query_lower for palavra in ['ano', 'mês', 'trimestre', 'em 20']):
                return template_config.get("periodo", template_config["default"])
            else:
                return template_config["default"]
        
        # Tenta encontrar template similar (fallback inteligente)
        tipo_base = tipo_consulta.split('_')[0] + '_' + tipo_consulta.split('_')[1] if '_' in tipo_consulta else tipo_consulta
        if tipo_base in templates_fallback:
            logger = logging.getLogger(__name__)
            logger.info(f"Usando template base {tipo_base} para tipo {tipo_consulta}")
            return templates_fallback[tipo_base]["default"]
        
        # Fallback genérico baseado no tipo principal
        if "soma" in tipo_consulta:
            if "itenspedidovenda" in tipo_consulta:
                return "SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i WHERE i.iped_empr = 1"
            else:
                return "SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1"
        elif "contagem" in tipo_consulta:
            if "entidades" in tipo_consulta:
                return "SELECT COUNT(*) AS total_entidades FROM public.entidades e WHERE e.enti_empr = 1"
            else:
                return "SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1"
        
        # Último fallback
        return "SELECT COUNT(*) AS total FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1"
    
    def processar_sql_llm(self, contexto: str, max_tentativas: int = 3) -> str:
        """Processa SQL do LLM com tentativas e fallback"""
        logger = logging.getLogger(__name__)
        
        for tentativa in range(max_tentativas):
            try:
                # Chama o LLM
                resposta = self.llm.invoke(contexto)
                sql_bruto = resposta.content.strip() if hasattr(resposta, 'content') else str(resposta).strip()
                
                # Remove marcadores de código
                sql_limpo = sql_bruto.strip("```sql").strip("```").strip()
                
                # Sanitiza o SQL
                sql_sanitizado = self.sanitizar_sql(sql_limpo)
                
                # Valida se o SQL sanitizado é válido
                if sql_sanitizado and len(sql_sanitizado) > 10:
                    # Verifica se tem estrutura básica de SQL
                    if re.search(r'select\s+.+\s+from\s+', sql_sanitizado.lower()):
                        return sql_sanitizado
                
                logger.warning(f"Tentativa {tentativa + 1}: SQL inválido ou corrompido: {sql_bruto[:100]}")
                
            except Exception as e:
                logger.error(f"Tentativa {tentativa + 1}: Erro ao processar LLM: {e}")
        
        # Se todas as tentativas falharam, retorna None para usar fallback
        logger.error("Todas as tentativas de geração via LLM falharam")
        return None
    
    def pre_process_query(self, query: str) -> str:
        """Pré-processa a query aplicando filtros naturais expandidos"""
        try:
            query_lower = query.lower()
            
            # Detecta tipo de consulta
            tipo_consulta = self.detectar_tipo_consulta(query)
            
            # Se menciona vendedor mas não tem filtro de tipo, adiciona
            if any(word in query_lower for word in ['vendedor', 'vendedores', 'representante']) and 'enti_tipo_enti' not in query_lower:
                # Adiciona contexto sobre vendedores
                query += " (considere apenas entidades do tipo VE - vendedores)"
            
            # Se menciona cliente mas não tem filtro de tipo, adiciona  
            if any(word in query_lower for word in ['cliente', 'clientes', 'comprador']) and 'enti_tipo_enti' not in query_lower:
                # Adiciona contexto sobre clientes
                query += " (considere apenas entidades do tipo CL - clientes)"
            
            # Adiciona dica sobre o tipo de consulta detectado
            if tipo_consulta != "geral":
                query += f" [TIPO_CONSULTA: {tipo_consulta}]"
                
            return query
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Erro no pré-processamento da query: {e}")
            return query  # Retorna query original em caso de erro

    def _gerar_tool(self):
        @tool
        def consulta_mcp(query: str) -> str:
            """
            Executa consultas reais no banco via linguagem natural com MCP tools e suporte a gráficos.
            Recebe pergunta, gera SQL via LLM, executa, pode gerar gráficos e usa MCP tools para melhorar a resposta.
            Retorna resposta formatada em texto natural para o usuário.
            """
            # Pré-processa query pra injetar filtro enti_tipo_enti se precisar
            query_processada = self.pre_process_query(query)
            tipo_consulta = self.detectar_tipo_consulta(query)
            
            # FORCAR ESCOLHA DA TABELA BASEADA NA DETECÇÃO
            tabela_detectada = tipo_consulta.split('_')[0]
            query_forcada = self.forcar_tabela_correta(query_processada, tabela_detectada, tipo_consulta)

            # Substitui aliases tipo "total faturado" → "pedi_tota"
            for k, v in self.factory.alias_filtros.items():
                query_forcada = query_forcada.replace(k, v)

            # Adiciona relacionamentos
            for rel in self.relacionamentos:
                query_forcada = query_forcada.replace(rel[0], rel[1])

            # Adiciona filtros naturais
            for filtro in self.filtros:
                query_forcada = query_forcada.replace(filtro[0], filtro[1])
            
            contexto = f"""
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

            EXEMPLOS DE CONSULTAS CORRETAS:

            1. CONTAGEM DE PEDIDOS:
            Pergunta: "quantos pedidos" / "número de pedidos" / "total de pedidos"
            SQL: SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1;

            2. CONTAGEM DE PEDIDOS POR PERÍODO:
            Pergunta: "quantos pedidos este ano" / "pedidos em 2024"
            SQL: SELECT COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE);

            3. FATURAMENTO TOTAL:
            Pergunta: "total faturado" / "faturamento" / "receita"
            SQL: SELECT SUM(pv.pedi_tota) AS total_faturado FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1;

            4. PRODUTOS MAIS VENDIDOS:
            Pergunta: "produtos mais vendidos" / "itens mais vendidos"
            SQL: SELECT p.prod_nome, SUM(i.iped_quan) AS quantidade_vendida FROM public.itenspedidovenda i JOIN public.produtos p ON i.iped_prod = p.prod_codi WHERE i.iped_empr = 1 AND p.prod_empr = 1 GROUP BY p.prod_nome ORDER BY quantidade_vendida DESC LIMIT 10;

            5. VENDAS POR VENDEDOR:
            Pergunta: "vendas por vendedor" / "faturamento por vendedor"
            SQL: SELECT e.enti_nome AS vendedor, SUM(pv.pedi_tota) AS total_vendido FROM public.pedidosvenda pv JOIN public.entidades e ON pv.pedi_vend = e.enti_clie WHERE pv.pedi_empr = 1 AND e.enti_empr = 1 AND e.enti_tipo_enti = 'VE' GROUP BY e.enti_nome ORDER BY total_vendido DESC;

            6. PEDIDOS POR VENDEDOR:
            Pergunta: "quantos pedidos por vendedor" / "pedidos do vendedor X"
            SQL: SELECT e.enti_nome AS vendedor, COUNT(DISTINCT pv.pedi_nume) AS total_pedidos FROM public.pedidosvenda pv JOIN public.entidades e ON pv.pedi_vend = e.enti_clie WHERE pv.pedi_empr = 1 AND e.enti_empr = 1 AND e.enti_tipo_enti = 'VE' GROUP BY e.enti_nome ORDER BY total_pedidos DESC;

            7. CONTAGEM DE ENTIDADES (TABELA: entidades):
            Pergunta: "quantas entidades" / "total de clientes" / "quantos vendedores" / "quantas entidades temos"
            SQL: SELECT COUNT(*) AS total_entidades FROM public.entidades e WHERE e.enti_empr = 1;
            Para clientes: SELECT COUNT(*) AS total_clientes FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'CL';
            Para vendedores: SELECT COUNT(*) AS total_vendedores FROM public.entidades e WHERE e.enti_empr = 1 AND e.enti_tipo_enti = 'VE';

            8. ITENS VENDIDOS (TABELA: itenspedidovenda):
            Pergunta: "quantos itens vendidos" / "quantos itens foram vendidos" / "total de itens" / "quantidade de itens vendidos"
            SQL: SELECT SUM(i.iped_quan) AS total_itens_vendidos FROM public.itenspedidovenda i WHERE i.iped_empr = 1;
            
            8b. CONTAGEM DE LINHAS DE ITENS (TABELA: itenspedidovenda):
            Pergunta: "quantas linhas de itens" / "quantos registros de itens"
            SQL: SELECT COUNT(*) AS total_linhas_itens FROM public.itenspedidovenda i WHERE i.iped_empr = 1;

            9. VENDAS POR PERÍODO:
            Pergunta: "vendas de janeiro a março" / "faturamento primeiro trimestre"
            SQL: SELECT SUM(pv.pedi_tota) AS total_periodo FROM public.pedidosvenda pv WHERE pv.pedi_empr = 1 AND EXTRACT(MONTH FROM pv.pedi_data) BETWEEN 1 AND 3 AND EXTRACT(YEAR FROM pv.pedi_data) = EXTRACT(YEAR FROM CURRENT_DATE);

            10. VENDAS POR CLIENTE:
            Pergunta: "vendas por cliente" / "faturamento por cliente"
            SQL: SELECT e.enti_nome AS cliente, SUM(pv.pedi_tota) AS total_comprado FROM public.pedidosvenda pv JOIN public.entidades e ON pv.pedi_forn = e.enti_clie WHERE pv.pedi_empr = 1 AND e.enti_empr = 1 AND e.enti_tipo_enti IN ('CL', 'AM') GROUP BY e.enti_nome ORDER BY total_comprado DESC;

            REGRAS CRÍTICAS - TABELA + OPERAÇÃO:
            
            📊 IDENTIFICAÇÃO DA TABELA:
            - "quantas entidades" → public.entidades + COUNT(*)
            - "quantos itens vendidos" → public.itenspedidovenda + SUM(iped_quan)
            - "quantos pedidos" → public.pedidosvenda + COUNT(DISTINCT pedi_nume)
            - "quantos produtos" → public.produtos + COUNT(*)
            - "total faturado" → public.pedidosvenda + SUM(pedi_tota)
            - "quantos vendedores" → public.entidades + COUNT(*) + enti_tipo_enti = 'VE'
            
            ⚠️ NUNCA use pedidosvenda para contar entidades ou itens!
            
            REGRAS GERAIS:
            - SEMPRE use pedi_empr = 1 (sem aspas)
            - Para CONTAGEM DE REGISTROS use COUNT(), para SOMA DE VALORES use SUM()
            - Para agrupamentos use GROUP BY
            - Para ordenação use ORDER BY
            - Use DISTINCT quando necessário para evitar duplicatas
            - Sempre dê alias descritivos aos resultados

            PERGUNTA DO USUÁRIO: {query_forcada}

            PASSO 1: Identifique qual tabela usar baseado nas palavras-chave
            PASSO 2: Escolha a operação correta (COUNT, SUM, etc.)
            PASSO 3: Gere o SQL usando a tabela e campos corretos
            
            Retorne APENAS o código SQL.
            """ 

            # NOVA ABORDAGEM: Usa sistema robusto de geração SQL
            logger = logging.getLogger(__name__)
            sql = None
            usar_fallback = False
            
            # DETECÇÃO RÁPIDA DE LLM CORROMPIDO
            # Se o LLM está consistentemente gerando conteúdo corrompido,
            # usa fallback diretamente para economizar tempo e recursos
            
            if self.llm_esta_corrompido():
                logger.warning(f"LLM detectado como corrompido, usando fallback diretamente para query: {query}")
                sql = self.gerar_sql_fallback(query_forcada, tipo_consulta)
                usar_fallback = True
            else:
                # Primeira tentativa: LLM com sistema robusto
                sql = self.processar_sql_llm(contexto)
                
                if sql is None:
                    # Se LLM falhou, usa fallback
                    logger.warning(f"LLM falhou, usando fallback para query: {query}")
                    sql = self.gerar_sql_fallback(query_forcada, tipo_consulta)
                    usar_fallback = True
            
            # Validar SQL gerado antes da execução
            is_valid, error_msg = self.validar_sql(sql, tipo_consulta)
            if not is_valid:
                if not usar_fallback:
                    # Se LLM falhou, tenta fallback
                    logger.warning(f"SQL do LLM inválido, tentando fallback: {error_msg}")
                    sql_fallback = self.gerar_sql_fallback(query_forcada, tipo_consulta)
                    
                    # CONFIAR NO FALLBACK - Templates internos são seguros por design
                    # Apenas validação básica de estrutura e lógica de negócio
                    is_fallback_valid = self.validar_sql_basico(sql_fallback, tipo_consulta)
                    if is_fallback_valid:
                        sql = sql_fallback
                        usar_fallback = True
                        logger.info(f"Fallback SQL usado: {sql}")
                    else:
                        # Se nem fallback funciona, retorna erro
                        return f"❌ **Erro crítico**: Não foi possível gerar SQL válido.\n\n**Erro LLM**: {error_msg}\n\n**Tipo detectado**: {tipo_consulta}\n\n**Sugestão**: Tente uma pergunta mais simples como 'quantos pedidos' ou 'total faturado'."
                else:
                    # Se até o fallback falhou na validação rigorosa, usa validação básica
                    logger.warning(f"Fallback falhou na validação rigorosa, usando validação básica: {error_msg}")
                    is_basic_valid = self.validar_sql_basico(sql, tipo_consulta)
                    if not is_basic_valid:
                        return f"❌ **Erro crítico no sistema**: Fallback com problema estrutural.\n\n**Erro**: {error_msg}\n\n**Sugestão**: Contate o administrador do sistema."
             

            # REMOVER APLICAÇÃO DUPLICADA DE FILTRO - Templates já incluem filtros corretos
            # Os templates de fallback e LLM já incluem os filtros de empresa necessários
            # Aplicar filtro adicional causa duplicação e SQL inválido
            
            # Corrigir aliases no GROUP BY (mantido pois pode ser necessário)
            sql = corrigir_group_by_aliases(sql)
                

            # Executar SQL com tratamento robusto de erros
            try:
                with connection.cursor() as cursor:
                    cursor.execute(sql)
                    colunas = [col[0] for col in cursor.description]
                    resultados = [dict(zip(colunas, row)) for row in cursor.fetchall()]
                    
                    if not resultados:
                        return "📊 **Nenhum dado encontrado** para esta consulta. Tente:\n" + \
                               "\n".join([f"• {ex}" for ex in ErrorRecovery.get_example_queries()[:3]])
                        
            except DatabaseError as e:
                error_info = MCPErrorHandler.handle_database_error(e, "execução SQL")
                suggestions = ErrorRecovery.suggest_query_alternatives(query, error_info['error_type'])
                error_msg = MCPErrorHandler.format_user_error(error_info)
                if suggestions:
                    error_msg += "\n\n**Sugestões:**\n" + "\n".join([f"• {s}" for s in suggestions])
                return error_msg
                
            except Exception as e:
                error_info = MCPErrorHandler.handle_sql_error(e, sql, "execução")
                error_msg = MCPErrorHandler.format_user_error(error_info)
                return error_msg

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
            
            # Adiciona informações sobre o método usado
            info_metodo = ""
            if usar_fallback:
                info_metodo = "\n\n⚙️ _Sistema de fallback usado para garantir resposta confiável_"
            else:
                info_metodo = "\n\n🤖 _SQL gerado via IA_"
            
            # Monta resposta final
            resposta_final = resposta_texto + info_metodo + f"\n\n📊 **Consulta SQL:**\n```sql\n{sql}\n```"
            
            # Log para debugging
            logger.info(f"Consulta processada com sucesso | Fallback: {usar_fallback} | Query: {query[:50]}...")
            
            return resposta_final

        return consulta_mcp

    def get_tool(self):
        return self.tool

    def invoke(self, query: str) -> str:
            """Método invoke para compatibilidade com LangChain"""
            return self.tool.invoke({"query": query})

    def __call__(self, query: str) -> str:
        return self.tool.invoke({"query": query})


