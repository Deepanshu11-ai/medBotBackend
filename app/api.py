from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from typing import Dict, Any, List, Optional
import os
import json
from .pdf_parser import extract_text_from_pdf
from .llm_analyzer import analyze_medical_report
from .advice_analyzer import get_medical_advice

router = APIRouter(prefix="/api/v1", tags=["Medical Bot API"])

# Store state (in production, use a proper database)
current_report = {
    "text": "",
    "summary": None,
    "chat_history": []
}

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_location: Optional[str] = Form(None)
) -> Dict[str, Any]:
    """
    Upload and analyze a medical report file
    """
    try:
        # Save file
        file_path = f"uploads/{file.filename}"
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract text
        text = extract_text_from_pdf(file_path)
        current_report["text"] = text
        
        # Analyze report
        summary = analyze_medical_report(text)
        current_report["summary"] = summary
        
        return {
            "success": True,
            "summary": summary,
            "message": "File uploaded and analyzed successfully"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
async def get_summary() -> Dict[str, Any]:
    """
    Get the current medical report summary
    """
    if not current_report["summary"]:
        raise HTTPException(status_code=404, detail="No report has been analyzed yet")
    
    return {
        "success": True,
        "summary": current_report["summary"]
    }

@router.post("/chat")
async def chat(message: str = Form(...)) -> Dict[str, Any]:
    """
    Chat about the current medical report
    """
    if not current_report["text"]:
        raise HTTPException(status_code=404, detail="No report has been uploaded yet")
    
    # Add user message to history
    current_report["chat_history"].append({
        "role": "user",
        "content": message
    })
    
    try:
        # Generate response based on the report context
        response = get_medical_advice(current_report["summary"], message)
        
        if response["success"]:
            current_report["chat_history"].append({
                "role": "assistant",
                "content": response["advice"]
            })
            
            return {
                "success": True,
                "message": response["advice"],
                "chat_history": current_report["chat_history"]
            }
        else:
            raise HTTPException(status_code=500, detail=response["error"])
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/chat-history")
async def get_chat_history() -> Dict[str, Any]:
    """
    Get the current chat history
    """
    return {
        "success": True,
        "chat_history": current_report["chat_history"]
    }

@router.post("/advice")
async def get_advice(query: str = Form(...)) -> Dict[str, Any]:
    """
    Get specific medical advice based on the report
    """
    if not current_report["summary"]:
        raise HTTPException(status_code=404, detail="No report has been analyzed yet")
    
    response = get_medical_advice(current_report["summary"], query)
    
    if response["success"]:
        return {
            "success": True,
            "advice": response["advice"]
        }
    else:
        raise HTTPException(status_code=500, detail=response["error"])

@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """
    Get confidence metrics and analysis data
    """
    if not current_report["summary"]:
        raise HTTPException(status_code=404, detail="No report has been analyzed yet")
    
    metrics = current_report["summary"].get("confidence_metrics", {})
    return {
        "success": True,
        "metrics": metrics
    }

@router.get("/status")
async def get_status() -> Dict[str, Any]:
    """
    Get the current status of the system
    """
    return {
        "success": True,
        "has_report": bool(current_report["text"]),
        "has_summary": bool(current_report["summary"]),
        "chat_messages": len(current_report["chat_history"])
    }