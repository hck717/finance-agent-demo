# python3 -m venv venv
# source venv/bin/activate
# pip install tavily-python ollama streamlit
# streamlit run local_web_search.py 



import streamlit as st
import ollama
from tavily import TavilyClient

# --- Page Config ---
st.set_page_config(
    page_title="Local Qwen Analyst",
    page_icon="🏠",
    layout="wide"
)

# --- Sidebar: Settings ---
with st.sidebar:
    st.header("⚙️ Local Agent Settings")
    
    # 1. Tavily API Key (Required for web search)
    tavily_key = st.text_input(
        "Tavily API Key", 
        type="password", 
        help="Get one at https://tavily.com"
    )
    
    # 2. Local Model Selection
    # Dynamically fetch available local models
    try:
        models_info = ollama.list()
        # Handle different response formats (newer Ollama versions return objects)
        model_names = [m['model'] for m in models_info['models']]
    except Exception as e:
        st.warning("Could not connect to Ollama. Make sure it's running!")
        model_names = ["qwen2.5:7b"] # Fallback

    selected_model = st.selectbox(
        "Local LLM",
        model_names,
        index=model_names.index("qwen2.5:7b") if "qwen2.5:7b" in model_names else 0
    )
    
    st.markdown("---")
    st.markdown("### 🟢 Status")
    if tavily_key:
        st.success("Tavily: Ready")
    else:
        st.error("Tavily: Missing Key")
        
    st.caption(f"Model: `{selected_model}`")

# --- Functions ---

def search_web(query, key):
    """
    Uses Tavily to search the web and return context optimized for LLMs.
    """
    try:
        tavily = TavilyClient(api_key=key)
        # 'search_depth="advanced"' gives more detailed results suitable for finance
        response = tavily.search(
            query=query, 
            search_depth="advanced", 
            max_results=5,
            include_domains=[] # Optional: Filter for finance sites like bloomberg.com if needed
        )
        
        # Format context for the LLM
        context_text = ""
        citations = []
        for result in response.get('results', []):
            context_text += f"\n---\nTitle: {result['title']}\nURL: {result['url']}\nContent: {result['content']}\n"
            citations.append(f"[{result['title']}]({result['url']})")
            
        return context_text, citations
    except Exception as e:
        return None, [f"Search Error: {str(e)}"]

def run_local_analyst(query, search_context, model):
    """
    Sends the Search Context + User Query to the Local Ollama Model.
    """
    
    # The Senior Analyst Prompt
    system_prompt = """
    You are a Senior Financial Analyst. 
    You have been provided with raw search results from the web (Context).
    
    Your Job:
    1. Synthesize the search results to answer the user's question.
    2. Focus on hard numbers: Revenue, Margins, Growth Rates, Guidance.
    3. Be skeptical: If sources conflict, note the discrepancy.
    4. Format: Use Markdown tables for data. Keep text concise.
    
    DISCLAIMER: Do not make up facts. If the answer is not in the Context, state that.
    """
    
    final_prompt = f"""
    ### CONTEXT FROM WEB SEARCH:
    {search_context}
    
    ### USER QUESTION:
    {query}
    
    ### YOUR ANALYSIS:
    """

    stream = ollama.chat(
        model=model,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': final_prompt}
        ],
        stream=True,
    )
    return stream

# --- Main Interface ---
st.title("🏠 Local Qwen + Tavily Analyst")
st.markdown("##### *Hybrid Agent: Cloud Search (Tavily) + Local Reasoning (Qwen)*")

# Initialize Chat History
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display History
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "citations" in msg and msg["citations"]:
            with st.expander("📚 Sources"):
                for c in msg["citations"]:
                    st.markdown(f"- {c}")

# Input Area
if prompt := st.chat_input("Research ticker or topic (e.g., 'Google Q4 2025 earnings analysis')..."):
    
    if not tavily_key:
        st.error("Please enter your Tavily API Key in the sidebar.")
        st.stop()

    # 1. User Message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. Assistant Process
    with st.chat_message("assistant"):
        status_box = st.status("🕵️ Agent Working...", expanded=True)
        
        # Step A: Search
        status_box.write("Searching the web (Tavily)...")
        context, citations = search_web(prompt, tavily_key)
        
        if not context:
            status_box.update(label="❌ Search Failed", state="error")
            st.error("Could not retrieve search results.")
            st.stop()
            
        status_box.write("Context retrieved. Analyzing with local Qwen model...")
        
        # Step B: Generate (Streaming)
        response_placeholder = st.empty()
        full_response = ""
        
        # Stream the response from Ollama
        stream = run_local_analyst(prompt, context, selected_model)
        
        for chunk in stream:
            content = chunk['message']['content']
            full_response += content
            response_placeholder.markdown(full_response + "▌")
            
        response_placeholder.markdown(full_response)
        
        # Step C: Finish
        status_box.update(label="✅ Analysis Complete", state="complete", expanded=False)
        
        # Show Citations
        if citations:
            with st.expander("📚 Sources Used"):
                for c in citations:
                    st.markdown(f"- {c}")

    # 3. Save to History
    st.session_state.messages.append({
        "role": "assistant", 
        "content": full_response,
        "citations": citations
    })
