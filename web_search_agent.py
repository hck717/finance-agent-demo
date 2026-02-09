# python3 -m venv venv
# source venv/bin/activate
# pip install streamlit requests
# streamlit run web_search_agent.py


import streamlit as st
import requests

# --- Configuration ---
API_URL = "https://api.perplexity.ai/chat/completions"

# --- Page Config ---
st.set_page_config(
    page_title="Financial Analyst AI",
    page_icon="📈",
    layout="wide"  # Changed to 'wide' for better table viewing
)

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Analyst Settings")
    
    # 1. API Key Input
    api_key = st.text_input(
        "Perplexity API Key", 
        type="password", 
        help="Required: Get key from https://www.perplexity.ai/settings/api"
    )
    
    # 2. Model Selection
    model = st.selectbox(
        "Select Model",
        ["sonar", "sonar-reasoning"],
        index=0,
        help="Sonar: Standard search (Faster). Sonar Reasoning: Deep reasoning (Better for complex analysis)."
    )
    
    st.info("💡 **Tip**: 'Sonar Reasoning' is recommended for deep-dive financial reports.")

    st.markdown("---")
    if st.button("Clear Research History"):
        st.session_state.messages = []
        st.rerun()

# --- Functions ---
def query_perplexity(messages, key, model_name):
    """Sends the conversation history to Perplexity API"""
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": model_name,
        "messages": messages,
        "return_citations": True 
    }

    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e)}

# --- Main Interface ---
st.title("📈 Fundamental Analyst AI")
st.markdown("##### *Real-time Equity Research Assistant for Portfolio Managers*")

# 1. Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# 2. Display Chat History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        # If citations exist, display them in an expander
        if "citations" in msg and msg["citations"]:
            with st.expander("📚 Verified Sources"):
                for i, citation in enumerate(msg["citations"], 1):
                    st.markdown(f"{i}. {citation}")

# 3. Handle User Input
if prompt := st.chat_input("Enter ticker or research query (e.g., 'Analyze Apple's latest 10-K risks')..."):
    
    # Check for API Key
    if not api_key:
        st.error("⚠️ Please enter your API Key in the sidebar to proceed.")
        st.stop()

    # Add User Message to History
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate Assistant Response
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        citations = []

        with st.spinner("Analyzing web data..."):
            # Prepare messages (User history)
            api_messages = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.messages
            ]
            
            # --- PROFESSIONAL FINANCE SYSTEM PROMPT ---
            system_instruction = """
            You are a Senior Equity Research Associate assisting a Portfolio Manager. 
            Your goal is to provide high-precision fundamental analysis based on real-time web search.

            ### EXECUTION GUIDELINES:
            1. **Sources**: STRICTLY prioritize official Investor Relations (IR), SEC/Regulatory filings (10-K/10-Q), and Tier-1 financial news (Bloomberg, Reuters, FT, WSJ). Ignore generic blogs.
            2. **Format**: Minimize text. Use Markdown tables for financial data. 
            3. **Tone**: Objective, professional, and direct. No conversational filler (e.g., "Here is what I found").

            ### OUTPUT STRUCTURE:
            - **Executive Summary**: High-level thesis/status (max 50 words).
            - **Key Fundamentals**: Markdown table (Required for: Revenue, EBITDA, Margins, EPS, YoY growth).
            - **Corporate Developments**: Strategic updates, M&A, or leadership changes.
            - **Risks/Catalysts**: Bullet points only.
            """
            
            # Insert System Prompt at the beginning
            api_messages.insert(0, {
                "role": "system", 
                "content": system_instruction
            })

            # Call API
            result = query_perplexity(api_messages, api_key, model)
            
            if "error" in result:
                st.error(f"API Error: {result['error']}")
            else:
                # Extract content
                full_response = result['choices'][0]['message']['content']
                citations = result.get('citations', [])

                # Display Answer
                message_placeholder.markdown(full_response)
                
                # Display Citations (if any)
                if citations:
                    with st.expander("📚 Verified Sources"):
                        for i, citation in enumerate(citations, 1):
                            st.markdown(f"[{i}] {citation}")

        # Add Assistant Message to History (including citations)
        st.session_state.messages.append({
            "role": "assistant", 
            "content": full_response,
            "citations": citations
        })
