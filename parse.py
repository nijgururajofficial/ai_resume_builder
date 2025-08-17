import sys
import io
import os
import json
import re
import traceback
from PyPDF2 import PdfReader
from typing import TypedDict, List
from dotenv import load_dotenv
import google.generativeai as genai
from langgraph.graph import StateGraph, START, END
from langchain_core.messages import HumanMessage
import threading
import time

# ==============================
# 1. Load API key
# ==============================
load_dotenv()
os.environ["GOOGLE_API_KEY"] = "AIzaSyDFmAT7k6pVujNqyAubBKO9NFCj7ZpMJYY"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# ==============================
# 2. JSON parsing function
# ==============================
def parse_ai_json(ai_text):
    # Extract JSON inside ```json ... ``` code block
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", ai_text, re.DOTALL)
    
    if json_match:
        json_str = json_match.group(1)  # Extracted JSON string
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None
    else:
        # No ```json code block found, try to parse whole string anyway
        try:
            return json.loads(ai_text)
        except json.JSONDecodeError as e:
            print(f"JSON decode error: {e}")
            return None

# ==============================
# 3. Agent state
# ==============================
class AgentState(TypedDict):
    messages: List[HumanMessage]
    pdf_text: str

model = genai.GenerativeModel("models/gemini-2.5-pro")

def process(state: AgentState) -> AgentState:
    prompt = f"Here is the extracted text from the uploaded PDF:\n\n{state.get('pdf_text','')}"
    response = model.generate_content(prompt)
    ai_text = response.text if response else "No response"
    # print(f"\nAI raw output:\n{ai_text}")

    # Parse the AI output text into JSON/dict
    resume_json = parse_ai_json(ai_text)
    if resume_json:
        print("\n✅ JSON parsing successful!")
        json.dumps(resume_json, indent=2)

        # Save parsed JSON to file automatically
        try:
            with open("parsed_resume.json", "w", encoding="utf-8") as f:
                json.dump(resume_json, f, indent=2, ensure_ascii=False)
            print("✅ JSON saved to 'parsed_resume.json'")
        except Exception as e:
            print(f"⚠️ Error saving JSON file: {e}")
        
    else:
        print("\n⚠️ Failed to parse AI output as JSON.")

    return state

graph = StateGraph(AgentState)
graph.add_node("parse", process)
graph.add_edge(START, "parse")
graph.add_edge("parse", END)
agent = graph.compile()

# Save the state graph as a PNG file for visualization (since no Jupyter display)
try:
    graph_image_bytes = agent.get_graph().draw_mermaid_png()
    with open("state_graph.png", "wb") as img_file:
        img_file.write(graph_image_bytes)
    print("✅ State graph saved as 'state_graph.png'")
except Exception as e:
    print(f"⚠️ Could not save state graph image: {e}")

# ==============================
# 4. PDF Text Extraction Function
# ==============================
def extract_pdf_text_from_file(filepath):
    try:
        with open(filepath, "rb") as f:
            reader = PdfReader(f)
            full_text = ""
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + f"\n\n--- End of Page {i+1} ---\n\n"
        return full_text
    except Exception as e:
        print(f"Error reading PDF file: {e}")
        sys.exit(1)

# ==============================
# 5. Loading animation function
# ==============================
def loading_animation(stop_event):
    animation = ['   ', '.  ', '.. ', '...']
    idx = 0
    while not stop_event.is_set():
        print(f'\r🤖 Running AI Agent{animation[idx]}', end='', flush=True)
        idx = (idx + 1) % len(animation)
        time.sleep(0.5)
    # Clear line and print done message
    print('\r🤖 Running AI Agent... done!   ')

# ==============================
# 6. Main CLI logic
# ==============================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse.py path_to_pdf.pdf")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"📄 Extracting text from PDF: {pdf_path}")
    pdf_text = extract_pdf_text_from_file(pdf_path)
    print("✅ Extraction Complete!")

    # Prepare initial agent state with extracted PDF text
    agent_state = {"messages": [], "pdf_text": pdf_text}

    # Start loading animation thread
    stop_event = threading.Event()
    thread = threading.Thread(target=loading_animation, args=(stop_event,))
    thread.start()

    # Run the agent
    try:
        agent.invoke(agent_state)
    except Exception:
        print("\nError running AI Agent:")
        traceback.print_exc()

    # Stop the loading animation
    stop_event.set()
    thread.join()
