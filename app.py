import streamlit as st
import base64
import time
import cv2
import numpy as np
from PIL import Image
import os
import requests
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 1. DYNAMIC GEMINI TEXT GENERATOR WITH ADVANCED VARIABILITY ---
def generate_ai_commentary(action_type, tissue_layer):
    """
    Calls the Gemini 1.5 Flash API to generate a brief, unique, 
    non-canned comment based on user interaction and history.
    """
    if "GEMINI_API_KEY" not in st.secrets:
        return f"Telemetry notice: {action_type} inside the {tissue_layer}."
        
    api_key = st.secrets["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    # Pull recent moves to give Gemini conversational awareness
    history_context = ""
    if "telemetry_log" in st.session_state and st.session_state.telemetry_log:
        recent = st.session_state.telemetry_log[-3:]
        history_context = " then ".join([f"{h['action']} on {h['layer']}" for h in recent])
    
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
        "contents": [{"parts": [{"text": prompt}]}]
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            result = response.json()
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            return ai_text.replace('"', '').replace('"', '')
    except Exception:
        pass
        
    random_tokens = ["Observing", "Analyzing", "Gliding over", "Inspecting"]
    token = random_tokens[int(time.time()) % len(random_tokens)]
    return f"{token} the {tissue_layer} region."

# --- 2. DYNAMIC ELEVENLABS AUDIO FEEDBACK GENERATOR ---
def play_queued_audio():
    """
    Checks if there is a pending audio string in the state queue.
    If found, synthesizes it via ElevenLabs, plays it, and instantly deletes it
    to prevent infinite Streamlit rerun playback loops.
    """
    if "active_audio" not in st.session_state or not st.session_state.active_audio:
        return

    text_script = st.session_state.active_audio
    
    # IMMEDIATELY FLUSH THE QUEUE so next rerun finds nothing
    st.session_state.active_audio = None

    if "ELEVENLABS_API_KEY" not in st.secrets:
        st.error("Missing ELEVENLABS_API_KEY in Streamlit Secrets.")
        return
        
    api_key = st.secrets["ELEVENLABS_API_KEY"]
    voice_id = "21m00Tcm4TlvDq8ikWAM" # Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text_script,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            audio_base64 = base64.b64encode(response.content).decode("utf-8")
            audio_html = f"""
                <audio autoplay style="display:none;">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
            """
            st.components.v1.html(audio_html, height=0, width=0)
    except Exception:
        pass

# --- 3. PAGE CONFIGURATION & INITIAL STATE ---
st.set_page_config(layout="wide", page_title="AI Microscope Dashboard")

if "stall_time" not in st.session_state:
    st.session_state.stall_time = 0
if "target_found" not in st.session_state:
    st.session_state.target_found = False
if "pivot_triggered" not in st.session_state:
    st.session_state.pivot_triggered = False
if "active_lens" not in st.session_state:
    st.session_state.active_lens = "Standard View"
if "unlocked_tools" not in st.session_state:
    st.session_state.unlocked_tools = ["Standard View"]

if "x_stage" not in st.session_state:
    st.session_state.x_stage = -1
if "y_stage" not in st.session_state:
    st.session_state.y_stage = -1

if "telemetry_log" not in st.session_state:
    st.session_state.telemetry_log = [] 
if "last_action_time" not in st.session_state:
    st.session_state.last_action_time = time.time()
if "active_audio" not in st.session_state:
    st.session_state.active_audio = None

# --- 4. THE DUAL-IMAGE BOTANICAL ENGINE ---
def load_microscope_assets():
    repo_files = os.listdir(".")
    leaf_file = next((f for f in ["leaf_section.jpg", "leaf_section.jpeg", "leaf_section.JPG", "leaf_section.PNG"] if f in repo_files), None)
    mask_file = next((f for f in ["color_layer.png", "color_layer.PNG", "color_layer.jpg", "color_layer.jpeg"] if f in repo_files), None)

    if not leaf_file or not mask_file:
        return None, None, "⚠️ Missing assets in GitHub root."

    try:
        leaf_img = np.array(Image.open(leaf_file))
        raw_mask = np.array(Image.open(mask_file))
        h, w, _ = leaf_img.shape
        aligned_mask = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return leaf_img, aligned_mask, f"🎯 **System Live:** {w}x{h} pixels."
    except Exception as e:
        return None, None, f"❌ Engine error: {str(e)}"

leaf_img, mask_img, status_msg = load_microscope_assets()

# --- 5. CORE 1989 COLOR LABELER CONFIGURATION ---
COLOR_ANCHORS = {
    "upper epidermis": [247, 197, 40],
    "palisade mesophyll": [32, 146, 20],
    "spongy mesophyll": [177, 226, 117],
    "midrib ground-tissue parenchyma": [211, 241, 197],
    "bundle sheath and vascular-associated tissue": [232, 141, 17],
    "xylem": [234, 36, 35],
    "phloem": [16, 98, 227],
    "sclerenchyma/collenchyma support tissue": [144, 95, 175],
    "lower epidermis": [150, 100, 40],
    "cuticle": [160, 158, 161],
    "intercellular space / background": [254, 254, 254],
    "cell wall boundary line": [0, 0, 0]
}

def identify_tissue_by_color(rgb_pixel):
    distances = {name: np.linalg.norm(np.array(rgb_pixel) - np.array(anchor)) for name, anchor in COLOR_ANCHORS.items()}
    return min(distances, key=distances.get)

# --- 6. DYNAMIC RENDERING LENSES ---
def apply_lens(img, lens_type):
    if lens_type == "Wall Density Profile (High Contrast)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    elif lens_type == "Geometric Borders (Outline Map)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        inverted = cv2.bitwise_not(edges)
        return cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
    return img

# --- 7. VISUAL INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)
st.markdown("---")

if leaf_img is None or mask_img is None:
    st.error("Please verify assets are pushed inside your GitHub repo root.")
else:
    h, w, _ = leaf_img.shape

    if st.session_state.x_stage == -1 or st.session_state.y_stage == -1:
        st.session_state.x_stage, st.session_state.y_stage = int(w / 2), int(h / 2)

    col_view, col_ctrl, col_pivot = st.columns([4.5, 3.5, 3]) if st.session_state.pivot_triggered else st.columns([5.5, 3.5, 0.1])

    with col_ctrl:
        st.write("### 🎛️ Microscope Bench Controls")
        
        objective_lens = st.selectbox(
            "🔄 Rotate Microscope Objective Turret:",
            options=["4x (Scanning Objective)", "10x (Low Power Objective)", "40x (High Power Objective)"],
            index=1
        )
        
        zoom = {"4x (Scanning Objective)": 1.0, "10x (Low Power Objective)": 2.2, "40x (High Power Objective)": 5.0}[objective_lens]
        crop_size = int(min(h, w) / zoom)
        half_crop = int(crop_size / 2)
        
        st.session_state.y_stage = max(half_crop, min(st.session_state.y_stage, h - half_crop))
        st.session_state.x_stage = max(half_crop, min(st.session_state.x_stage, w - half_crop))
        
        st.markdown("**🗺️ Specimen Overview Map (Click to re-center):**")
        map_canvas = leaf_img.copy()
        cv2.rectangle(map_canvas, (st.session_state.x_stage - half_crop, st.session_state.y_stage - half_crop), 
                      (st.session_state.x_stage + half_crop, st.session_state.y_stage + half_crop), (230, 40, 40), 6)
        
        thumb_w = 400
        thumb_h = int(h * (thumb_w / w))
        map_thumb = cv2.resize(map_canvas, (thumb_w, thumb_h))
        
        click_data = streamlit_image_coordinates(map_thumb, key="macro_map_click")
        if click_data:
            calculated_x = int((click_data["x"] / thumb_w) * w)
            calculated_y = int((click_data["y"] / thumb_h) * h)
            if calculated_x != st.session_state.x_stage or calculated_y != st.session_state.y_stage:
                st.session_state.x_stage = max(half_crop, min(calculated_x, w - half_crop))
                st.session_state.y_stage = max(half_crop, min(calculated_y, h - half_crop))
                
                nav_layer = identify_tissue_by_color(mask_img[st.session_state.y_stage, st.session_state.x_stage][:3])
                st.session_state.telemetry_log.append({"action": "Navigate Map", "layer": nav_layer, "timestamp": time.time()})
                st.session_state.last_action_time = time.time()
                
                # 🧠 Ask Gemini, then drop into single-use playback queue
                st.session_state.active_audio = generate_ai_commentary(action_type="Navigation", tissue_layer=nav_layer)
                
                st.date_index = time.time()
                st.rerun()

        st.caption(f"📍 Target Anchor Coordinate: ({st.session_state.x_stage}, {st.session_state.y_stage})")

        if len(st.session_state.unlocked_tools) > 1:
            st.session_state.active_lens = st.radio("🛠️ Lens Filter Select:", options=st.session_state.unlocked_tools, horizontal=True)
            
        st.markdown("---")
        if st.button("🎯 Submit Center Crosshair Target", type="primary", use_container_width=True):
            sampled_rgb = mask_img[st.session_state.y_stage, st.session_state.x_stage][:3]
            detected_layer = identify_tissue_by_color(sampled_rgb)
            
            st.session_state.telemetry_log.append({"action": "Submit Target", "layer": detected_layer, "timestamp": time.time()})
            st.session_state.last_action_time = time.time()
            
            # 🧠 Ask Gemini, then drop into single-use playback queue
            st.session_state.active_audio = generate_ai_commentary(action_type="Final Answer Submission", tissue_layer=detected_layer)
            
            if detected_layer == "spongy mesophyll":
                st.session_state.target_found = True
                st.success("🎉 **Correct Interpretation!** Located Spongy Mesophyll.")
            elif detected_layer == "cell wall boundary line":
                st.warning("🧐 **Boundary Hit:** Touching a cell wall line.")
            elif detected_layer == "intercellular space / background":
                st.info("💨 **Atmospheric Space Hit:** Empty air pocket.")
            else:
                st.error(f"❌ **Tissue Misalignment:** Target inside the {detected_layer.upper()}.")

        st.markdown("---")
        with st.expander("🛠️ Developer / Alignment Debug Tools", expanded=False):
            overlay_opacity = st.slider("Map Overlay Opacity (Alpha Blend)", min_value=0, max_value=100, value=0, step=5)
            st.markdown("---")
            st.write("**Live Telemetry History (Last 4 Actions):**")
            if st.session_state.telemetry_log:
                for entry in st.session_state.telemetry_log[-4:]:
                    st.text(f"⏱️ {time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))} | {entry['action']} -> {entry['layer']}")

    with col_view:
        st.write("### 🔬 Microscope Viewport")
        y1, y2 = st.session_state.y_stage - half_crop, st.session_state.y_stage + half_crop
        x1, x2 = st.session_state.x_stage - half_crop, st.session_state.x_stage + half_crop
        
        cropped_img = leaf_img[y1:y2, x1:x2]
        cropped_mask = mask_img[y1:y2, x1:x2]
        processed_img = apply_lens(cropped_img, st.session_state.active_lens).copy()
        
        if overlay_opacity > 0:
            alpha, beta = (100 - overlay_opacity) / 100.0, overlay_opacity / 100.0
            processed_img = cv2.addWeighted(processed_img, alpha, cropped_mask[:, :, :3], beta, 0)
        
        vh, vw, _ = processed_img.shape
        cv2.drawMarker(processed_img, (int(vw / 2), int(vh / 2)), (240, 50, 50), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        st.image(processed_img, use_container_width=True)

    if st.session_state.pivot_triggered and not st.session_state.target_found:
        with col_pivot:
            st.error("🤖 AI Microscope Co-Pilot Intervening")

    # 🛑 THE CIRCUIT BREAKER: Execute audio playback one time, then immediately zero it out
    play_queued_audio()
