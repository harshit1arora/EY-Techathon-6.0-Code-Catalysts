# MCP-SERVER-TATA-CAPITAL

# 🚀 Loan Sales Agentic API

A lightweight backend API for Personal Loan Eligibility, Offers, Document Verification, and Application Management.

---

# 📌 Base URL

```
http://127.0.0.1:8000/docs
```

---

# 📂 API Endpoints Overview

| Endpoint                            | Method | Description                      |
| ----------------------------------- | ------ | -------------------------------- |
| `/health`                           | GET    | Server status check              |
| `/loan/personal/check-eligibility`  | POST   | Check customer loan eligibility  |
| `/loan/personal/apply`              | POST   | Submit personal loan application |
| `/loan/personal/status`             | POST   | Track loan application status    |
| `/loan/personal/offer`              | POST   | Generate loan offers             |
| `/loan/personal/verify-pan`         | POST   | PAN verification                 |
| `/loan/personal/verify-salary-slip` | POST   | Salary slip verification         |
| `/loan/personal/cibil-score`        | POST   | Get CIBIL score                  |
| `/loan/personal/calculate-emi`      | POST   | Calculate EMI                    |

---

# 🟢 1. **GET /health**

### ✔ Check whether server is active

#### Response

```json
{
  "status": "ok",
  "message": "Server is running"
}
```

---

# 🟦 2. **POST /loan/personal/check-eligibility**

Checks loan eligibility based on income, CIBIL, age, and existing liabilities.

### Sample Request

```json
{
  "customer_id": "CUST001",
  "age": 28,
  "monthly_income": 45000,
  "existing_emis": 5000,
  "cibil_score": 735,
  "employment_type": "salaried"
}
```

### ✔ Success

```json
{
  "eligible": true,
  "approved_amount": 250000,
  "interest_rate": 12.5,
  "message": "Customer is eligible for the loan"
}
```

### ❌ Low Income

```json
{
  "eligible": false,
  "message": "Minimum income requirement not met"
}
```

### ❌ Low CIBIL

```json
{
  "eligible": false,
  "message": "CIBIL score too low for personal loan"
}
```

---

# 🟦 3. **POST /loan/personal/apply**

Creates a loan application entry.

### Sample Request

```json
{
  "customer_id": "CUST001",
  "loan_amount": 200000,
  "tenure_months": 36,
  "income": 45000,
  "employment_type": "salaried",
  "address": "Mumbai"
}
```

### ✔ Success

```json
{
  "application_id": "APP10235",
  "status": "submitted",
  "message": "Loan application submitted successfully"
}
```

### ❌ Missing Fields

```json
{
  "error": "customer_id and loan_amount are required"
}
```

---

# 🟦 4. **POST /loan/personal/status**

Retrieve status of a loan application.

### Sample Request

```json
{
  "application_id": "APP10235"
}
```

### ✔ Success

```json
{
  "application_id": "APP10235",
  "status": "under_review"
}
```

### ❌ Invalid ID

```json
{
  "error": "Application ID not found"
}
```

---

# 🟦 5. **POST /loan/personal/offer**

Generates personalized loan offers.

### Sample Request

```json
{
  "customer_id": "CUST001",
  "income": 45000,
  "cibil_score": 730
}
```

### ✔ Success

```json
{
  "customer_id": "CUST001",
  "offers": [
    {
      "loan_amount": 200000,
      "interest_rate": 12.4,
      "tenure_months": 36
    },
    {
      "loan_amount": 300000,
      "interest_rate": 13.5,
      "tenure_months": 48
    }
  ]
}
```

---

# 🟦 6. **POST /loan/personal/verify-pan**

Validates the PAN number format and mapping.

### Sample Request

```json
{
  "customer_id": "CUST001",
  "pan_number": "ABCDE1234F"
}
```

### ✔ Success

```json
{
  "valid": true,
  "message": "PAN verification successful"
}
```

### ❌ Invalid PAN

```json
{
  "valid": false,
  "message": "Invalid PAN format or not found"
}
```

---

# 🟦 7. **POST /loan/personal/verify-salary-slip**

Verifies if customer's salary slip is available in backend data folder.

### Sample Request

```json
{
  "customer_id": "CUST001"
}
```

### ✔ Success

```json
{
  "verified": true,
  "file": "salary_slip_CUST001.pdf"
}
```

### ❌ Not Found

```json
{
  "verified": false,
  "message": "Salary slip not found"
}
```

---

# 🟦 8. **POST /loan/personal/cibil-score**

Returns the stored CIBIL score for a customer.

### Sample Request

```json
{
  "customer_id": "CUST001"
}
```

### ✔ Success

```json
{
  "customer_id": "CUST001",
  "cibil_score": 742
}
```

### ❌ Not Found

```json
{
  "error": "Customer not found"
}
```

---

# 🟦 9. **POST /loan/personal/calculate-emi**

Calculates EMI using reducing balance interest formula.

### Sample Request

```json
{
  "loan_amount": 200000,
  "interest_rate": 12.5,
  "tenure_months": 36
}
```

### ✔ Success

```json
{
  "emi": 6681.23
}
```

### ❌ Missing Fields

```json
{
  "error": "loan_amount, interest_rate and tenure_months are required"
}
```

---

# 📌 Folder Structure Example

```
project/
│── main.py
│── requirements.txt
│── data/
│    ├── salary_slips/
│    │    ├── salary_slip_CUST001.pdf
│    │    ├── salary_slip_CUST002.pdf
│    │    └── ...
│    └── cibil_scores.json
```

---

# 🚀 Run Server

```
uvicorn main:app --reload
```

---
