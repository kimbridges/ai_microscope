import streamlit as st
import time
import cv2
import numpy as np
from PIL import Image

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
    st.session_state.unlocked_tools = []

# --- 2. BOTANICAL IMAGE ENGINE ---
@st.cache_data
def load_micrograph():
    try:
        img = Image.open("leaf_section.jpg")
        return np.array(img)
    except FileNotFoundError:
        # Generate our synthetic C3 leaf cross-section simulation
        img = np.ones((800, 1200, 3), dtype=np.uint8) * 245
        
        # Upper Epidermis (boxy cells, safranin outlines)
        for x in range(0, 1200, 40):
            cv2.rectangle(img, (x, 40), (x+40, 100), (200, 130, 180), 2)
            
        # Palisade Mesophyll (Columnar green cells)
        for x in range(10, 1200, 30):
            for y in [110, 200]:
                cv2.rectangle(img, (x, y), (x+25, y+80), (140, 200, 140), -1)
                cv2.rectangle(img, (x, y), (x+25, y+80), (60, 110, 60), 2)
                
        # Spongy Mesophyll (Loose parenchyma with air gaps)
        np.random.seed(42)
        for _ in range(90):
            cx = np.random.randint(40, 1160)
            cy = np.random.randint(300, 660)
            if int((cx-600)**2 + (cy-460)**2)**0.5 < 170:
                continue
            cv2.circle(img, (cx, cy), np.random.randint(22, 36), (140, 200, 140), -1)
            cv2.circle(img, (cx, cy), np.random.randint(22, 36), (60, 110, 60), 2)
            
        # Vascular Bundle (Central Vein)
        cv2.circle(img, (600, 460), 160, (225, 220, 210), -1)
        cv2.circle(img, (600, 460), 160, (120, 120, 120), 3)
        
        # Xylem (Safranin red thick-walled cells)
        for k in range(-2, 3):
            cv2.circle(img, (600 + k*40, 370), 24, (235, 120, 120), -1)
            cv2.circle(img, (600 + k*40, 370), 24, (180, 40, 40), 4)
            cv2.circle(img, (580 + k*35, 415), 18, (235, 120, 120), -1)
            cv2.circle(img, (580 + k*35, 415), 18, (180, 40, 40), 4)
            
        # Phloem (Fast Green thin-walled cells)
        for px in range(500, 710, 16):
            for py in range(460, 580, 16):
                if int((px-600)**2 + (py-460)**2)**0.5 < 140:
                    cv2.circle(img, (px, py), 7, (160, 220, 190), -1)
                    cv2.circle(img, (px, py), 7, (90, 150, 120), 1)
                    
        # Lower Epidermis
        for x in range(0, 1200, 40):
            cv2.rectangle(img, (x, 700), (x+40, 760), (200, 130, 180), 2)
            
        return img

raw_img = load_micrograph()
h, w, _ = raw_img.shape

# --- 3. DYNAMIC RENDERING LENSES ---
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

# --- 4. USER INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.subheader("Objective: Locate the Spongy Mesophyll (Parenchyma)")

if st.session_state.pivot_triggered:
    col_left, col_right = st.columns([3, 2])
else:
    col_left, col_right = st.columns([5, 0.1])

with col_left:
    st.write("### Microscope Viewport")
    
    objective_lens = st.selectbox(
        "🔄 Rotate Microscope Objective Turret:",
        options=["4x (Scanning Objective)", "10x (Low Power Objective)", "40x (High Power Objective)"],
        index=1
    )
    
    zoom_map = {"4x (Scanning Objective)": 1.0, "10x (Low Power Objective)": 2.0, "40x (High Power Objective)": 4.5}
    zoom = zoom_map[objective_lens]
    crop_size = int(min(h, w) / zoom)
    
    # --- SAFE STAGE BOUNDARY LOGIC ---
    # Vertical Axis Calculation
    y_min = int(crop_size / 2)
    y_max = int(h - crop_size / 2)
    if y_min >= y_max:
        y_center = y_min  # Lock to midpoint because the whole height is visible
        st.caption("↔️ *Vertical Stage: Centered (Full specimen height is within view)*")
    else:
        y_center = st.slider("Stage Vertical Position (Y-Axis)", min_value=y_min, max_value=y_max, value=int(h/2))
        
    # Horizontal Axis Calculation
    x_min = int(crop_size / 2)
    x_max = int(w - crop_size / 2)
    if x_min >= x_max:
        x_center = x_min  # Lock to midpoint
        st.caption("↔️ *Horizontal Stage: Centered (Full specimen width is within view)*")
    else:
        x_center = st.slider("Stage Horizontal Position (X-Axis)", min_value=x_min, max_value=x_max, value=int(w/2))
    
    # Execute safe viewport cropping
    y1, y2 = y_center - int(crop_size/2), y_center + int(crop_size/2)
    x1, x2 = x_center - int(crop_size/2), x_center + int(crop_size/2)
    cropped_img = raw_img[y1:y2, x1:x2]
    
    processed_img = apply_lens(cropped_img, st.session_state.active_lens)
    st.image(processed_img, use_container_width=True)
    
    st.caption(f"**Current Status:** Viewing specimen through the {objective_lens}.")
    
    st.markdown("---")
    st.write("🔧 *Prototype Telemetry Controls*")
    
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
        if (h * 0.40) <= y_center <= (h * 0.75):
            if st.button("🎯 Submit Current Viewport Coordinates", type="primary"):
                st.session_state.target_found = True
                st.success("Correct! You've located the loose, irregular cells of the Spongy Mesophyll.")
        else:
            if st.button("🎯 Submit Current Viewport Coordinates", type="secondary"):
                st.error("Target not found at these coordinates. Review cell shapes and positions.")

# --- 5. THE SOCRATIC PIVOT ---
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
            if "Wall Density Profile (High Contrast)" not in st.session_state.unlocked_tools:
                st.session_state.unlocked_tools = ["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"]
            
            st.session_state.active_lens = st.selectbox(
                "Select a lens filter to apply back to your primary viewport:", 
                options=st.session_state.unlocked_tools
            )
            
            if st.button("Close Palette and Return to Full Screen"):
                st.session_state.pivot_triggered = False
                st.rerun()

# --- 6. PERMANENT SYSTEM ACCESSORIES ---
if len(st.session_state.unlocked_tools) > 0 and not st.session_state.pivot_triggered:
    st.sidebar.markdown("### 🛠️ Unlocked Accessory Tray")
    st.sidebar.write("Alternative visual tools permanently available for use:")
    st.session_state.active_lens = st.sidebar.radio(
        "Active Microscope Lens Profile:", 
        options=st.session_state.unlocked_tools
    )