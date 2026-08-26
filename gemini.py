"""
Backward compatibility layer for gemini.py
Routes to the centralized AIService in services/ai_service.py
"""
from services.ai_service import get_ai_response, process_user_query

__all__ = ["get_ai_response", "process_user_query"]
