import streamlit as st
import time
import cv2
import numpy as np
from PIL import Image
import os

# --- 1. PAGE CONFIGURATION & INITIAL STATE ---
st.set_page_config(layout="wide", page_title="AI Microscope Prototype")

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
    
    # Locate Visual Micrograph Asset
    leaf_file = None
    for f in ["leaf_section.jpg", "leaf_section.jpeg", "leaf_section.JPG", "leaf_section.PNG"]:
        if f in repo_files:
            leaf_file = f
            break
            
    # Locate Interpretive Segmentation Mask Asset
    mask_file = None
    for f in ["color_layer.png", "color_layer.PNG", "color_layer.jpg", "color_layer.jpeg"]:
        if f in repo_files:
            mask_file = f
            break

    # Guard Rail: If assets missing, provide explicit instructions
    if not leaf_file or not mask_file:
        missing = []
        if not leaf_file: missing.append("`leaf_section.jpg`")
        if not mask_file: missing.append("`color_layer.png`")
        return None, None, f"⚠️ Missing required assets in repository root: {', '.join(missing)}. Please verify file names match exactly."

    try:
        leaf_img = np.array(Image.open(leaf_file))
        mask_img = np.array(Image.open(mask_file))
        return leaf_img, mask_img, f"🎯 **System Live:** Successfully paired visual micrograph `{leaf_file}` with interpretive segmentation map `{mask_file}`."
    except Exception as e:
        return None, None, f"❌ Error initializing image buffers: {str(e)}"

leaf_img, mask_img, status_msg = load_microscope_assets()

# --- 3. CORE 1989 COLOR LABELER ENGINE ---
# Calibrated RGB anchors derived directly from the color_layer.png palette
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

# --- 5. USER INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)
st.markdown("---")

if leaf_img is None or mask_img is None:
    st.error("Please ensure both your visual photo (`leaf_section.jpg`) and your colored underlay (`color_layer.png`) are committed to your GitHub repository root directory to start.")
