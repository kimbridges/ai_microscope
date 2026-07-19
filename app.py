import streamlit as st
import time
import cv2
import numpy as np
from PIL import Image
import os

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
        missing = []
        if not leaf_file: missing.append("`leaf_section.jpg`")
        if not mask_file: missing.append("`color_layer.png`")
        return None, None, f"⚠️ Missing required assets in repository root: {', '.join(missing)}"

    try:
        leaf_img = np.array(Image.open(leaf_file))
        mask_img = np.array(Image.open(mask_file))
        return leaf_img, mask_img, f"🎯 **System Live:** Paired `{leaf_file}` with interpretive map `{mask_file}`."
    except Exception as e:
        return None, None, f"❌ Error initializing image buffers: {str(e)}"

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
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    
    elif lens_type == "Geometric Borders (Outline Map)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 30, 100)
        inverted = cv2.bitwise_not(edges)
        return cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
    
    return img


# --- 5. FIXED PERSISTENT DASHBOARD LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)

if leaf_img is None or mask_img is None:
    st.error("Please ensure both your visual photo (`leaf_section.jpg`) and your colored underlay (`color_layer.png`) are committed to your GitHub repository root.")
else:
    h, w, _ = leaf_img.shape
    mask_h, mask_w, _ = mask_img.shape

    # Establish our layout grid configuration
    if st.session_state.pivot_triggered:
        # 3 Columns active: Viewport (Left), Controls (Center), Co-Pilot (Right)
        col_view, col_ctrl, col_pivot = st.columns([4, 3, 3])
    else:
        # 2 Columns active: Viewport (Left), Controls (Center), Hidden Spacer (Right)
        col_view, col_ctrl, col_pivot = st.columns([5, 3, 0.1])

    # --- EXECUTION PASS 1: THE CONTROL DECK (CENTER COLUMN) ---
    with col_ctrl:
        st.write("### 🎛️ Bench Control Deck")
        
        objective_lens = st.selectbox(
            "🔄 Rotate Microscope Objective Turret:",
            options=["4x (Scanning Objective)", "10x (Low Power Objective)", "40x (High Power Objective)"],
            index=1
        )
        
        zoom_map = {"4x (Scanning Objective)": 1.0, "10x (Low Power Objective)": 2.0, "40x (High Power Objective)": 4.5}
        zoom = zoom_map[objective_lens]
        crop_size = int(min(h, w) / zoom)
        
        # Calculate safe mechanical stage constraints
        y_min, y_max = int(crop_size / 2), int(h - crop_size / 2)
        x_min, x_max = int(crop_size / 2), int(w - crop_size / 2)
        
        st.markdown("**Stage Navigation Clamps:**")
        if y_min >= y_max:
            y_center = y_min
            st.caption("↕️ *Vertical Stage: Centered & Locked*")
        else:
            y_center = st.slider("Vertical Axis (Y-Center)", min_value=y_min, max_value=y_max, value=int(h/2))
            
        if x_min >= x_max:
            x_center = x_min
            st.caption("↔️ *Horizontal Stage: Centered & Locked*")
        else:
            x_center = st.slider("Horizontal Axis (X-Center)", min_value=x_min, max_value=x_max, value=int(w/2))
            
        if len(st.session_state.unlocked_tools) > 1:
            st.session_state.active_lens = st.radio(
                "🛠️ Lens Filter Select:",
                options=st.session_state.unlocked_tools,
                horizontal=True
            )
            
        # PRIMARY CALL TO ACTION (Positioned right under the sliders)
        st.markdown("---")
        if st.button("🎯 Submit Current Viewport Coordinates", type="primary", use_container_width=True):
            pct_x = x_center / w
            pct_y = y_center / h
            
            target_mask_x = max(0, min(int(pct_x * mask_w), mask_w - 1))
            target_mask_y = max(0, min(int(pct_y * mask_h), mask_h - 1))
            
            sampled_rgb = mask_img[target_mask_y, target_mask_x][:3]
            detected_layer = identify_tissue_by_color(sampled_rgb)
            
            if detected_layer == "spongy mesophyll":
                st.session_state.target_found = True
                st.success("🎉 **Correct Interpretation!** The color map confirms your target is directly inside the loose Spongy Mesophyll tissue layer.")
            elif detected_layer == "cell wall boundary line":
                st.warning("🧐 **Boundary Hit:** You landed right on a dark cell wall line. Nudge the stage coordinate sliders slightly to slide deep inside a cell chamber.")
            elif detected_layer == "intercellular space / background":
                st.info("💨 **Atmospheric Space Hit:** You are targeting an empty intercellular air pocket or vessel lumen. Shift the stage position slightly to acquire a distinct cellular body.")
            else:
                st.error(f"❌ **Tissue Misalignment:** Your target coordinates are sitting inside the **{detected_layer.upper()}** layer instead. Adjust your stage vertical axis to track down the irregular parenchyma.")

        # COMPACT COLLAPSIBLE EXPANDER FOR TESTING TELEMETRY
        with st.expander("🔧 Backend Telemetry Simulation Tools"):
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("Active Scan Signal", use_container_width=True):
                    st.session_state.stall_time = 0
                    st.toast("Telemetry refreshed.")
            with tc2:
                if st.button("90-Sec Stall Signal", use_container_width=True):
                    st.session_state.stall_time = 95
                    if not st.session_state.target_found:
                        st.session_state.pivot_triggered = True
                        st.rerun()

    # --- EXECUTION PASS 2: THE MICROSCOPE VIEWPORT (LEFT COLUMN) ---
    with col_view:
        st.write("### 🔬 Microscope Viewport")
        
        # Safely slice coordinate matrices using values evaluated in the Control Deck column
        y1, y2 = y_center - int(crop_size/2), y_center + int(crop_size/2)
        x1, x2 = x_center - int(crop_size/2), x_center + int(crop_size/2)
        cropped_img = leaf_img[y1:y2, x1:x2]
        
        processed_img = apply_lens(cropped_img, st.session_state.active_lens)
        st.image(processed_img, use_container_width=True)
        st.caption(f"**Optics Engine Status:** Viewing a {crop_size}x{crop_size} pixel region on the specimen canvas.")

    # --- EXECUTION PASS 3: THE SOCRATIC PIVOT (RIGHT COLUMN) ---
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
                
                st.session_state.active_lens = st.selectbox(
                    "Select alternative lens filter profile:", 
                    options=st.session_state.unlocked_tools
                )
                
                if st.button("Close Palette & Lock Tray", use_container_width=True):
                    st.session_state.pivot_triggered = False
                    st.rerun()