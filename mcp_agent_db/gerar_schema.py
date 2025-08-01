# gerar_schema.py

import psycopg2
import sqlite3
import os
import json
from typing import Dict, List, Any

SCHEMA_DIR = "schemas"

# Configurações de exemplo para diferentes tipos de banco
DATABASES = {
    "casaa": {
        "tipo": "postgres",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "@spartacus201@",
        "dbname": "casaa"
    },
    "spartacus": {
        "tipo": "postgres",
        "host": "localhost",
        "port": 5432,
        "user": "postgres",
        "password": "postgres",
        "dbname": "spartacus"
    },
    "cliente_sqlite": {
        "tipo": "sqlite",
        "caminho": "exemplo.db"
    },
    "cliente_teste": {
        "tipo": "sqlite",
        "caminho": "teste.db"
    },
    "cliente_mysql": {
        "tipo": "mysql",
        "host": "localhost",
        "port": 3306,
        "user": "root",
        "password": "senha",
        "dbname": "cliente_db"
    }
}

def conectar_db(config: Dict[str, Any]):
    """Conecta ao banco baseado no tipo configurado"""
    tipo = config.get("tipo", "postgres")
    
    if tipo == "postgres":
        return psycopg2.connect(
            host=config["host"],
            port=config["port"],
            user=config["user"],
            password=config["password"],
            dbname=config["dbname"]
        )
    elif tipo == "sqlite":
        return sqlite3.connect(config["caminho"])
    elif tipo == "mysql":
        try:
            import mysql.connector
            return mysql.connector.connect(
                host=config["host"],
                port=config["port"],
                user=config["user"],
                password=config["password"],
                database=config["dbname"]
            )
        except ImportError:
            raise ImportError("mysql-connector-python não instalado. Execute: pip install mysql-connector-python")
    else:
        raise ValueError(f"Tipo de banco não suportado: {tipo}")