else:
    h, w, _ = leaf_img.shape
    mask_h, mask_w, _ = mask_img.shape

    if st.session_state.pivot_triggered:
        col_left, col_right = st.columns([3, 2])
    else:
        col_left, col_right = st.columns([5, 0.1])

    with col_left:
        st.write("### 🎛️ Microscope Bench Controls")
        ctrl_col1, ctrl_col2 = st.columns(2)
        
        with ctrl_col1:
            objective_lens = st.selectbox(
                "🔄 Rotate Microscope Objective Turret:",
                options=["4x (Scanning Objective)", "10x (Low Power Objective)", "40x (High Power Objective)"],
                index=1
            )
        
        with ctrl_col2:
            if len(st.session_state.unlocked_tools) > 1:
                st.session_state.active_lens = st.radio(
                    "🛠️ Unlocked Accessory Tray (Alternative Lenses):",
                    options=st.session_state.unlocked_tools,
                    horizontal=True
                )
            else:
                st.info("🛠️ *Accessory Tray: Empty. Diagnostic tools will unlock here if you experience a structural roadblock.*")

        # Map Objective Magnification
        zoom_map = {"4x (Scanning Objective)": 1.0, "10x (Low Power Objective)": 2.0, "40x (High Power Objective)": 4.5}
        zoom = zoom_map[objective_lens]
        crop_size = int(min(h, w) / zoom)
        
        # Adaptive Stage Sliders
        y_min, y_max = int(crop_size / 2), int(h - crop_size / 2)
        y_center = y_min if y_min >= y_max else st.slider("Stage Vertical Position (Y-Axis)", min_value=y_min, max_value=y_max, value=int(h/2))
            
        x_min, x_max = int(crop_size / 2), int(w - crop_size / 2)
        x_center = x_min if x_min >= x_max else st.slider("Stage Horizontal Position (X-Axis)", min_value=x_min, max_value=x_max, value=int(w/2))
        
        # Crop Viewport from Main Photo
        y1, y2 = y_center - int(crop_size/2), y_center + int(crop_size/2)
        x1, x2 = x_center - int(crop_size/2), x_center + int(crop_size/2)
        cropped_img = leaf_img[y1:y2, x1:x2]
        
        processed_img = apply_lens(cropped_img, st.session_state.active_lens)
        st.image(processed_img, use_container_width=True)
        st.caption(f"**Microscope Status:** Actively rendering a {crop_size}x{crop_size} micron window centered at coordinate ({x_center}, {y_center}).")
        
        # --- PROTOTYPE EVALUATION ENGINE ---
        st.markdown("---")
        st.write("🔧 *System Feedback Framework*")
        
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("Simulate Active Scanning"):
                st.session_state.stall_time = 0
                st.toast("Telemetry received: User actively exploring.")
        with c2:
            if st.button("Simulate 90-Second Stall"):
                st.session_state.stall_time = 95
                if st.session_state.stall_time > 90 and not st.session_state.target_found:
                    st.session_state.pivot_triggered = True
                    st.rerun()
        with c3:
            # INTERPRETIVE GRADING EVENT (1989 METAPHOR)
            if st.button("🎯 Submit Current Viewport Coordinates", type="primary"):
                # 1. Translate active visual coordinates to relative percentage positions
                pct_x = x_center / w
                pct_y = y_center / h
                
                # 2. Scale percentages to target indices on the interpretation mask image
                target_mask_x = int(pct_x * mask_w)
                target_mask_y = int(pct_y * mask_h)
                
                # Boundary clamping safety
                target_mask_x = max(0, min(target_mask_x, mask_w - 1))
                target_mask_y = max(0, min(target_mask_y, mask_h - 1))
                
                # 3. Read the underlying RGB vector color signature
                sampled_rgb = mask_img[target_mask_y, target_mask_x][:3]
                
                # 4. Classify via the 1989 Color Key Keypad
                detected_layer = identify_tissue_by_color(sampled_rgb)
                
                # 5. Route educational logic response
                if detected_layer == "spongy mesophyll":
                    st.session_state.target_found = True
                    st.success("🎉 Excellent interpretation! The color map confirms your coordinates sit squarely within the loose, irregular cells of the Spongy Mesophyll layer.")
                elif detected_layer == "cell wall boundary line":
                    st.warning("🧐 **Anatomical Boundary Hit:** You submitted coordinates right on a dark cell wall line or boundary. Nudge the stage position adjustments slightly to land directly inside a cell's interior chamber.")
                elif detected_layer == "intercellular space / background":
                    st.info("💨 **Intercellular Void Hit:** You are currently aiming inside an empty atmospheric pocket or a hollow vessel lumen. Adjust your focus dials slightly to pick up a neighboring parenchymal cellular body.")
                else:
                    st.error(f"❌ **Misalignment Detoured:** Your microscope target is currently positioned inside the **{detected_layer.upper()}** layer instead. Re-examine the cell shape signatures and slide the stage accordingly.")

    # --- 6. THE SOCRATIC PIVOT ---
    if st.session_state.pivot_triggered and not st.session_state.target_found:
        with col_right:
            st.error("🤖 AI Microscope Co-Pilot Intervening")
            st.info(
                "🗣️ **Audio Script Broadcast:**\n\n"
                "\"I might not have highlighted the structural map well enough for this slide. "
                "We can pull up the gas exchange module here to see how these cells cooperate with air spaces, "
                "or I can give you a direct visual clue. What is your preference?\""
            )
            
            choice = st.radio("Choose your resolution path:", ["Select an option...", "Open the Visual Diagnostic Palette", "Get a Direct Structural Clue"])
            
            if choice == "Get a Direct Structural Clue":
                st.warning("💡 **Clue:** Look lower than the tightly packed, vertical column cells (Palisade Layer). The cells you want are rounded, irregular, and surrounded by large empty air pockets.")
            
            elif choice == "Open the Visual Diagnostic Palette":
                st.success("🔓 Alternative Visual Toolkit Unlocked")
                st.session_state.unlocked_tools = ["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"]
                
                st.session_state.active_lens = st.selectbox(
                    "Select a lens filter to apply back to your primary viewport:", 
                    options=st.session_state.unlocked_tools
                )
                
                if st.button("Close Palette and Return to Full Screen"):
                    st.session_state.pivot_triggered = False
                    st.rerun()