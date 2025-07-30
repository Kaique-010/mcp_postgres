from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .consulta_tool import ConsultaTool
from .model_registry import MODELS_MCP
from .relacionamento_registry import RELACIONAMENTOS_MCP
from .filtros_naturais import FILTROS_NATURAIS
from .model_tool_factory import ModelToolFactory
from .llm_config import llm


@method_decorator(csrf_exempt, name='dispatch')
class ConsultaAPIView(APIView):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.factory = ModelToolFactory(
            slug="mcp",
            models=MODELS_MCP,
            relacionamentos=RELACIONAMENTOS_MCP,
            alias_filtros=FILTROS_NATURAIS
        )
        self.consulta_tool = ConsultaTool(factory=self.factory, llm=llm)

    def post(self, request, *args, **kwargs):
        query = request.data.get("query")
        print('query Enviada:', query)
        if not query:
            return Response({"error": "query não informada"}, status=status.HTTP_400_BAD_REQUEST)
        
        resposta = self.consulta_tool(query)
        print('resposta:', resposta)
        return Response({"response": resposta})


def chat(request):
    return render(request, 'index.html')

def clear_session_view(request):
    if request.method == 'POST':
        request.session.clear()
        return Response({"message": "Sessão limpa com sucesso"}, status=status.HTTP_200_OK)
    return Response({"error": "método não permitido"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)