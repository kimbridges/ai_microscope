import streamlit as st
import base64
import time
import cv2
import numpy as np
from PIL import Image
import os
import requests
from streamlit_image_coordinates import streamlit_image_coordinates

# --- 0. THE NARRATIVE & ETYMOLOGICAL GROUND-TRUTH REPOSITORY ---
BOTANICAL_LORE = {
    "upper epidermis": {
        "analog": "The Greenhouse Glass",
        "literal_meaning": "Upper Over-Skin (From Greek 'epi' = upon/over, and 'derma' = skin)",
        "narrative": (
            "Think of the upper epidermis as the transparent glass roof of a massive solar factory. "
            "Its primary job is to let maximum sunlight stream down into the machinery below while acting "
            "as a secure physical shield against weather, microscopic invaders, and destructive UV rays. "
            "To achieve this, the cells are packed tightly together side-by-side like continuous floor tiles, "
            "and they remain completely clear—containing no green photosynthetic machinery of their own. "
            "It is a pure structural window designed for protection and transparency."
        )
    },
    "cuticle": {
        "analog": "The Pool Liner / Waterproof Seal",
        "literal_meaning": "Little Skin (From Latin 'cuticula')",
        "narrative": (
            "Because the leaf is constantly exposed to dry moving air and baking sunlight, it faces a "
            "constant threat of drying out. To stop water from evaporating right through the roof, the plant "
            "secretes a continuous, clear, waxy sheet across the very top of the epidermis. It behaves "
            "exactly like a heavy-duty pool liner or a clear rubber laminate over a blueprint. Water molecules "
            "cannot easily pierce this hydrophobic wax barrier, forcing the plant's moisture to stay inside "
            "where it can be used for vital metabolic processes."
        )
    },
    "palisade mesophyll": {
        "analog": "The Solar Panel Array",
        "literal_meaning": "The Middle-Leaf Defensive Wall (From Latin 'palus' = stake/post, and Greek 'meso-' = middle, '-phyllon' = leaf)",
        "narrative": (
            "To capture the absolute maximum amount of sunlight entering from above, the plant stands its "
            "cellular machinery straight up on end—like tightly packed columns or defensive wooden stakes driven into "
            "the ground side-by-side. This vertical architecture lets the light pass deeply down through the length "
            "of each cell, packing thousands of green chloroplasts into the prime upper real estate to drive the "
            "engines of photosynthesis without blocking out the lower levels."
        )
    },
    "spongy mesophyll": {
        "analog": "The Ventilation Network / Air Pockets",
        "literal_meaning": "The Middle-Leaf Air-Sponge (From Greek 'spongia' = porous structure, and 'mesophyll' = middle leaf)",
        "narrative": (
            "For a factory to run, it needs an absolute mountain of raw ventilation to exchange carbon dioxide, "
            "oxygen, and water vapor. Instead of packing cells tight like bricks, the plant builds a subterranean cavern, "
            "shifting to loose, chaotic, wildly irregular shapes with massive empty spaces between them. It looks and "
            "acts exactly like a kitchen sponge. This open-air network lets gases drift lazily and safely through "
            "internal atmospheric pathways, brushing against wet, living cell walls where molecular gas exchange happens."
        )
    },
    "xylem": {
        "analog": "The High-Pressure Plumbing Main",
        "literal_meaning": "The Woody Pipeline (From Greek 'xylon' = wood/timber)",
        "narrative": (
            "The plant moves water under extreme negative tension—pulling on a thin microscopic thread of liquid "
            "lifted hundreds of feet from the soil. If you try to drink a thick milkshake through a flimsy paper straw, "
            "the straw instantly collapses under the suction. To beat this physical constraint, xylem cells build heavy, "
            "circular rings reinforced with lignin—the very compound that makes wood rigid. They then deliberately die, "
            "leaving behind hollow, hardened, reinforced pipelines that can withstand immense suction pressure without imploding."
        )
    },
    "phloem": {
        "analog": "The Sugar Transit Conveyor",
        "literal_meaning": "The Bark Packing Line (From Greek 'phloios' = inner bark)",
        "narrative": (
            "Once the solar panels produce rich, energetic sugars, that cargo needs to be exported down "
            "to the roots, stems, and growing fruits. The phloem is the active outbound shipping lane. Unlike "
            "the dead water pipes next to it, phloem conduits are alive, running on delicate osmotic pressure gradients. "
            "It moves a thick, viscous sap through specialized microscopic sieve plates to distribute manufactured fuel."
        )
    },
    "bundle sheath and vascular-associated tissue": {
        "analog": "The Cargo Loading Dock / Security Terminal",
        "literal_meaning": "Vascular Wrapper",
        "narrative": (
            "The fluid pipes carrying water and sugar cannot sit bare and exposed inside the turbulent, "
            "air-filled spaces of the leaf. Instead, the plant encases the plumbing veins inside a tightly "
            "knit protective collar of specialized cells. Think of this as a highly secure cargo loading dock or "
            "customs terminal. Every molecule of water exiting the plumbing, and every molecule of manufactured sugar "
            "entering it, must pass inspection through these gatekeeper cells, which also reinforce the veins against bending."
        )
    },
    "lower epidermis": {
        "analog": "The Secure Utility Vault",
        "literal_meaning": "Lower Under-Skin",
        "narrative": (
            "The bottom floor of the leaf faces less direct scorching sunlight than the roof, making it the "
            "delicate breathing floor. The lower epidermis acts like a secure utility vault floor. It maintains "
            "the physical boundary of the leaf framework but is peppered with hundreds of microscopic, adjustable valve gates. "
            "It keeps the internal architecture contained while managing the air intake system away from the baking heat."
        )
    },
    "intercellular space / background": {
        "analog": "The Ventilation Vaults / Breathing Chambers",
        "literal_meaning": "Between-Cell Voids",
        "narrative": (
            "This isn't empty wasted space—it is a beautifully orchestrated atmospheric cavern. Carbon dioxide "
            "needs room to drift freely around the living cells so it can be absorbed, and oxygen needs a clear pathway "
            "to escape. By leaving massive internal gaps between the irregular cell walls, the plant creates an "
            "internal atmosphere that is constantly humid and rich in gas circulation, acting like complex air ducts."
        )
    },
    "cell wall boundary line": {
        "analog": "The Structural Mortar / Property Lines",
        "literal_meaning": "Cellular Perimeter",
        "narrative": (
            "These dark structural lines are the structural mortar holding the leaf factory together. They provide "
            "the rigid mechanical boundary that shapes each cell and keeps the entire leaf flat and extended toward the light, "
            "preventing structural collapse under gravity."
        )
    },
    "midrib ground-tissue parenchyma": {
        "analog": "The Central Chassis / Bulk Structural Filler",
        "literal_meaning": "Poured-in-Beside Tissue (From Greek 'para' = beside, and 'enchyma' = poured infusion)",
        "narrative": (
            "This is the core packing material and shock absorber surrounding the main structural vein of the leaf. "
            "It forms the central chassis that keeps the primary transport lines stable, functioning as a resilient, "
            "fluid-filled cushion that gives the leaf its foundational bounce and thickness."
        )
    },
    "sclerenchyma/collenchyma support tissue": {
        "analog": "The Reinforced Steel I-Beams",
        "literal_meaning": "Hardened Structural Tissue (From Greek 'skleros' = hard, and 'kolla' = glue)",
        "narrative": (
            "These are the heavy-duty structural reinforcement brackets of the leaf. They are thick, dense clusters "
            "of support cells built specifically to brace the leaf against high winds and torsional strain. They act "
            "exactly like structural steel I-beams or structural rebar welded onto the main chassis."
        )
    }
}

