import streamlit as st
import time
import cv2
import numpy as np
from PIL import Image
import urllib.request

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

# --- 2. LOAD BOTANICAL MICROGRAPH DATA ---
@st.cache_data
def load_micrograph():
    # Primary Choice: If you upload your own image to your repo, use it natively
    try:
        img = Image.open("leaf_section.jpg")
        return np.array(img)
    except FileNotFoundError:
        # Secondary Choice: Fallback to the web image if no local file exists
        url = "https://upload.wikimedia.org/wikipedia/commons/e/e0/Leaf_anatomy_with_labels_small.jpg"
        
        # We explicitly add a User-Agent header to bypass automated scraping blocks
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AI-Microscope-Bot/1.0'}
        )
        with urllib.request.urlopen(req) as response:
            img = Image.open(response)
        return np.array(img)

raw_img = load_micrograph()
h, w, _ = raw_img.shape

# --- 3. DYNAMIC RENDERING LENSES (IMAGE PROCESSING) ---
def apply_lens(img, lens_type):
    if lens_type == "Wall Density Profile (High Contrast)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        # Emphasize thick xylem / epidermal structures via adaptive thresholding
        thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
        return cv2.cvtColor(thresh, cv2.COLOR_GRAY2RGB)
    
    elif lens_type == "Geometric Borders (Outline Map)":
        gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        # Inverse edges to look like a black-and-ink drawing line map
        inverted = cv2.bitwise_not(edges)
        return cv2.cvtColor(inverted, cv2.COLOR_GRAY2RGB)
    
    return img

# --- 4. USER INTERFACE LAYOUT ---
st.title("🔬 AI Microscope Learning Environment")
st.subheader("Objective: Locate the Spongy Mesophyll (Parenchyma)")

# Setup split-screen dynamically based on system state
if st.session_state.pivot_triggered:
    col_left, col_right = st.columns([3, 2])
else:
    col_left, col_right = st.columns([5, 0.1])

with col_left:
    st.write("### Microscope Viewport")
    
    # Simulate a viewport cropping mechanism (simulating panning/zooming)
    zoom = st.slider("Microscope Magnification Stage", min_value=1, max_value=4, value=2)
    crop_size = int(min(h, w) / zoom)
    
    # For prototype testing, user simulates scanning by picking a region
    y_center = st.slider("Stage Vertical Adjust (Y-Axis)", min_value=int(crop_size/2), max_value=int(h - crop_size/2), value=int(h/2))
    x_center = st.slider("Stage Horizontal Adjust (X-Axis)", min_value=int(crop_size/2), max_value=int(w - crop_size/2), value=int(w/2))
    
    y1, y2 = y_center - int(crop_size/2), y_center + int(crop_size/2)
    x1, x2 = x_center - int(crop_size/2), x_center + int(crop_size/2)
    cropped_img = raw_img[y1:y2, x1:x2]
    
    # Apply selected visual adjustment filters from the student toolkit
    processed_img = apply_lens(cropped_img, st.session_state.active_lens)
    st.image(processed_img, use_container_width=True)
    
    # --- SIMULATED TELEMETRY CONTROLS (BENEATH THE HOOD SENSORS) ---
    st.markdown("---")
    st.write("🔧 *Prototype Telemetry Controls (To test system behavior without waiting 90 seconds)*")
    
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
        # Spongy mesophyll is historically located in the middle-to-lower ground tissue
        # We simulate finding it if they position the Y-Axis into the lower-middle half
        if (h * 0.45) <= y_center <= (h * 0.80):
            if st.button("🎯 Submit Current Viewport Coordinates", type="primary"):
                st.session_state.target_found = True
                st.success("Correct! You've located the loose, irregular cells of the Spongy Mesophyll.")
        else:
            if st.button("🎯 Submit Current Viewport Coordinates", type="secondary"):
                st.error("Target not found at these coordinates. Review cell shapes and positions.")

# --- 5. THE SOCRATIC PIVOT (THE RIGHT HALF OF THE SPLIT SCREEN) ---
if st.session_state.pivot_triggered and not st.session_state.target_found:
    with col_right:
        st.error("🤖 AI Microscope Co-Pilot Intervening")
        
        # Uncluttered Audio/Visual Metaphor: The system takes responsibility for the gap
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
            # Update permanent session assets
            if "Wall Density Profile (High Contrast)" not in st.session_state.unlocked_tools:
                st.session_state.unlocked_tools = ["Standard View", "Wall Density Profile (High Contrast)", "Geometric Borders (Outline Map)"]
            
            # Allow the student to select their diagnostic lens manually
            st.session_state.active_lens = st.selectbox(
                "Select a lens filter to apply back to your primary viewport:", 
                options=st.session_state.unlocked_tools
            )
            
            if st.button("Close Palette and Return to Full Screen"):
                st.session_state.pivot_triggered = False
                st.rerun()

# --- 6. PERMANENT SYSTEM ACCESSORIES (THE SOFT TOOL TRAY) ---
if len(st.session_state.unlocked_tools) > 0 and not st.session_state.pivot_triggered:
    st.sidebar.markdown("### 🛠️ Unlocked Accessory Tray")
    st.sidebar.write("Alternative visual tools permanently available for use:")
    st.session_state.active_lens = st.sidebar.radio(
        "Active Microscope Lens Profile:", 
        options=st.session_state.unlocked_tools
    )