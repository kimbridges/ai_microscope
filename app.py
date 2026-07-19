import streamlit as st
import base64
import time
import cv2
import numpy as np
from PIL import Image
import os
from streamlit_image_coordinates import streamlit_image_coordinates

import streamlit as st
import base64
import requests

def trigger_dynamic_audio_feedback(text_script):
    """
    Sends the generated AI text response to the ElevenLabs API,
    synthesizes speech on the fly, and injects the raw binary bytes
    into a hidden, auto-playing HTML5 audio element.
    """
    # 1. Retrieve the secure API key from Streamlit's secrets vault
    if "ELEVENLABS_API_KEY" not in st.secrets:
        st.error("Missing ELEVENLABS_API_KEY in Streamlit Secrets.")
        return
        
    api_key = st.secrets["ELEVENLABS_API_KEY"]
    
    # 2. Configure the ElevenLabs endpoint 
    # Using 'Rachel' voice (21m00Tcm4TlvDq8ikWAM) as a clear default mentor voice
    voice_id = "21m00Tcm4TlvDq8ikWAM"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key
    }
    
    data = {
        "text": text_script,
        "model_id": "eleven_flash_v2_5", # Low-latency optimized flash model
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        # 3. Fire the request to ElevenLabs
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            # 4. Convert the raw mp3 binary stream straight into base64 bytes
            audio_base64 = base64.b64encode(response.content).decode("utf-8")
            
            audio_html = f"""
                <audio autoplay style="display:none;">
                    <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
                </audio>
            """
            st.components.v1.html(audio_html, height=0, width=0)
        else:
            st.error(f"ElevenLabs API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        st.error(f"Failed to connect to ElevenLabs TTS pipeline: {str(e)}")

# --- 1. PAGE CONFIGURATION & INITIAL STATE ---
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

# 🔄 TELEMETRY HISTORY TRACKING INITIALIZATION
if "telemetry_log" not in st.session_state:
    st.session_state.telemetry_log = [] # Stores dicts: {'action': str, 'layer': str, 'timestamp': float}
if "last_action_time" not in st.session_state:
    st.session_state.last_action_time = time.time()

# --- 2. THE DUAL-IMAGE BOTANICAL ENGINE ---
def load_microscope_assets():
    repo_files = os.listdir(".")
    
    leaf_file = None
    for f in ["leaf_section.jpg", "leaf_section.jpeg", "leaf_section.JPG", "leaf_section.PNG"]:
        if f in repo_files:
            leaf_file = f
            break
            
    mask_file = None
    for f in ["color_layer.png", "color_layer.PNG", "color_layer.jpg", "color_layer.jpeg"]:
        if f in repo_files:
            mask_file = f
            break

    if not leaf_file or not mask_file:
        return None, None, "⚠️ Missing leaf_section.jpg or color_layer.png in GitHub root."

    try:
        leaf_img = np.array(Image.open(leaf_file))
        raw_mask = np.array(Image.open(mask_file))
        
        h, w, _ = leaf_img.shape
        aligned_mask = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        
        return leaf_img, aligned_mask, f"🎯 **System Live:** Spatial grids matched successfully at {w}x{h} pixels."
    except Exception as e:
        return None, None, f"❌ Error initializing alignment engine: {str(e)}"

leaf_img, mask_img, status_msg = load_microscope_assets()

# --- 3. CORE 1989 COLOR LABELER CONFIGURATION ---
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
    distances = {}
    for tissue_name, anchor_rgb in COLOR_ANCHORS.items():
        dist = np.linalg.norm(np.array(rgb_pixel) - np.array(anchor_rgb))
        distances[tissue_name] = dist
    return min(distances, key=distances.get)

# --- 4. DYNAMIC RENDERING LENSES ---
def apply_lens(img, lens_type):
    if lens_type == "Wall Density Profile (High Contrast)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTOP_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    
    elif lens_type == "Geometric Borders (Outline Map)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        inverted = cv2.bitwise_not(edges)
        return cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
    
    return img

# --- 5. VISUAL INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)
st.markdown("---")

if leaf_img is None or mask_img is None:
    st.error("Please verify assets are pushed inside your GitHub repo root.")
else:
    h, w, _ = leaf_img.shape

    if st.session_state.x_stage == -1 or st.session_state.y_stage == -1:
        st.session_state.x_stage = int(w / 2)
        st.session_state.y_stage = int(h / 2)

    if st.session_state.pivot_triggered:
        col_view, col_ctrl, col_pivot = st.columns([4.5, 3.5, 3])
    else:
        col_view, col_ctrl, col_pivot = st.columns([5.5, 3.5, 0.1])

    # --- PASS 1: CONTROL DECK (CENTER COLUMN) ---
    with col_ctrl:
        st.write("### 🎛️ Microscope Bench Controls")
        
        objective_lens = st.selectbox(
            "🔄 Rotate Microscope Objective Turret:",
            options=["4x (Scanning Objective)", "10x (Low Power Objective)", "40x (High Power Objective)"],
            index=1
        )
        
        zoom_map = {"4x (Scanning Objective)": 1.0, "10x (Low Power Objective)": 2.2, "40x (High Power Objective)": 5.0}
        zoom = zoom_map[objective_lens]
        crop_size = int(min(h, w) / zoom)
        
        half_crop = int(crop_size / 2)
        y_min, y_max = half_crop, h - half_crop
        x_min, x_max = half_crop, w - half_crop
        
        st.session_state.y_stage = max(y_min, min(st.session_state.y_stage, y_max))
        st.session_state.x_stage = max(x_min, min(st.session_state.x_stage, x_max))
        
        # Overview Minimap Controller
        st.markdown("**🗺️ Specimen Overview Map (Click to re-center):**")
        map_canvas = leaf_img.copy()
        cv2.rectangle(map_canvas, (st.session_state.x_stage - half_crop, st.session_state.y_stage - half_crop), 
                      (st.session_state.x_stage + half_crop, st.session_state.y_stage + half_crop), (230, 40, 40), 6)
        cv2.circle(map_canvas, (st.session_state.x_stage, st.session_state.y_stage), 12, (230, 40, 40), -1)
        
        thumb_w = 400
        thumb_h = int(h * (thumb_w / w))
        map_thumb = cv2.resize(map_canvas, (thumb_w, thumb_h))
        
        click_data = streamlit_image_coordinates(map_thumb, key="macro_map_click")
        if click_data:
            calculated_x = int((click_data["x"] / thumb_w) * w)
            calculated_y = int((click_data["y"] / thumb_h) * h)
            if calculated_x != st.session_state.x_stage or calculated_y != st.session_state.y_stage:
                st.session_state.x_stage = max(x_min, min(calculated_x, x_max))
                st.session_state.y_stage = max(y_min, min(calculated_y, y_max))
                
                # 🔄 TELEMETRY LINK 1: Log Navigation Event
                nav_rgb = mask_img[st.session_state.y_stage, st.session_state.x_stage][:3]
                nav_layer = identify_tissue_by_color(nav_rgb)
                st.session_state.telemetry_log.append({
                    "action": "Navigate Map",
                    "layer": nav_layer,
                    "timestamp": time.time()
                })
                st.session_state.last_action_time = time.time()
                
                trigger_spoken_feedback("trivial_test.mp3")
                st.date_index = time.time()
                st.rerun()

        st.caption(f"📍 Target Anchor Coordinate: ({st.session_state.x_stage}, {st.session_state.y_stage})")

        if len(st.session_state.unlocked_tools) > 1:
            st.session_state.active_lens = st.radio("🛠️ Lens Filter Select:", options=st.session_state.unlocked_tools, horizontal=True)
            
        # SUBMIT RESPONSE INTERACTION
        st.markdown("---")
        if st.button("🎯 Submit Center Crosshair Target", type="primary", use_container_width=True):
            trigger_spoken_feedback("trivial_test.mp3")
            
            sampled_rgb = mask_img[st.session_state.y_stage, st.session_state.x_stage][:3]
            detected_layer = identify_tissue_by_color(sampled_rgb)
            
            # 🔄 TELEMETRY LINK 2: Log Submission Event
            st.session_state.telemetry_log.append({
                "action": "Submit Target",
                "layer": detected_layer,
                "timestamp": time.time()
            })
            st.session_state.last_action_time = time.time()
            
            if detected_layer == "spongy mesophyll":
                st.session_state.target_found = True
                st.success("🎉 **Correct Interpretation!** Your crosshair target is centered inside the loose Spongy Mesophyll tissue layer.")
            elif detected_layer == "cell wall boundary line":
                st.warning("🧐 **Boundary Hit:** Your target crosshair is touching a dark cell wall line. Click slightly inside a cell interior chamber to submit.")
            elif detected_layer == "intercellular space / background":
                st.info("💨 **Atmospheric Space Hit:** You are targeting an empty intercellular air pocket. Use the overview map to acquire a distinct cell body.")
            else:
                st.error(f"❌ **Tissue Misalignment:** Target is sitting inside the **{detected_layer.upper()}** layer instead. Click the low-power zone below the palisade columns.")

        # --- OPTIONAL EXPANDABLE CHASSIS FOR ADMIN/DIAGNOSTIC TOOLS ---
        st.markdown("---")
        with st.expander("🛠️ Developer / Alignment Debug Tools", expanded=False):
            overlay_opacity = st.slider("Map Overlay Opacity (Alpha Blend)", min_value=0, max_value=100, value=0, step=5)
            st.caption("💡 *Slide past 0% to bleed your color interpretation layout directly over the microscope window to verify matching coordinates.*")
            
            # 🔄 TELEMETRY DIAGNOSTIC DISPLAY
            st.markdown("---")
            st.write("**Live Telemetry History (Last 4 Actions):**")
            if st.session_state.telemetry_log:
                for entry in st.session_state.telemetry_log[-4:]:
                    st.text(f"⏱️ {time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))} | {entry['action']} -> {entry['layer']}")
            else:
                st.text("No history recorded yet. Click the map to populate.")
            
            st.markdown("---")
            st.write("*Simulate Student Telemetry Signals:*")
            if st.button("Trigger 90-Sec Stall Warning", use_container_width=True):
                st.session_state.stall_time = 95
                if not st.session_state.target_found: 
                    st.session_state.pivot_triggered = True
                    st.rerun()

    # --- PASS 2: MICROSCOPE VIEWPORT WITH OPTIONAL OVERLAY BLENDING (LEFT) ---
    with col_view:
        st.write("### 🔬 Microscope Viewport")
        
        y1, y2 = st.session_state.y_stage - half_crop, st.session_state.y_stage + half_crop
        x1, x2 = st.session_state.x_stage - half_crop, st.session_state.x_stage + half_crop
        
        cropped_img = leaf_img[y1:y2, x1:x2]
        cropped_mask = mask_img[y1:y2, x1:x2]
        processed_img = apply_lens(cropped_img, st.session_state.active_lens).copy()
        
        if overlay_opacity > 0:
            alpha = (100 - overlay_opacity) / 100.0
            beta = overlay_opacity / 100.0
            processed_img = cv2.addWeighted(processed_img, alpha, cropped_mask[:, :, :3], beta, 0)
        
        vh, vw, _ = processed_img.shape
        cv2.drawMarker(processed_img, (int(vw / 2), int(vh / 2)), (240, 50, 50), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        
        st.image(processed_img, use_container_width=True)
        st.caption("🔬 *Viewport Reticle Active: The red crosshair marks your absolute coordinate submission center point.*")

    # --- PASS 3: THE SOCRATIC PIVOT (RIGHT) ---
    if st.session_state.pivot_triggered and not st.session_state.target_found:
        with col_pivot:
            st.error("🤖 AI Microscope Co-Pilot Intervening")
            st.info(
                "🗣️ **Audio Hint Broadcast:**\n\n"
                "\"I might not have highlighted the structural map well enough for this slide. "
                "We can pull up the gas exchange module here to see how these cells cooperate with air spaces, "
                "or I can give you a direct visual clue. What is your preference?\""
            )
            
            choice = st.radio("Choose resolution path:", ["Select an option...", "Open Visual Diagnostic Palette", "Get Direct Structural Clue"])
            
            if choice == "Get Direct Structural Clue":
                st.warning("💡 **Clue:** Look directly below the tightly packed, bright green vertical columns (Palisade Layer). The target tissue consists of pale green, rounded, loosely packed cells.")
            
            elif choice == "Open Visual Diagnostic Palette":
                st.success("🔓 Alternative Visual Toolkit Unlocked")
                st.session_state.unlocked_tools = ["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"]
                st.session_state.active_lens = st.selectbox("Select alternative lens filter profile:", options=st.session_state.unlocked_tools)
                
                if st.button("Close Palette & Lock Tray", use_container_width=True):
                    st.session_state.pivot_triggered = False; st.rerun()