# --- 1. DYNAMIC GEMINI TEXT GENERATOR ---
def generate_ai_commentary(action_type, tissue_layer, target_assignment):
    if "GEMINI_API_KEY" not in st.secrets:
        return f"Telemetry notice: Standing inside the {tissue_layer} region."
        
    api_key = st.secrets["GEMINI_API_KEY"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={api_key}"
    
    goal_lore = BOTANICAL_LORE.get(target_assignment, {"analog": "Target", "narrative": ""})
    current_lore = BOTANICAL_LORE.get(tissue_layer, {"analog": "Unknown Space", "literal_meaning": "Layer", "narrative": ""})
    
    history_list = []
    if "telemetry_log" in st.session_state and st.session_state.telemetry_log:
        for h in st.session_state.telemetry_log[-3:]:
            history_list.append(f"{h['action']} on {h['layer']}")
    history_context = " then ".join(history_list) if history_list else "None yet"
    
    prompt = (
        "You are a private, supportive botanical lab assistant speaking into the student's headphones.\n"
        f"The student's active engineering objective is to locate: {target_assignment} (Analog: {goal_lore['analog']}).\n"
        f"They just clicked coordinates that resolved to this tissue type: {tissue_layer} (Analog: {current_lore['analog']}).\n"
        f"Their recent navigation history: {history_context}\n\n"
        "DETERMINISTIC KNOWLEDGE BASE (Use ONLY these facts to construct observations):\n"
        f"- Current Location Function: {current_lore['narrative']}\n"
        f"- Current Location Etymology/Root: {current_lore['literal_meaning']}\n\n"
        "TASK: Write a natural, brief observation (maximum 18 words) spoken directly to the user's headset.\n\n"
        "STRICT PEDAGOGICAL GUIDELINES:\n"
        "1. NEVER use text phrases like 'Telemetry notice', 'Incorrect', 'Wrong answer', or 'You are looking at'.\n"
        "2. Act as a conversational assistant, not an evaluator.\n"
        "3. If they hit the target, congratulate their spatial deduction naturally using the analogy.\n"
        "4. If they missed, use the 'Current Location Function' or 'Etymology' common-sense analogs to explain what this specific layer achieves mechanically for the plant, then gently steer their attention toward the target."
    )
    
    headers = {"Content-Type": "application/json"}
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=8)
        if response.status_code == 200:
            result = response.json()
            ai_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
            return ai_text.replace('"', '')
    except Exception:
        pass
        
    return f"Inspecting the {current_lore['analog']} structure."

