import os
import json
import requests
from dotenv import load_dotenv
import google.generativeai as genai
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
from typing import TypedDict, List

# ==============================
# 1. Load API key
# ==============================
load_dotenv()
os.environ["GOOGLE_API_KEY"] = "AIzaSyDFmAT7k6pVujNqyAubBKO9NFCj7ZpMJYY"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ==============================
# 2. JSON Parsing Helper
# ==============================
def parse_ai_json(ai_text):
    try:
        return json.loads(ai_text)
    except json.JSONDecodeError:
        # Try extracting JSON from inside code block
        import re
        match = re.search(r"\{[\s\S]*\}", ai_text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass
    return {}

# ==============================
# 3. Agent State
# ==============================
class AgentState(TypedDict):
    messages: List[HumanMessage]

model = genai.GenerativeModel("models/gemini-2.5-pro")

def process(state: AgentState) -> AgentState:
    user_message = state["messages"][-1].content

    prompt = f"""
    You are given the raw HTML content of a job posting web page.
    Extract a structured summary in JSON format.
    Keys should include position, location, team, responsibilities, qualifications, etc.
    Respond ONLY with valid JSON.
    
    HTML content:
    {user_message}
    """

    response = model.generate_content(prompt)
    ai_text = response.text if response else "{}"

    parsed_json = parse_ai_json(ai_text)

    # Print & save JSON
    print("\n✅ Parsed JSON:\n", json.dumps(parsed_json, indent=2, ensure_ascii=False))
    with open("summary.json", "w", encoding="utf-8") as f:
        json.dump(parsed_json, f, indent=2, ensure_ascii=False)
    print("✅ Saved as summary.json")

    return state

# ==============================
# 4. Get HTML from URL
# ==============================
def fetch_html(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        print(f"❌ Error fetching URL: {e}")
        return ""

# ==============================
# 5. Run
# ==============================
graph = StateGraph(AgentState)
graph.add_node("process", process)
graph.add_edge(START, "process")
graph.add_edge("process", END)
agent = graph.compile()

if __name__ == "__main__":
    url = input("Enter the job posting URL: ").strip()
    html_content = fetch_html(url)

    if not html_content:
        print("❌ No HTML fetched. Exiting.")
        exit(1)

    agent.invoke({"messages": [HumanMessage(content=html_content)]})