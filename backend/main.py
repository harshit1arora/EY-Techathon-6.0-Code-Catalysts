# mcp_server/main.py
import os
import json
import uuid
from typing import Any, Dict
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel
from reportlab.pdfgen import canvas
from datetime import datetime

# Config
STORAGE_DIR = os.environ.get("MCP_STORAGE_DIR", "./storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

app = FastAPI(title="NBFC MCP Server")

# --- Mock data: 10 synthetic customers
CUSTOMERS = {
    "CUST001": {"customer_id":"CUST001","name":"Asha Verma","age":32,"city":"Pune","phone":"9810000001","email":"asha@example.com","pre_approved_limit":300000,"salary_monthly":60000,"credit_score":745},
    "CUST002": {"customer_id":"CUST002","name":"Rahul Sharma","age":29,"city":"Delhi","phone":"9810000002","email":"rahul@example.com","pre_approved_limit":200000,"salary_monthly":45000,"credit_score":712},
    "CUST003": {"customer_id":"CUST003","name":"Sneha Iyer","age":35,"city":"Bengaluru","phone":"9810000003","email":"sneha@example.com","pre_approved_limit":400000,"salary_monthly":85000,"credit_score":780},
    "CUST004": {"customer_id":"CUST004","name":"Vikram Singh","age":40,"city":"Lucknow","phone":"9810000004","email":"vikram@example.com","pre_approved_limit":150000,"salary_monthly":30000,"credit_score":690},
    "CUST005": {"customer_id":"CUST005","name":"Nisha Patel","age":27,"city":"Ahmedabad","phone":"9810000005","email":"nisha@example.com","pre_approved_limit":250000,"salary_monthly":52000,"credit_score":710},
    "CUST006": {"customer_id":"CUST006","name":"Arjun Rao","age":31,"city":"Hyderabad","phone":"9810000006","email":"arjun@example.com","pre_approved_limit":350000,"salary_monthly":70000,"credit_score":760},
    "CUST007": {"customer_id":"CUST007","name":"Meera Desai","age":30,"city":"Surat","phone":"9810000007","email":"meera@example.com","pre_approved_limit":180000,"salary_monthly":40000,"credit_score":695},
    "CUST008": {"customer_id":"CUST008","name":"Karan Mehta","age":33,"city":"Mumbai","phone":"9810000008","email":"karan@example.com","pre_approved_limit":320000,"salary_monthly":65000,"credit_score":735},
    "CUST009": {"customer_id":"CUST009","name":"Priya Nair","age":28,"city":"Kochi","phone":"9810000009","email":"priya@example.com","pre_approved_limit":280000,"salary_monthly":48000,"credit_score":725},
    "CUST010": {"customer_id":"CUST010","name":"Sourav Ghosh","age":36,"city":"Kolkata","phone":"9810000010","email":"sourav@example.com","pre_approved_limit":500000,"salary_monthly":90000,"credit_score":790}
}

# Tools manifest
@app.get("/tools")
def get_tools():
    tools = [
        {
            "name": "get_customer_info",
            "description": "Fetch customer basic info",
            "input_schema": {
                "type":"object",
                "properties":{"customer_id":{"type":"string"}},
                "required":["customer_id"]
            }
        },
        {"name":"verify_kyc","description":"Verify phone/address (mock)"},
        {"name":"get_credit_score","description":"Return credit score for customer"},
        {"name":"underwrite_loan","description":"Underwriting decision using stated rules"},
        {"name":"upload_salary_slip","description":"Upload salary slip file"},
        {"name":"generate_sanction_letter","description":"Generate sanction PDF"},
        {"name":"log_event","description":"Audit log an event"}
    ]
    return {"tools": tools}

# Models
class UnderwriteInput(BaseModel):
    customer_id: str
    requested_amount: int
    tenure_months: int = 36
    annual_rate: float = 12.0
    salary_provided: int = None
    salary_slip_resource: str = None

# Tool: get_customer_info
@app.post("/call/get_customer_info")
def call_get_customer_info(payload: Dict[str, Any]):
    cid = payload.get("customer_id")
    if not cid:
        raise HTTPException(status_code=400, detail="customer_id required")
    cust = CUSTOMERS.get(cid)
    if not cust:
        raise HTTPException(status_code=404, detail="customer not found")
    return {"status":"ok","result":cust}

# Tool: verify_kyc
@app.post("/call/verify_kyc")
def call_verify_kyc(payload: Dict[str, Any]):
    cid = payload.get("customer_id")
    phone = payload.get("phone")
    if not cid or not phone:
        raise HTTPException(status_code=400, detail="customer_id and phone required")
    cust = CUSTOMERS.get(cid)
    if not cust:
        raise HTTPException(status_code=404, detail="customer not found")
    phone_verified = (cust.get("phone") == phone)
    return {"status":"ok","result":{"phone_verified":phone_verified,"address_verified":True}}

# Tool: get_credit_score
@app.post("/call/get_credit_score")
def call_get_credit_score(payload: Dict[str, Any]):
    cid = payload.get("customer_id")
    if not cid:
        raise HTTPException(status_code=400)
    cust = CUSTOMERS.get(cid)
    if not cust:
        raise HTTPException(status_code=404)
    return {"status":"ok","result":{"credit_score":cust.get("credit_score")}}

# EMI helper
def compute_emi(P: float, annual_rate: float, n_months: int) -> float:
    r = annual_rate / 12.0 / 100.0
    if r == 0:
        return P / n_months
    num = P * r * (1 + r) ** n_months
    den = (1 + r) ** n_months - 1
    return num / den

# Tool: underwrite_loan
@app.post("/call/underwrite_loan")
def call_underwrite_loan(payload: UnderwriteInput):
    data = payload
    cid = data.customer_id
    cust = CUSTOMERS.get(cid)
    if not cust:
        raise HTTPException(status_code=404)

    score = cust.get("credit_score", 0)
    pre_limit = cust.get("pre_approved_limit", 0)
    requested = data.requested_amount
    tenure = data.tenure_months
    annual_rate = data.annual_rate

    if score < 700:
        return {"status":"ok","result":{"decision":"reject","reason":"credit_score_below_700","credit_score":score}}

    if requested <= pre_limit:
        emi = compute_emi(requested, annual_rate, tenure)
        return {"status":"ok","result":{"decision":"approve","emi":emi,"reason":"within_pre_approved_limit"}}

    if requested <= 2 * pre_limit:
        if not data.salary_slip_resource and not data.salary_provided:
            return {"status":"ok","result":{"decision":"require_salary_slip","reason":"salary_slip_required"}}

        salary = data.salary_provided if data.salary_provided is not None else cust.get("salary_monthly", 0)
        emi = compute_emi(requested, annual_rate, tenure)

        if emi <= 0.5 * salary:
            return {"status":"ok","result":{"decision":"approve","emi":emi,"reason":"emi_within_50pct_salary"}}
        else:
            return {"status":"ok","result":{"decision":"reject","reason":"emi_exceeds_50pct_salary","emi":emi,"salary_monthly":salary}}

    return {"status":"ok","result":{"decision":"reject","reason":"amount_exceeds_2x_pre_approved","pre_limit":pre_limit,"requested":requested}}

# Tool: upload_salary_slip
@app.post("/call/upload_salary_slip")
async def call_upload_salary_slip(customer_id: str = None, file: UploadFile = File(...)):
    if not customer_id:
        raise HTTPException(status_code=400, detail="customer_id required")
    if customer_id not in CUSTOMERS:
        raise HTTPException(status_code=404, detail="customer not found")

    ext = os.path.splitext(file.filename)[1] or ".pdf"
    filename = f"salary_{customer_id}_{uuid.uuid4().hex}{ext}"
    path = os.path.join(STORAGE_DIR, filename)

    with open(path, "wb") as f:
        contents = await file.read()
        f.write(contents)

    resource_url = f"resource://{filename}"
    return {"status":"ok","result":{"resource":resource_url,"path":path}}

# Tool: generate_sanction_letter
@app.post("/call/generate_sanction_letter")
def call_generate_sanction_letter(payload: Dict[str, Any]):
    cid = payload.get("customer_id")
    amount = payload.get("amount")

    if not cid or not amount:
        raise HTTPException(status_code=400)

    cust = CUSTOMERS.get(cid)
    if not cust:
        raise HTTPException(status_code=404)

    filename = f"sanction_{cid}_{uuid.uuid4().hex}.pdf"
    path = os.path.join(STORAGE_DIR, filename)

    c = canvas.Canvas(path)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(50, 800, "Sanction Letter")
    c.setFont("Helvetica", 11)
    c.drawString(50, 770, f"Date: {datetime.utcnow().strftime('%Y-%m-%d')}")
    c.drawString(50, 750, f"Customer: {cust.get('name')} (ID: {cid})")
    c.drawString(50, 730, f"Approved Amount: INR {amount}")
    c.drawString(50, 710, f"Tenure: {payload.get('tenure_months', 36)} months")
    c.drawString(50, 690, f"Interest Rate (annual): {payload.get('interest_rate', 12.0)}%")
    c.drawString(50, 660, "This is a demo sanction letter generated by MCP server.")
    c.save()

    resource_url = f"resource://{filename}"
    return {"status":"ok","result":{"resource":resource_url,"path":path}}

# Fetch stored resource
@app.get("/resource/{filename}")
def fetch_resource(filename: str):
    path = os.path.join(STORAGE_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404)
    return FileResponse(path)

# Log event
@app.post("/call/log_event")
def call_log_event(payload: Dict[str, Any]):
    with open(os.path.join(STORAGE_DIR, "mcp_audit.log"), "a") as f:
        f.write(json.dumps({"ts": datetime.utcnow().isoformat(), "event": payload}) + "\n")
    return {"status":"ok"}

# Health
@app.get("/health")
def health():
    return {"status":"ok","time": datetime.utcnow().isoformat()}

# Main entry
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
