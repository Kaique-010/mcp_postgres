import hashlib
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

class QueryCache:
    def __init__(self, ttl_minutes: int = 30):
        self.cache: Dict[str, Dict] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_key(self, pergunta: str, slug: str) -> str:
        """Gera chave única para a consulta"""
        content = f"{pergunta.lower().strip()}_{slug}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, pergunta: str, slug: str) -> Optional[Dict]:
        """Recupera resultado do cache se válido"""
        key = self._generate_key(pergunta, slug)
        
        if key in self.cache:
            cached_item = self.cache[key]
            if datetime.now() - cached_item['timestamp'] < self.ttl:
                print(f"🎯 Cache hit: {pergunta[:50]}...")
                return cached_item['result']
            else:
                # Remove item expirado
                del self.cache[key]
        
        return None
    
    def set(self, pergunta: str, slug: str, resultado: Any, sql: str = None):
        """Armazena resultado no cache"""
        key = self._generate_key(pergunta, slug)
        self.cache[key] = {
            'result': resultado,
            'sql': sql,
            'timestamp': datetime.now(),
            'pergunta_original': pergunta
        }
        print(f"💾 Cache stored: {pergunta[:50]}...")
    
    def clear_expired(self):
        """Remove itens expirados do cache"""
        now = datetime.now()
        expired_keys = [
            key for key, item in self.cache.items()
            if now - item['timestamp'] > self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

# Instância global do cache
query_cache = QueryCache(ttl_minutes=30)