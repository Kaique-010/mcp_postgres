"""
Script para testar se os filtros de tipo de entidade foram corrigidos
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from consulta_tool import consultar_banco_dados_interno

def testar_consultas_sem_filtros():
    """Testa consultas que não devem ter filtros de tipo de entidade"""
    
    print("🧪 TESTANDO CORREÇÃO DOS FILTROS DE TIPO DE ENTIDADE")
    print("=" * 60)
    
    consultas_teste = [
        "TOP 10 clientes que mais compraram",
        "Pedidos por cliente nos últimos 30 dias",
        "Vendas por fornecedor este mês",
        "Total de pedidos por tipo de entidade",
        "Ranking de entidades que mais compraram"
    ]
    
    for i, pergunta in enumerate(consultas_teste, 1):
        print(f"\n🔍 TESTE {i}: {pergunta}")
        print("-" * 50)
        
        try:
            resultado = consultar_banco_dados_interno(pergunta, "casaa")
            
            # Verificar se o SQL gerado não contém filtros restritivos
            if "enti_tipo_enti = 'CL'" in resultado:
                print("❌ ERRO: SQL ainda contém filtro restritivo enti_tipo_enti = 'CL'")
            elif "enti_tipo_enti = 'FO'" in resultado:
                print("❌ ERRO: SQL ainda contém filtro restritivo enti_tipo_enti = 'FO'")
            elif "enti_tipo_enti" in resultado and "SELECT" in resultado:
                print("✅ CORRETO: SQL inclui enti_tipo_enti no SELECT (discriminando tipos)")
            else:
                print("⚠️  ATENÇÃO: Verificar se enti_tipo_enti está sendo incluído adequadamente")
            
            # Mostrar parte do resultado
            linhas = resultado.split('\n')
            for linha in linhas[:10]:  # Primeiras 10 linhas
                if linha.strip():
                    print(f"  {linha}")
            
            if len(linhas) > 10:
                print(f"  ... (mais {len(linhas) - 10} linhas)")
                
        except Exception as e:
            print(f"❌ ERRO na consulta: {e}")
    
    print(f"\n✅ TESTES CONCLUÍDOS!")
    print("Verifique se:")
    print("1. Nenhuma consulta usa filtros enti_tipo_enti = 'CL' ou 'FO'")
    print("2. O campo enti_tipo_enti aparece no SELECT para discriminar tipos")
    print("3. Os resultados incluem todas as entidades, independente do tipo")

if __name__ == "__main__":
    testar_consultas_sem_filtros()