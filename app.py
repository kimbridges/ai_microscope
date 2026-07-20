# --- DYNAMIC GEMINI TEXT GENERATOR WITH ADVANCED VARIABILITY ---
def generate_ai_commentary(action_type, tissue_layer):
    """
    Calls the Gemini 1.5 Flash API to generate a brief, unique, 
    non-canned comment based on user interaction and history.
    """
    if "GEMINI_API_KEY" not in st.secrets:
        return f"Telemetry notice: {action_type} inside the {tissue_layer}."
        
    api_key = st.secrets["GEMINI_API_KEY"]
    
    # Updated direct v1 endpoint for 1.5-flash
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Pull recent moves to give Gemini conversational awareness
    history_context = ""
    if "telemetry_log" in st.session_state and st.session_state.telemetry_log:
        recent = st.session_state.telemetry_log[-3:]
        history_context = " then ".join([f"{h['action']} on {h['layer']}" for h in recent])
    
    # An aggressive prompt forcing distinct vocabulary, styles, and phrasing
    prompt = f"""
    You are an enthusiastic, spontaneous AI botanical microscope mentor. 
    The student just did a "{action_type}" and landed on the "{tissue_layer}".
    Their recent path: [{history_context}]
    
    Task: Write a single, brief conversational observation (maximum 12 words).
    
    STRICT VARIABILITY RULES:
    1. NEVER start with "Telemetry notice", "You are looking at", or "Navigation inside".
    2. Be spontaneous. Use casual academic phrasing, sudden curiosity, or brief encouragement.
    3. Seamlessly wrap the layer name "{tissue_layer}" into a natural, unique sentence.
    4. Do not repeat your phrasing structure if the history shows they are clicking around.
    """
    
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            result = response.json()
            # Extract text safely from the Google API structure
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            # Clean up any stray quotes the AI might wrap the text in
            return ai_text.replace('"', '').replace('"', '')
        else:
            # If the API key is invalid or rejected, show it on screen for debugging
            st.toast(f"⚠️ Gemini API Status Code: {response.status_code} - {response.text[:50]}")
    except Exception as e:
        st.toast(f"⚠️ Gemini Connection Timeout: {str(e)[:50]}")
        
    # Fallback with minor random injection so it still varies even if network drops
    random_tokens = ["Observing", "Analyzing", "Gliding over", "Inspecting"]
    token = random_tokens[int(time.time()) % len(random_tokens)]
    return f"{token} the {tissue_layer} region."