# --- 2. DYNAMIC ELEVENLABS AUDIO FEEDBACK GENERATOR ---
def play_queued_audio():
    if "active_audio" not in st.session_state or not st.session_state.active_audio:
        return
    text_script = st.session_state.active_audio
    st.session_state.active_audio = None

    if "ELEVENLABS_API_KEY" not in st.secrets:
        return
        
    api_key = st.secrets["ELEVENLABS_API_KEY"]
    voice_id = "21m00Tcm4TlvDq8ikWAM" # Rachel
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    
    headers = {"Accept": "audio/mpeg", "Content-Type": "application/json", "xi-api-key": api_key}
    data = {
        "text": text_script,
        "model_id": "eleven_flash_v2_5",
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.8}
    }
    
    try:
        response = requests.post(url, json=data, headers=headers, timeout=10)
        if response.status_code == 200:
            audio_base64 = base64.b64encode(response.content).decode("utf-8")
            audio_html = f'<audio autoplay style="display:none;"><source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3"></audio>'
            st.components.v1.html(audio_html, height=0, width=0)
    except Exception:
        pass

# --- 3. PAGE CONFIGURATION & INITIAL STATE ---
st.set_page_config(layout="centered", page_title="AI Microscope Dashboard")

if "target_found" not in st.session_state:
    st.session_state.target_found = False
if "active_lens" not in st.session_state:
    st.session_state.active_lens = "Standard View"
if "x_stage" not in st.session_state:
    st.session_state.x_stage = -1
if "y_stage" not in st.session_state:
    st.session_state.y_stage = -1
if "telemetry_log" not in st.session_state:
    st.session_state.telemetry_log = [] 
if "active_audio" not in st.session_state:
    st.session_state.active_audio = None

