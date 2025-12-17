import json
import re
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from groq import Groq
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession

from langchain_core.messages import HumanMessage

from sales import build_sales_graph
from verification import build_verification_graph
from underwriting import build_underwriting_graph
from sanction import build_sanction_graph


# --------------------------------------------------
# ENV
# --------------------------------------------------
load_dotenv()
groq = Groq(api_key=os.getenv("GROQ_API_KEY"))


# --------------------------------------------------
# MCP LIFESPAN (SINGLE SOURCE OF TRUTH)
# --------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # sse_client yields read_stream, write_stream
    async with sse_client("http://127.0.0.1:8000/sse") as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            app.state.mcp_session = session
            print("✅ MCP session connected")
            yield
            print("🛑 MCP session closed")



# --------------------------------------------------
# FASTAPI APP
# --------------------------------------------------
app = FastAPI(
    title="Loan Orchestrator",
    lifespan=lifespan
)


# --------------------------------------------------
# REQUEST MODEL
# --------------------------------------------------
class ChatRequest(BaseModel):
    message: str


# --------------------------------------------------
# LLM ROUTER (DECIDES AGENT)
# --------------------------------------------------
def route_agent(message: str) -> str:
    prompt = f"""
You are a loan workflow router.

Choose ONE agent:
- sales
- verification
- underwriting
- sanction

Return JSON ONLY:
{{ "agent": "" }}

User message:
\"{message}\"
"""

    res = groq.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    text = res.choices[0].message.content
    match = re.search(r"\{.*\}", text, re.S)

    if not match:
        return "sales"

    return json.loads(match.group()).get("agent", "sales")


# --------------------------------------------------
# AGENT EXECUTION
# --------------------------------------------------
async def run_agent(agent: str, message: str, session: ClientSession):
    state = {
        "messages": [HumanMessage(content=message)],
        "customer_id": "CUST001",
        "requested_amount": 50000,
        "preferred_tenure_months": 48,
        "max_interest_rate": 16.0,
        "salary": 500000,
        "pre_approved_limit": 200000,
        "credit_score": 750
    }

    if agent == "sales":
        graph = await build_sales_graph(session)
    elif agent == "verification":
        graph = await build_verification_graph(session)
    elif agent == "underwriting":
        graph = await build_underwriting_graph(session)
    elif agent == "sanction":
        graph = await build_sanction_graph(session)
    else:
        raise ValueError("Unknown agent")

    result = await graph.ainvoke(state)
    print("GRAPH RESULT:", result)

    # Safely extract the final message
    if isinstance(result, dict) and "messages" in result:
        return result["messages"][-1].content
    else:
        # fallback to negotiated_offer justification
        return result.get("negotiated_offer", {}).get("justification", str(result))



# --------------------------------------------------
# CHAT ENDPOINT
# --------------------------------------------------
@app.post("/chat")
async def chat(req: ChatRequest):
    agent = route_agent(req.message)
    session: ClientSession = app.state.mcp_session

    response = await run_agent(agent, req.message, session)

    return {
        "agent_called": agent,
        "response": response
    }


# --------------------------------------------------
# HEALTH
# --------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok"}