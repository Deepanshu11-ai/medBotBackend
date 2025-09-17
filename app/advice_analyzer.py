import os
import requests
from typing import Dict, Any
from concurrent.futures import ThreadPoolExecutor, TimeoutError

def get_medical_advice(summary: str, query: str) -> Dict[str, Any]:
    """
    Get medical advice using OpenRouter API with Deepseek model
    """
    try:
        API_KEY = os.getenv("OPENROUTER_API_KEY","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")
        if not API_KEY:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
            
        API_URL = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "http://localhost:8000",  # Changed to http instead of https
            "X-Title": "Medical Report Analyzer",
            "Content-Type": "application/json"
        }

        # Optimized prompt for faster response
        prompt = f"""
        As a medical assistant, provide a concise analysis based on:

        Summary: {summary}
        Query: {query}

        Quick response format:
        1. Direct answer (2-3 sentences)
        2. Key recommendations (bullet points)
        3. Important precautions
        4. Quick follow-up notes
        5. Warning signs (if any)

        Keep responses brief but informative.
        """

        data = {
            "model": "deepseek/deepseek-chat-v3.1:free",  # Using faster Claude Instant model
            "messages": [
                {"role": "system", "content": "You are a knowledgeable medical assistant providing accurate and helpful medical advice."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 500,  # Reduced tokens for faster response
            "top_p": 0.9,
            "stream": False  # Ensure non-streaming response
        }

        # Use ThreadPoolExecutor for timeout management
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(
                requests.post,
                API_URL,
                headers=headers,
                json=data,
                timeout=15  # Reduced timeout
            )
            
            try:
                response = future.result(timeout=20)  # Total timeout including processing
                response.raise_for_status()
                
                # Parse response
                result = response.json()
                
                # Early response with initial content
                return {
                    "success": True,
                    "advice": result["choices"][0]["message"]["content"],
                    "error": None
                }
                
            except TimeoutError:
                return {
                    "success": False,
                    "advice": None,
                    "error": "Request timed out. Please try again."
                }
            except requests.exceptions.ReadTimeout:
                return {
                    "success": False,
                    "advice": None,
                    "error": "Response taking too long. Please try a shorter query."
                }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "advice": None,
            "error": f"API Request Error: {str(e)}"
        }
    except Exception as e:
        return {
            "success": False,
            "advice": None,
            "error": f"Unexpected Error: {str(e)}"
        }
