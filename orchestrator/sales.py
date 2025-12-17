import asyncio
import json
from typing import TypedDict, Dict, Any
import httpx

from dotenv import load_dotenv

from pydantic import BaseModel, Field
from langgraph.graph import StateGraph, START, END
from langchain_google_genai import ChatGoogleGenerativeAI

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client


load_dotenv()

class NegotiatedOffer(BaseModel):
    customer_id: str = Field(description="Unique identifier for the customer")
    approved_amount: int = Field(description="Amount upto which NBFC is allowed to give up personal loan")
    tenure_months: int = Field(description="Period in months for which loan is to be taken")
    interest_rate: float = Field(description="Interest rate upto which loan can be approved")
    justification: str = Field(description="Justification for the approval or rejection of deal")


class SalesAgentState(TypedDict, total=False):
    customer_id: str
    requested_amount: int
    preferred_tenure_months: int
    max_interest_rate: float
    salary:int
    pre_approved_limit: int
    credit_score: int

    customer_info: Dict[str, Any]
    negotiated_offer: Dict[str, Any]
    

async def build_sales_graph(session:ClientSession):

    llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0.2,
            max_output_tokens=2048,
        ).with_structured_output(NegotiatedOffer)

    # NODE 1 → FETCH CUSTOMER INFO
    async def fetch_customer_info(state: SalesAgentState) -> SalesAgentState:
        cid = "CUST001"
        try:
            result = await session.call_tool(
                "get_customer_info",
                arguments={"customer_id": cid}
            )
            customer_data = json.loads(result.content[0].text)
            if "result" in customer_data and isinstance(customer_data["result"], dict):
                state["customer_info"] = customer_data["result"]
            else:
                 state["customer_info"] = customer_data

        except httpx.ConnectError:
            print("RROR: Connection Refused. (Likely the 0.0.0.0 bug)")
            state["customer_info"] = {"error": "Connection Refused"}
            
        except httpx.TimeoutException:
            print("ERROR: Timed Out. (Server is blocked or slow)")
            state["customer_info"] = {"error": "Timeout"}
            
        except Exception as e:
            print(f"ERROR: Generic Exception -> {type(e).__name__}: {e}")
            state["customer_info"] = {"error": str(e)}

        return state

    # NODE 2 → LLM_NODE 
    async def llm_node(state: SalesAgentState):
        # Debug: log incoming state
        print(f"DEBUG llm_node incoming state: {state}")
        # Safely read values from state and fall back to parsing the last message or defaults
        customer = state.get("customer_info", {})
        requested = 50000
        tenure = 48
        max_rate = 16.0
        salary= 500000
        pre_approved_limit = 200000
        credit_score = 750

        # If any of the key parameters are missing, try to extract them from the incoming message
        if requested is None or tenure is None or max_rate is None:
            messages = state.get("messages", [])
            last_text = None
            for m in reversed(messages):
                if hasattr(m, "content") and isinstance(m.content, str):
                    last_text = m.content
                    break

            if last_text:
                import re
                if requested is None:
                    m = re.search(r"requested.*?(\d{4,7})", last_text, re.I)
                    if m:
                        requested = int(m.group(1))
                if tenure is None:
                    m = re.search(r"tenure.*?(\d{1,3})", last_text, re.I)
                    if m:
                        tenure = int(m.group(1))
                if max_rate is None:
                    m = re.search(r"(?:interest rate|rate).*?(\d{1,2}(?:\.\d+)?)", last_text, re.I)
                    if m:
                        try:
                            max_rate = float(m.group(1))
                        except ValueError:
                            pass

        #Reasonable defaults if still missing
        if requested is None:
            print("WARNING: 'requested_amount' missing from state; using default 100000")
            requested = 100000
        if tenure is None:
            print("WARNING: 'preferred_tenure_months' missing from state; using default 12")
            tenure = 12
        if max_rate is None:
            print("WARNING: 'max_interest_rate' missing from state; using default 20.0")
            max_rate = 20.0

        context = {
            "customer_info": customer,
            "requested_amount": requested,
            "preferred_tenure_months": tenure,
            "max_interest_rate": max_rate,
            "salary":salary,
            "pre_approved_limit":pre_approved_limit,
            "credit_score" :credit_score
        }

        system_prompt = f"""
        You are an NBFC Sales Agent. 
        negotiate the offer based on the given rules by utilising the given context.

        Negotiate loan terms based on:
        - customer salary
        - pre-approved limit
        - credit score
        - requested amount
        - preferred tenure
        - max acceptable interest rate

        Rules:
        - Never exceed max_interest_rate.
        - Stay within 2x pre-approved limit.
        - If credit score < 720, be conservative.
        - Provide clear justification.
        Return only JSON following the NegotiatedOffer schema.
        """

        try:
            result = await llm.ainvoke(
                f""" {system_prompt} \n "context": {json.dumps(context, indent=2)} """
            )
            state["negotiated_offer"] = result.model_dump()
        except Exception as e:
            print(f"ERROR: LLM invocation failed: {type(e).__name__}: {e}")
            # Store the error in the state so downstream logic can handle it
            state["negotiated_offer"] = {"error": str(e)}

        return state
    

    graph = StateGraph(SalesAgentState)

    graph.add_node("fetch_customer_info", fetch_customer_info)
    graph.add_node("llm_node", llm_node)
    

    graph.add_edge(START, "fetch_customer_info")
    graph.add_edge("fetch_customer_info", "llm_node")
    graph.add_edge("llm_node", END)

    return graph.compile()



async def main():

    server_url = "http://127.0.0.1:8000/sse"
    header = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream"
    }
    timeout = 30.0

    async with sse_client(server_url,headers=header, timeout=timeout) as streams:
        read_stream, write_stream = streams
        async with ClientSession(read_stream, write_stream) as session:
            print("Successfully connected to MCP server")

            await session.initialize()

            agent = await build_sales_graph(session)

            # HERE MAKE THE SALES AGENT FETCH DETAIL FROM ORCHESTRATOR SHARED STATE AND RETURN THE UPDATED STATE ACCORDINGLY
            # THIS CODE NEEDS TO BE CHANGED
            
            init: SalesAgentState = {
                "customer_id": "CUST005",
                "requested_amount": 350000,
                "preferred_tenure_months": 48,
                "max_interest_rate": 16.0
            }
            
            final_state = await agent.ainvoke(init)
            print(json.dumps(final_state, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