def extrair_schema_postgres(conexao):
    """Extrai schema do PostgreSQL"""
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT 
            t.table_name,
            c.column_name,
            c.data_type,
            c.is_nullable,
            c.column_default,
            CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
        FROM information_schema.tables t
        JOIN information_schema.columns c ON t.table_name = c.table_name
        LEFT JOIN (
            SELECT ku.table_name, ku.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage ku ON tc.constraint_name = ku.constraint_name
            WHERE tc.constraint_type = 'PRIMARY KEY'
        ) pk ON c.table_name = pk.table_name AND c.column_name = pk.column_name
        WHERE t.table_schema = 'public' AND t.table_type = 'BASE TABLE'
        ORDER BY t.table_name, c.ordinal_position;
    """)
    return cursor.fetchall()

def extrair_schema_sqlite(conexao):
    """Extrai schema do SQLite"""
    cursor = conexao.cursor()
    
    # Obter lista de tabelas
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tabelas = cursor.fetchall()
    
    resultado = []
    for (tabela,) in tabelas:
        # Obter informações das colunas
        cursor.execute(f"PRAGMA table_info({tabela});")
        colunas = cursor.fetchall()
        
        for col in colunas:
            cid, nome, tipo, notnull, default_value, pk = col
            resultado.append((
                tabela,
                nome, 
                tipo,
                'NO' if notnull else 'YES',  # is_nullable
                default_value,
                bool(pk)  # is_primary_key
            ))
    
    return resultado

def extrair_schema(conexao, tipo_banco="postgres"):
    """Extrai schema baseado no tipo de banco"""
    if tipo_banco == "postgres":
        dados = extrair_schema_postgres(conexao)
    elif tipo_banco == "sqlite":
        dados = extrair_schema_sqlite(conexao)
    else:
        raise ValueError(f"Tipo de banco não suportado para extração: {tipo_banco}")
    
    schema = {}
    for row in dados:
        table_name, column_name, data_type, is_nullable, column_default, is_primary_key = row
        
        if table_name not in schema:
            schema[table_name] = {
                "colunas": [],
                "descricao": f"Tabela {table_name}"
            }
        
        schema[table_name]["colunas"].append({
            "nome": column_name,
            "tipo": data_type,
            "nullable": is_nullable == 'YES',
            "default": column_default,
            "primary_key": is_primary_key
        })
    
    return schema

def salvar_schema(slug, schema):
    os.makedirs(SCHEMA_DIR, exist_ok=True)
    caminho = os.path.join(SCHEMA_DIR, f"{slug}.json")
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)
    print(f"✅ Schema salvo em {caminho}")

def gerar_schema(slug: str):
    """Gera schema para um cliente específico"""
    print(f"🔍 Gerando schema para: {slug}")
    
    config = DATABASES.get(slug)
    if not config:
        raise ValueError(f"Slug '{slug}' não encontrado em DATABASES")
    
    print(f"📊 Conectando ao banco {config.get('tipo', 'postgres')}...")
    conn = conectar_db(config)
    
    try:
        schema = extrair_schema(conn, config.get('tipo', 'postgres'))
        salvar_schema(slug, schema)
        
        # Mostrar resumo
        total_tabelas = len(schema)
        total_colunas = sum(len(tabela['colunas']) for tabela in schema.values())
        print(f"✅ Schema extraído: {total_tabelas} tabelas, {total_colunas} colunas")
        
        return schema
        
    finally:
        conn.close()

def criar_banco_exemplo_sqlite():
    """Cria um banco SQLite de exemplo para testar"""
    print("🛠️ Criando banco SQLite de exemplo...")
    
    conn = sqlite3.connect("exemplo.db")
    cursor = conn.cursor()
    
    # Criar tabelas de exemplo
    cursor.executescript("""
        DROP TABLE IF EXISTS pedidos;
        DROP TABLE IF EXISTS clientes;
        DROP TABLE IF EXISTS produtos;
        
        CREATE TABLE clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE,
            data_cadastro DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            preco DECIMAL(10,2),
            categoria TEXT,
            ativo BOOLEAN DEFAULT 1
        );
        
        CREATE TABLE pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER,
            produto_id INTEGER,
            quantidade INTEGER DEFAULT 1,
            valor_total DECIMAL(10,2),
            data_pedido DATETIME DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pendente'
        );
        
        -- Dados de exemplo
        INSERT INTO clientes (nome, email) VALUES 
            ('João Silva', 'joao@email.com'),
            ('Maria Santos', 'maria@email.com');
            
        INSERT INTO produtos (nome, preco, categoria) VALUES 
            ('Notebook', 2500.00, 'eletrônicos'),
            ('Mouse', 50.00, 'acessórios');
            
        INSERT INTO pedidos (cliente_id, produto_id, quantidade, valor_total) VALUES 
            (1, 1, 1, 2500.00),
            (2, 2, 2, 100.00);
    """)
    
    conn.commit()
    conn.close()
    print("✅ Banco SQLite criado: exemplo.db")

def testar_sistema_completo():
    """Testa o sistema completo de geração de schema"""
    print("🚀 TESTANDO SISTEMA DE GERAÇÃO DE SCHEMA")
    print("=" * 50)
    
    # Criar banco de exemplo
    criar_banco_exemplo_sqlite()
    
    # Gerar schema
    schema = gerar_schema("cliente_sqlite")
    
    # Mostrar resultado
    print("\n📋 SCHEMA GERADO:")
    for tabela, info in schema.items():
        print(f"\n🔹 {tabela}:")
        for coluna in info['colunas']:
            pk = " (PK)" if coluna['primary_key'] else ""
            nullable = "NULL" if coluna['nullable'] else "NOT NULL"
            print(f"  - {coluna['nome']}: {coluna['tipo']} {nullable}{pk}")
    
    return schema

if __name__ == "__main__":
    # Testar sistema completo
    testar_sistema_completo()