# --- 4. ASSET LOADER ---
def load_microscope_assets():
    repo_files = os.listdir(".")
    leaf_file = next((f for f in ["leaf_section.jpg", "leaf_section.jpeg", "leaf_section.JPG", "leaf_section.PNG"] if f in repo_files), None)
    mask_file = next((f for f in ["color_layer.png", "color_layer.PNG", "color_layer.jpg", "color_layer.jpeg"] if f in repo_files), None)
    if not leaf_file or not mask_file:
        return None, None, "⚠️ Missing assets."
    try:
        leaf_img = np.array(Image.open(leaf_file))
        raw_mask = np.array(Image.open(mask_file))
        h, w, _ = leaf_img.shape
        aligned_mask = cv2.resize(raw_mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return leaf_img, aligned_mask, f"🎯 **System Live:** {w}x{h} pixels."
    except Exception as e:
        return None, None, f"❌ Engine error: {str(e)}"

leaf_img, mask_img, status_msg = load_microscope_assets()

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

# --- 5. SINGLE-CANVAS VERTICAL MOBILE-FIRST LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)
st.markdown("---")

if leaf_img is None or mask_img is None:
    st.error("Please verify assets are pushed inside your GitHub repo root.")
else:
    h, w, _ = leaf_img.shape
    if st.session_state.x_stage == -1 or st.session_state.y_stage == -1:
        st.session_state.x_stage, st.session_state.y_stage = int(w / 2), int(h / 2)

    # --- TOP CONTROLS STACKED VERTICALLY ---
    assignment_options = {k: f"{v['analog']} ({k.title()})" for k, v in BOTANICAL_LORE.items()}
    selected_target_key = st.selectbox(
        "🎯 Select Your Lab Investigation Objective:",
        options=list(assignment_options.keys()),
        format_func=lambda x: assignment_options[x],
        index=2 
    )
    
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        objective_lens = st.selectbox(
            "🔄 Turret Objective:",
            options=["4x (Scanning)", "10x (Low Power)", "40x (High Power)"],
            index=1
        )
    with col_c2:
        lens_mode = st.selectbox(
            "🔬 View Mode:",
            options=["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"],
            index=0
        )
    st.session_state.active_lens = lens_mode

    # Zoom & Crop Math (Locked strictly to uniform scaling factors)
    zoom = {"4x (Scanning)": 1.0, "10x (Low Power)": 2.5, "40x (High Power)": 6.0}[objective_lens]
    crop_size = int(w / zoom)
    half_crop = int(crop_size / 2)
    
    st.session_state.x_stage = max(half_crop, min(st.session_state.x_stage, w - half_crop))
    st.session_state.y_stage = max(half_crop, min(st.session_state.y_stage, h - half_crop))

    # --- SINGLE VIEWPORT CANVAS ---
    st.markdown(f"### 🔬 Microscope Viewport ({objective_lens} - Click anywhere to center)")
    
    y1 = st.session_state.y_stage - half_crop
    y2 = st.session_state.y_stage + half_crop
    x1 = st.session_state.x_stage - half_crop
    x2 = st.session_state.x_stage + half_crop
    
    cropped_img = leaf_img[y1:y2, x1:x2]
    cropped_mask = mask_img[y1:y2, x1:x2]
    
    # Force exact square dimensions to prevent stretching across all magnifications
    target_dim = min(cropped_img.shape[0], cropped_img.shape[1])
    cropped_img = cv2.resize(cropped_img, (target_dim, target_dim))
    cropped_mask = cv2.resize(cropped_mask, (target_dim, target_dim), interpolation=cv2.INTER_NEAREST)

    processed_img = apply_lens(cropped_img, st.session_state.active_lens).copy()
    
    vh, vw, _ = processed_img.shape
    # Draw prominent size-50 crosshair dead center
    cv2.drawMarker(processed_img, (int(vw / 2), int(vh / 2)), (240, 50, 50), markerType=cv2.MARKER_CROSS, markerSize=50, thickness=3)
    
    # Unified interactive widget
    viewport_click = streamlit_image_coordinates(processed_img, key=f"single_viewport_{objective_lens}")
    if viewport_click:
        local_x = viewport_click["x"]
        local_y = viewport_click["y"]
        
        scale_factor = target_dim / vw if vw > 0 else 1.0
        new_global_x = int(x1 + (local_x * scale_factor))
        new_global_y = int(y1 + (local_y * scale_factor))
        
        if new_global_x != st.session_state.x_stage or new_global_y != st.session_state.y_stage:
            st.session_state.x_stage = max(half_crop, min(new_global_x, w - half_crop))
            st.session_state.y_stage = max(half_crop, min(new_global_y, h - half_crop))
            
            nav_layer = identify_tissue_by_color(mask_img[st.session_state.y_stage, st.session_state.x_stage][:3])
            st.session_state.telemetry_log.append({"action": "Single Canvas Click", "layer": nav_layer, "timestamp": time.time()})
            st.session_state.active_audio = generate_ai_commentary("Viewport Navigation", nav_layer, selected_target_key)
            st.rerun()

    st.markdown("---")
    if st.button("🎯 Submit Center Crosshair Target", type="primary", use_container_width=True):
        sampled_rgb = mask_img[st.session_state.y_stage, st.session_state.x_stage][:3]
        detected_layer = identify_tissue_by_color(sampled_rgb)
        
        st.session_state.telemetry_log.append({"action": "Submit Target", "layer": detected_layer, "timestamp": time.time()})
        st.session_state.active_audio = generate_ai_commentary("Final Answer Submission", detected_layer, selected_target_key)
        
        if detected_layer == selected_target_key:
            st.session_state.target_found = True
            st.success(f"🎉 **Correct Interpretation!** Successfully verified the {detected_layer.upper()}.")
        else:
            st.error(f"❌ **Tissue Misalignment:** Target is resting in the {detected_layer.upper()} instead of your objective.")

    play_queued_audio()
