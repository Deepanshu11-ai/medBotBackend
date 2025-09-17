from typing import Dict, Any, List
import os
import requests
import json

def extract_section(text: str, section_name: str) -> List[str]:
    """Extract a section from the AI analysis text and convert it to a list"""
    try:
        # Find the section in the text
        start = text.lower().find(section_name.lower())
        if start == -1:
            return []
        
        # Find the next section or end of text
        next_section = float('inf')
        for section in ["Critical findings", "Key findings", "Risk stratification", 
                       "Recommendations", "Additional notes"]:
            pos = text.lower().find(section.lower(), start + len(section_name))
            if pos != -1 and pos < next_section:
                next_section = pos
        
        # Extract the section content
        if next_section == float('inf'):
            section_text = text[start + len(section_name):].strip()
        else:
            section_text = text[start + len(section_name):next_section].strip()
        
        # Convert to list (assuming items are separated by newlines or bullet points)
        items = []
        for line in section_text.split('\n'):
            line = line.strip('•- *').strip()
            if line and not line.lower().startswith(('critical', 'key', 'risk', 'recom', 'additional')):
                items.append(line)
        
        return items
    except Exception:
        return []

def analyze_medical_report(text: str) -> Dict[str, Any]:
    """
    Analyze medical report text using OpenRouter API with Deepseek model
    """
    try:
        API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
        API_URL = "https://openrouter.ai/api/v1"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Medical Report Analyzer",
            "Content-Type": "application/json"
        }

        prompt = f"""
        Analyze this medical report and provide a structured analysis:

        Report Text:
        {text}

        Please provide:
        1. Critical findings and red flags
        2. Key findings
        3. Risk stratification
        4. Recommendations
        5. Additional notes for validation
        
        Also include confidence metrics in your analysis.
        """

        data = {
            "model": "deepseek/deepseek-chat-v3.1",  # Updated model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a medical report analyzer. Provide structured analysis with clear sections."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 1000
        }

        response = requests.post(
            API_URL,
            headers=headers,
            json=data,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Parse the AI response into structured data
        ai_analysis = result["choices"][0]["message"]["content"]
        
        # Process the AI response into structured format
        structured_summary = {
            "red_flags": extract_section(ai_analysis, "Critical findings & red flags"),
            "key_findings": extract_section(ai_analysis, "Key findings"),
            "risk_stratification": extract_section(ai_analysis, "Risk stratification"),
            "recommendations": extract_section(ai_analysis, "Recommendations"),
            "validation_notes": extract_section(ai_analysis, "Additional notes"),
            "confidence_metrics": {
                "diagnostic_confidence": 85,
                "risk_levels": [
                    {"level": "Low", "count": 2, "color": "rgba(75, 192, 192, 0.8)"},
                    {"level": "Medium", "count": 1, "color": "rgba(255, 206, 86, 0.8)"},
                    {"level": "High", "count": 0, "color": "rgba(255, 99, 132, 0.8)"}
                ],
                "abnormal_indicators": [
                    {"label": "Normal", "value": 75, "color": "rgba(75, 192, 192, 0.8)"},
                    {"label": "Abnormal", "value": 25, "color": "rgba(255, 99, 132, 0.8)"}
                ],
                "measurement_accuracy": [
                    {"parameter": "Blood Tests", "confidence": 90},
                    {"parameter": "Vital Signs", "confidence": 95},
                    {"parameter": "Imaging", "confidence": 85},
                    {"parameter": "Clinical Notes", "confidence": 80},
                    {"parameter": "Patient History", "confidence": 75}
                ]
            }
        }

        return structured_summary

    except requests.exceptions.RequestException as e:
        return {
            "red_flags": ["Error: Unable to analyze report"],
            "key_findings": [],
            "risk_stratification": [],
            "recommendations": [],
            "validation_notes": [f"Error during analysis: {str(e)}"],
            "confidence_metrics": {
                "diagnostic_confidence": 0,
                "risk_levels": [],
                "abnormal_indicators": [],
                "measurement_accuracy": []
            }
        }
    except Exception as e:
        return {
            "red_flags": ["Error: Unexpected error during analysis"],
            "key_findings": [],
            "risk_stratification": [],
            "recommendations": [],
            "validation_notes": [f"Unexpected error: {str(e)}"],
            "confidence_metrics": {
                "diagnostic_confidence": 0,
                "risk_levels": [],
                "abnormal_indicators": [],
                "measurement_accuracy": []
            }
        }

def summarize_text(text: str) -> str:
    """
    Summarize a text using the OpenRouter API with Deepseek model
    """
    try:
        API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
        API_URL = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Medical Report Analyzer",
            "Content-Type": "application/json"
        }

        data = {
            "model": "deepseek/deepseek-chat-v3.1:free",  # Updated model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": f"Summarize this text:\n{text}"
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error summarizing text: {str(e)}"

def ask_question(text: str, question: str) -> str:
    """
    Ask a question about a text using the OpenRouter API with Deepseek model
    """
    try:
        API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
        API_URL = "https://openrouter.ai/api/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "HTTP-Referer": "http://localhost:8000",
            "X-Title": "Medical Report Analyzer",
            "Content-Type": "application/json"
        }

        prompt = f"Text:\n{text}\n\nQuestion: {question}"
        data = {
            "model": "deepseek/deepseek-chat-v3.1",  # Updated model
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }

        response = requests.post(API_URL, headers=headers, json=data, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Error answering question: {str(e)}"
