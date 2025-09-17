import os
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from .advice_analyzer import get_medical_advice
from .routes import router
# Initialize global variables
uploaded_text = ""  # Store full text from PDF/Word/TXT
uploaded_summary = {  # Store structured summary with default empty values
    "red_flags": [],
    "risk_stratification": [],
    "validation_notes": [],
    "key_findings": [],
    "recommendations": [],
    "confidence_metrics": {
        "diagnostic_confidence": 85,  # Default confidence level
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
chat_history = []  # Store chat messages with role and content


from PyPDF2 import PdfReader   # for PDFs
import docx                    # for Word files

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Make sure uploads folder exists
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = FastAPI(
    title="Medical Bot API",
    description="API for medical report analysis and AI-powered medical advice",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

app.include_router(router)

# CORS configuration for frontend
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and include API router
from .api import router as api_router
app.include_router(api_router)

# Static + Templates (for legacy web interface)
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
app.mount("/uploads", StaticFiles(directory=os.path.join(BASE_DIR, "uploads")), name="uploads")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.post("/get_advice")
async def get_advice(request: Request, query: str = Form(...)):
    """Get medical advice based on the uploaded report and user query"""
    if not uploaded_summary:
        return JSONResponse(
            content={"success": False, "error": "Please upload a medical report first"},
            status_code=400
        )
    
    result = get_medical_advice(uploaded_summary, query)
    return JSONResponse(content=result)

# Initialize chat history (we already have uploaded_summary defined above)
chat_history = []




# --- Utility: extract text from different file types ---
from PyPDF2 import PdfReader
import docx

def extract_text(file_path: str) -> str:
    ext = file_path.lower().split('.')[-1]
    text = ""
    if ext == "pdf":
        reader = PdfReader(file_path)
        for page in reader.pages:
            text += page.extract_text() or ""
    elif ext in ["docx", "doc"]:
        doc = docx.Document(file_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    elif ext == "txt":
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    return text


# --- Utility: better chat logic ---
from rapidfuzz import fuzz

def answer_query(text, structured_summary, user_input):
    """
    Provide focused answers to user questions about the medical document
    """
    user_input_lower = user_input.lower()
    words = set(user_input_lower.split())
    
    # First try to find specific matches in the text
    text_lines = text.split('\n')
    best_lines = []
    for line in text_lines:
        if any(word in line.lower() for word in words):
            best_lines.append(line.strip())
    
    if best_lines:
        # Return only the most relevant line(s)
        return "\n".join(best_lines[:2])  # Limit to 2 most relevant lines
    
    # If no direct matches, check structured sections for relevant info
    categories = {
        "red_flags": ["red flag", "warning", "alert", "danger", "concern"],
        "risk_stratification": ["risk", "severity", "condition", "status"],
        "validation_notes": ["validation", "note", "remark", "comment", "observation"]
    }
    
    # Look for category-specific questions
    for cat, keywords in categories.items():
        if any(kw in user_input_lower for kw in keywords):
            if structured_summary.get(cat):
                # Find the most relevant item in this category
                best_item = None
                best_score = 0
                for item in structured_summary[cat]:
                    score = sum(1 for word in words if word in item.lower())
                    if score > best_score:
                        best_score = score
                        best_item = item
                
                if best_item:
                    return best_item  # Return only the most relevant item
    
    # If no specific matches found
    if len(text) > 0:
        return "I couldn't find a specific answer to your question. Could you please be more specific or try rephrasing your question?"
    else:
        return "No document has been uploaded yet. Please upload a medical document first."

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "summary": uploaded_summary, "chat": chat_history}
    )

def structure_summary(text: str):
    """
    Analyze medical reports and extract key information including:
    - Red flags and critical findings
    - Risk stratification and assessments
    - Validation notes and recommendations
    - Key measurements and test results
    With confidence levels for findings
    """
    sections = {
        "red_flags": [],
        "risk_stratification": [],
        "validation_notes": [],
        "key_findings": [],
        "recommendations": [],
        "confidence_metrics": {
            "diagnostic_confidence": 0,
            "risk_levels": [],
            "abnormal_indicators": [],
            "measurement_accuracy": [],
            "test_results": []
        }
    }

    # Medical terms and patterns to look for
    critical_terms = [
        "abnormal", "critical", "urgent", "immediate", "severe", "danger",
        "warning", "alert", "high risk", "emergency", "concerning",
        "irregular", "elevated", "below normal", "positive for"
    ]
    
    risk_terms = [
        "risk", "probability", "likelihood", "chance", "stratification",
        "assessment", "score", "level", "grade", "stage", "classification"
    ]
    
    measurement_patterns = [
        "blood pressure", "heart rate", "temperature", "glucose",
        "cholesterol", "bpm", "mmHg", "mg/dL", "white blood cell",
        "red blood cell", "platelet", "hemoglobin", "creatinine"
    ]

    normal_ranges = {
        "blood pressure": (90, 120),  # Systolic
        "heart rate": (60, 100),
        "temperature": (36.5, 37.5),  # Celsius
        "glucose": (70, 140),  # mg/dL
        "cholesterol": (0, 200)  # mg/dL
    }

    lines = [line.strip() for line in text.split("\n") if line.strip()]
    
    for line in lines:
        l = line.lower()
        
        # Check for critical findings and red flags
        if any(term in l for term in critical_terms):
            sections["red_flags"].append(f"⚠️ {line}")
        
        # Look for numeric measurements and compare with normal ranges
        for measure in measurement_patterns:
            if measure in l:
                import re
                numbers = re.findall(r'\d+\.?\d*', l)
                if numbers:
                    try:
                        value = float(numbers[0])
                        if measure in normal_ranges:
                            low, high = normal_ranges[measure]
                            if value < low or value > high:
                                sections["red_flags"].append(f"⚠️ Abnormal {measure}: {line}")
                            else:
                                sections["key_findings"].append(f"✅ Normal {measure}: {line}")
                    except ValueError:
                        continue

        # Risk stratification analysis
        if any(term in l for term in risk_terms):
            sections["risk_stratification"].append(f"⚖️ {line}")
        
        # Look for recommendations and follow-up instructions
        if any(term in l for term in ["recommend", "suggest", "advise", "follow up", "referral"]):
            sections["recommendations"].append(f"💡 {line}")
        
        # Validation notes and additional findings
        if any(term in l for term in ["note", "observation", "finding", "impression", "conclusion"]):
            sections["validation_notes"].append(f"📝 {line}")

    # Add diagnostic summaries if found
    diagnosis_terms = ["diagnosis", "assessment", "impression"]
    for line in lines:
        l = line.lower()
        if any(term in l for term in diagnosis_terms):
            sections["key_findings"].append(f"🔍 {line}")

    # Calculate confidence metrics
    total_measurements = len([x for x in lines if any(pattern in x.lower() for pattern in measurement_patterns)])
    total_findings = len(sections["key_findings"])
    
    # Diagnostic confidence based on presence of key medical terms and measurements
    diagnostic_terms = sum(1 for line in lines if any(term in line.lower() for term in 
        ["diagnosis", "confirmed", "observed", "examination", "assessment"]))
    sections["confidence_metrics"]["diagnostic_confidence"] = min(100, (diagnostic_terms / max(1, len(lines))) * 100)
    
    # Risk level distribution
    risk_levels = {
        "high": sum(1 for x in sections["red_flags"] if any(term in x.lower() for term in ["severe", "critical", "high"])),
        "medium": sum(1 for x in sections["red_flags"] if any(term in x.lower() for term in ["moderate", "concerning"])),
        "low": sum(1 for x in sections["red_flags"] if any(term in x.lower() for term in ["mild", "minor", "low"]))
    }
    sections["confidence_metrics"]["risk_levels"] = [
        {"level": "High Risk", "count": risk_levels["high"], "color": "rgba(255, 99, 132, 0.8)"},
        {"level": "Medium Risk", "count": risk_levels["medium"], "color": "rgba(255, 206, 86, 0.8)"},
        {"level": "Low Risk", "count": risk_levels["low"], "color": "rgba(75, 192, 192, 0.8)"}
    ]

    # Abnormal indicators tracking
    abnormal_counts = {
        "critical": sum(1 for x in sections["red_flags"] if "critical" in x.lower()),
        "abnormal": sum(1 for x in sections["red_flags"] if "abnormal" in x.lower()),
        "normal": sum(1 for x in sections["key_findings"] if "normal" in x.lower())
    }
    sections["confidence_metrics"]["abnormal_indicators"] = [
        {"label": "Critical", "value": abnormal_counts["critical"], "color": "rgba(255, 99, 132, 0.8)"},
        {"label": "Abnormal", "value": abnormal_counts["abnormal"], "color": "rgba(255, 206, 86, 0.8)"},
        {"label": "Normal", "value": abnormal_counts["normal"], "color": "rgba(75, 192, 192, 0.8)"}
    ]

    # Measurement accuracy (based on presence of specific values)
    for measure in measurement_patterns:
        found = False
        for line in lines:
            if measure in line.lower() and any(char.isdigit() for char in line):
                sections["confidence_metrics"]["measurement_accuracy"].append({
                    "parameter": measure,
                    "confidence": 100 if any(unit in line.lower() for unit in ["mg/dl", "mmhg", "bpm"]) else 70
                })
                found = True
                break
        if not found and any(measure in line.lower() for line in lines):
            sections["confidence_metrics"]["measurement_accuracy"].append({
                "parameter": measure,
                "confidence": 30
            })

    # Test results confidence
    test_keywords = ["test", "examination", "scan", "x-ray", "mri", "ct", "ultrasound"]
    for keyword in test_keywords:
        count = sum(1 for line in lines if keyword in line.lower())
        if count > 0:
            sections["confidence_metrics"]["test_results"].append({
                "test_type": keyword.upper(),
                "count": count,
                "confidence": min(100, count * 20)
            })

    # If no entries found in any section, add default messages
    if not any(sections.values()):
        sections["validation_notes"].append("📝 No structured medical data found in the document.")
        
    # Remove duplicates while preserving order
    for key in sections:
        if isinstance(sections[key], list) and key != "confidence_metrics":
            sections[key] = list(dict.fromkeys(sections[key]))
            if not sections[key]:
                sections[key] = [f"No {key.replace('_', ' ')} found in the report."]

    return sections


@app.post("/upload")
async def upload_file(request: Request, file: UploadFile, user_location: str = Form(None)):
    global uploaded_text, uploaded_summary, chat_history
    
    # Save the uploaded file
    file_path = f"uploads/{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())
    
    # Always process new file uploads
    if file:
        chat_history.clear()
        uploaded_text = extract_text(file_path)
        uploaded_summary = structure_summary(uploaded_text)
    
    return templates.TemplateResponse("index.html", {
        "request": request,
        "summary": uploaded_summary,
        "chat": chat_history,
        "user_location": user_location
    })

@app.post("/chat")
async def chat(request: Request, user_input: str = Form(...)):
    global chat_history
    ai_reply = answer_query(uploaded_text, uploaded_summary, user_input)
    chat_history.append({"role": "user", "content": user_input})
    chat_history.append({"role": "ai", "content": ai_reply})
    return templates.TemplateResponse("index.html", {
        "request": request,
        "summary": uploaded_summary,
        "chat": chat_history
    })
