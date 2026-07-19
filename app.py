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
        raw_mask = np.array(Image.open(mask_file))
        
        # EXTRACT MICROGRAPH TARGET DIMENSIONS
        h, w, _ = leaf_img.shape
        
        # ALIGNMENT ENGINE: Force the mask to stretch to match the exact matrix dimensions of the photo.
        # We use INTER_NEAREST to keep cell interpretation borders perfectly sharp instead of blurry.
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

    # --- PASS 1: CONTROL DECK & DIAGNOSTIC SLIDERS (CENTER) ---
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
        
        # --- DEBUG TOOLRAY ADDITION: OVERLAY ALPHA SLIDER ---
        st.markdown("---")
        st.write("🔬 **Debug & Alignment Assessment Toolkit**")
        overlay_opacity = st.slider("Map Overlay Opacity (Alpha Blend)", min_value=0, max_value=100, value=35, step=5)
        st.caption("💡 *Slide past 0% to bleed your color interpretation layout directly over the microscope window to verify matching coordinates.*")
        st.markdown("---")

        # Overview Minimap Controller
        st.markdown("**🗺️ Specimen Overview Map (Click to re-center):**")
        map_canvas = leaf_img.copy()
        
        # Render boundary box on thumbnail map
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
                st.date_index = time.time()
                st.rerun()

        if len(st.session_state.unlocked_tools) > 1:
            st.session_state.active_lens = st.radio("🛠️ Lens Filter Select:", options=st.session_state.unlocked_tools, horizontal=True)
            
        # SUBMIT RESPONSE INTERACTION
        if st.button("🎯 Submit Center Crosshair Target", type="primary", use_container_width=True):
            # Because arrays match size perfectly now, we extract from coordinates natively
            sampled_rgb = mask_img[st.session_state.y_stage, st.session_state.x_stage][:3]
            detected_layer = identify_tissue_by_color(sampled_rgb)
            
            if detected_layer == "spongy mesophyll":
                st.session_state.target_found = True
                st.success("🎉 **Correct Interpretation!** Target sits in the Spongy Mesophyll.")
            elif detected_layer == "cell wall boundary line":
                st.warning("🧐 **Boundary Hit:** Target is touching a cell wall boundary line. Click slightly inside a cell chamber.")
            elif detected_layer == "intercellular space / background":
                st.info("💨 **Atmospheric Space Hit:** Targeting an empty intercellular air pocket.")
            else:
                st.error(f"❌ **Tissue Misalignment:** Target is sitting inside the **{detected_layer.upper()}** layer instead.")

        with st.expander("🔧 Telemetry Controls"):
            if st.button("90-Sec Stall Signal", use_container_width=True):
                st.session_state.stall_time = 95
                if not st.session_state.target_found: st.session_state.pivot_triggered = True; st.rerun()

    # --- PASS 2: HIGH-POWER MICROSCOPE VIEWPORT WITH LIVE MATRIX BLENDING (LEFT) ---
    with col_view:
        st.write("### 🔬 Microscope Viewport")
        
        y1, y2 = st.session_state.y_stage - half_crop, st.session_state.y_stage + half_crop
        x1, x2 = st.session_state.x_stage - half_crop, st.session_state.x_stage + half_crop
        
        cropped_img = leaf_img[y1:y2, x1:x2]
        cropped_mask = mask_img[y1:y2, x1:x2]
        
        # Apply alternative filter matrix logic if active
        processed_img = apply_lens(cropped_img, st.session_state.active_lens).copy()
        
        # DYNAMIC ALPHA BLENDER INTERACTION
        if overlay_opacity > 0:
            alpha = (100 - overlay_opacity) / 100.0
            beta = overlay_opacity / 100.0
            # Blend the visual channel snapshot with the aligned interpretation layer
            processed_img = cv2.addWeighted(processed_img, alpha, cropped_mask[:, :, :3], beta, 0)
        
        # Draw central viewport overlay coordinate target marker
        vh, vw, _ = processed_img.shape
        cv2.drawMarker(processed_img, (int(vw / 2), int(vh / 2)), (240, 50, 50), markerType=cv2.MARKER_CROSS, markerSize=30, thickness=2)
        
        st.image(processed_img, use_container_width=True)
        st.caption(f"🔬 Snapshot coordinates window spanning pixel range X:[{x1}:{x2}], Y:[{y1}:{y2}].")

    # --- PASS 3: THE SOCRATIC PIVOT ---
    if st.session_state.pivot_triggered and not st.session_state.target_found:
        with col_pivot:
            st.error("🤖 AI Co-Pilot Intervention")
            choice = st.radio("Resolution path:", ["Select an option...", "Open Visual Diagnostic Palette", "Get Direct Structural Clue"])
            if choice == "Get Direct Structural Clue":
                st.warning("💡 **Clue:** Target tissue consists of pale green, rounded, loosely packed cells underneath the vertical palisade columns.")
            elif choice == "Open Visual Diagnostic Palette":
                st.success("🔓 Alternative Visual Toolkit Unlocked")
                st.session_state.unlocked_tools = ["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"]
                st.session_state.active_lens = st.selectbox("Select alternative filter:", options=st.session_state.unlocked_tools)
                if st.button("Close Palette & Lock Tray", use_container_width=True):
                    st.session_state.pivot_triggered = False; st.rerun()