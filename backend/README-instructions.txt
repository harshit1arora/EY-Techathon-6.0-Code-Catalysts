# Run locally (development)
docker compose up --build

# After container is up:
# 1) Get demo token:
curl http://localhost:8000/auth/demo_token
# Use returned token as "Authorization: Bearer <token>"

# 2) List tools:
curl -H "Authorization: Bearer <token>" http://localhost:8000/tools

# 3) Get customer info:
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"customer_id":"CUST001"}' http://localhost:8000/call/get_customer_info

# 4) Underwrite (example):
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"customer_id":"CUST001","requested_amount":450000,"tenure_months":36}' \
  http://localhost:8000/call/underwrite_loan

# 5) Upload salary slip (multipart form):
curl -X POST -H "Authorization: Bearer <token>" -F "customer_id=CUST001" -F "file=@/path/to/demo_salary.pdf" \
  http://localhost:8000/call/upload_salary_slip

# 6) Generate sanction letter (after approval):
curl -X POST -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
  -d '{"customer_id":"CUST001","amount":300000,"tenure_months":24,"interest_rate":12.0}' \
  http://localhost:8000/call/generate_sanction_letter
