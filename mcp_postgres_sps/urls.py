from django.urls import path
from .views import chat, ConsultaAPIView, clear_session_view

urlpatterns = [
    path('', chat, name='chat-ui'),
    path('api/consulta/', ConsultaAPIView.as_view(), name='consulta-api'),
    path('chat', ConsultaAPIView.as_view()), 
    path('clear', clear_session_view),      
]
