import streamlit as st
import time
import cv2
import numpy as np
from PIL import Image
import os
from streamlit_image_coordinates import streamlit_image_coordinates

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

# Initialize persistent stage coordinates in session state if not set
if "x_stage" not in st.session_state:
    st.session_state.x_stage = -1
if "y_stage" not in st.session_state:
    st.session_state.y_stage = -1

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
        mask_img = np.array(Image.open(mask_file))
        return leaf_img, mask_img, f"🎯 **System Live:** Navigation map calibrated using `{leaf_file}`."
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

# --- 5. VISUAL INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.caption(status_msg)
st.markdown("---")

if leaf_img is None or mask_img is None:
    st.error("Please ensure both your visual photo (`leaf_section.jpg`) and your colored underlay (`color_layer.png`) are committed to your GitHub repository root.")
else:
    h, w, _ = leaf_img.shape
    mask_h, mask_w, _ = mask_img.shape

    # Set default center coordinates upon first startup
    if st.session_state.x_stage == -1 or st.session_state.y_stage == -1:
        st.session_state.x_stage = int(w / 2)
        st.session_state.y_stage = int(h / 2)

    # Establish layout grid split
    if st.session_state.pivot_triggered:
        col_view, col_ctrl, col_pivot = st.columns([4.5, 3.5, 3])
    else:
        col_view, col_ctrl, col_pivot = st.columns([5.5, 3.5, 0.1])

    # --- PASS 1: SYSTEM CONTROLS & MINI-MAP MOUSE NAVIGATOR (CENTER) ---
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
        
        # Calculate bounding boundaries based on current selection
        half_crop = int(crop_size / 2)
        y_min, y_max = half_crop, h - half_crop
        x_min, x_max = half_crop, w - half_crop
        
        # Force clamp current positions inside safe operating bounds
        st.session_state.y_stage = max(y_min, min(st.session_state.y_stage, y_max))
        st.session_state.x_stage = max(x_min, min(st.session_state.x_stage, x_max))
        
        # --- GENERATE THE INTERACTIVE MAP OVERVIEW ---
        st.markdown("**🗺️ Specimen Overview Map (Click anywhere to center target):**")
        
        # Build an overlay graphic copy for navigation orientation
        map_canvas = leaf_img.copy()
        
        # Draw the target box showing the high-magnification window boundaries
        box_y1 = st.session_state.y_stage - half_crop
        box_y2 = st.session_state.y_stage + half_crop
        box_x1 = st.session_state.x_stage - half_crop
        box_x2 = st.session_state.x_stage + half_crop
        cv2.rectangle(map_canvas, (box_x1, box_y1), (box_x2, box_y2), (230, 40, 40), 6) # Red Box
        
        # Add a small anchor center point dot
        cv2.circle(map_canvas, (st.session_state.x_stage, st.session_state.y_stage), 12, (230, 40, 40), -1)
        
        # Resize canvas to a standard, predictable thumbnail size for display tracking
        thumb_w = 400
        thumb_h = int(h * (thumb_w / w))
        map_thumb = cv2.resize(map_canvas, (thumb_w, thumb_h))
        
        # Render the map and listen continuously for mouse click vector inputs
        click_data = streamlit_image_coordinates(map_thumb, key="macro_map_click")
        
        if click_data:
            # Scale the thumbnail click coordinates back up to full image pixel constraints
            calculated_x = int((click_data["x"] / thumb_w) * w)
            calculated_y = int((click_data["y"] / thumb_h) * h)
            
            # If coordinates shifted, update positions and force instant window update
            if calculated_x != st.session_state.x_stage or calculated_y != st.session_state.y_stage:
                st.session_state.x_stage = max(x_min, min(calculated_x, x_max))
                st.session_state.y_stage = max(y_min, min(calculated_y, y_max))
                st.date_index = time.time()  # Cache busting token
                st.rerun()

        st.caption(f"📍 **Current Stage Center Coordinate:** X: `{st.session_state.x_stage}`, Y: `{st.session_state.y_stage}`")
        
        if len(st.session_state.unlocked_tools) > 1:
            st.session_state.active_lens = st.radio(
                "🛠️ Lens Filter Select:", options=st.session_state.unlocked_tools, horizontal=True
            )
            
        # PRIMARY GRADING INTERACTION
        st.markdown("---")
        if st.button("🎯 Submit Center Crosshair Target", type="primary", use_container_width=True):
            pct_x = st.session_state.x_stage / w
            pct_y = st.session_state.y_stage / h
            
            target_mask_x = max(0, min(int(pct_x * mask_w), mask_w - 1))
            target_mask_y = max(0, min(int(pct_y * mask_h), mask_h - 1))
            
            sampled_rgb = mask_img[target_mask_y, target_mask_x][:3]
            detected_layer = identify_tissue_by_color(sampled_rgb)
            
            if detected_layer == "spongy mesophyll":
                st.session_state.target_found = True
                st.success("🎉 **Correct Interpretation!** Your crosshair target is centered inside the loose Spongy Mesophyll tissue layer.")
            elif detected_layer == "cell wall boundary line":
                st.warning("🧐 **Boundary Hit:** Your target crosshair is touching a dark cell wall line. Click slightly inside a cell interior chamber to submit.")
            elif detected_layer == "intercellular space / background":
                st.info("💨 **Atmospheric Space Hit:** You are targeting an empty intercellular air pocket. Use the overview map to acquire a distinct cell body.")
            else:
                st.error(f"❌ **Tissue Misalignment:** Target is sitting inside the **{detected_layer.upper()}** layer instead. Click the low-power zone below the palisade columns.")

        with st.expander("🔧 Backend Telemetry Simulation Tools"):
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("Active Scan Signal", use_container_width=True): st.session_state.stall_time = 0
            with tc2:
                if st.button("90-Sec Stall Signal", use_container_width=True):
                    st.session_state.stall_time = 95
                    if not st.session_state.target_found: st.session_state.pivot_triggered = True; st.rerun()

    # --- PASS 2: THE HIGH-POWER MICROSCOPE VIEWPORT WITH CENTER RETICLE (LEFT) ---
    with col_view:
        st.write("### 🔬 Microscope Viewport")
        
        # Calculate viewport frame bounds safely
        y1 = st.session_state.y_stage - half_crop
        y2 = st.session_state.y_stage + half_crop
        x1 = st.session_state.x_stage - half_crop
        x2 = st.session_state.x_stage + half_crop
        
        cropped_img = leaf_img[y1:y2, x1:x2]
        processed_img = apply_lens(cropped_img, st.session_state.active_lens).copy()
        
        # Draw a subtle optical target reticle/crosshair right in the center of the student's field of view
        vh, vw, _ = processed_img.shape
        cx, cy = int(vw / 2), int(vh / 2)
        cv2.drawMarker(processed_img, (cx, cy), (240, 50, 50), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        
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
                
                st.session_state.active_lens = st.selectbox(
                    "Select alternative lens filter profile:", options=st.session_state.unlocked_tools
                )
                
                if st.button("Close Palette & Lock Tray", use_container_width=True):
                    st.session_state.pivot_triggered = False; st.rerun()