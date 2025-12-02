import streamlit as st
import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO

# 1. Page Configuration (Must be first)
st.set_page_config(
    page_title="Glass Canvas | AR Tracing", 
    page_icon="✨", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS FOR FANCY UI ---
st.markdown("""
    <style>
        /* Import Google Font */
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&display=swap');

        /* Main Background */
        .stApp {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            font-family: 'Space Grotesk', sans-serif;
        }

        /* Title Styling */
        h1 {
            color: #fff;
            font-weight: 700;
            text-align: center;
            text-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
            font-size: 3.5rem !important;
        }
        
        .subtitle {
            text-align: center;
            color: #a5b4fc;
            font-size: 1.2rem;
            margin-bottom: 2rem;
        }

        /* Glassmorphism Cards */
        .glass-card {
            background: rgba(255, 255, 255, 0.05);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px;
            margin-bottom: 20px;
        }

        /* Widget Styling Override */
        .stButton>button {
            width: 100%;
            background: linear-gradient(90deg, #8E2DE2, #4A00E0);
            color: white;
            border: none;
            border-radius: 8px;
            font-weight: bold;
        }
        
        /* Text Color Override */
        .stMarkdown, .stText, label {
            color: #e2e8f0 !important;
        }
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def get_image_base64(image_array):
    if len(image_array.shape) > 2:
        img_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = image_array
    pil_img = Image.fromarray(img_rgb)
    buff = BytesIO()
    pil_img.save(buff, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buff.getvalue()).decode()}"

def process_image(pil_image, mode, t1=100, t2=200):
    img_array = np.array(pil_image.convert('RGB'))
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    if mode == "Original":
        return img_cv
    elif mode == "Grayscale":
        return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    elif mode == "Magic Outline (Edge Detection)":
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, t1, t2)
        return cv2.bitwise_not(edges)

# --- UI HEADER ---
st.markdown("<h1>GLASS CANVAS</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>AR-Powered Tracing Assistant • Batch-53</div>", unsafe_allow_html=True)

# --- MAIN APP LOGIC ---

# 1. Upload Section
with st.container():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📂 Upload your reference image", type=['jpg', 'png', 'jpeg'])
    st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file:
    image = Image.open(uploaded_file)
    
    # 2. Controls Section
    st.markdown("### ⚙️ Studio Controls")
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        mode = st.selectbox("View Mode", ["Original", "Grayscale", "Magic Outline (Edge Detection)"])
    
    t1, t2 = 100, 200
    if mode == "Magic Outline (Edge Detection)":
        with col2:
            t1 = st.slider("Detail Level (Min)", 0, 500, 50)
            t2 = st.slider("Detail Level (Max)", 0, 500, 150)

    # Process
    processed_img = process_image(image, mode, t1, t2)
    img_b64 = get_image_base64(processed_img)

    # Preview
    with st.expander("👁️ View Generated Preview", expanded=True):
        st.image(processed_img, use_container_width=True)

    # 3. The Camera Interface
    st.markdown("---")
    st.markdown("### 📱 AR Tracing Surface")
    st.info("Scroll down. Place phone on a glass/stand. Look through the screen to trace.")

    # HTML/JS Injection for Camera
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; overflow: hidden; background: #000; font-family: 'Space Grotesk', sans-serif; }}
        .container {{ position: relative; width: 100%; height: 650px; overflow: hidden; border-radius: 15px; border: 2px solid #4A00E0; }}
        #camera-video {{ 
            width: 100%; height: 100%; object-fit: cover; 
        }}
        #overlay-wrapper {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
            pointer-events: none; 
        }}
        #trace-img {{
            width: 80%;
            opacity: 0.5;
            transform-origin: center;
            mix-blend-mode: multiply; 
            filter: invert(0); /* Can toggle for dark mode paper */
        }}
        .controls {{
            position: absolute; bottom: 20px; left: 20px; right: 20px;
            background: rgba(0, 0, 0, 0.6);
            backdrop-filter: blur(10px);
            padding: 15px; border-radius: 15px;
            display: flex; flex-direction: column; gap: 10px;
            pointer-events: auto; border: 1px solid rgba(255,255,255,0.2);
            color: white;
        }}
        input[type=range] {{ width: 100%; accent-color: #8E2DE2; }}
        .btn {{
            background: #4A00E0; color: white; border: none; padding: 10px;
            border-radius: 8px; font-weight: bold; cursor: pointer;
        }}
    </style>
    </head>
    <body>

    <div class="container">
        <!-- Camera Feed -->
        <video id="camera-video" autoplay playsinline></video>
        
        <!-- Overlay Image -->
        <div id="overlay-wrapper">
            <img id="trace-img" src="{img_b64}">
        </div>

        <!-- Touch Controls -->
        <div class="controls">
            <div style="display:flex; justify-content:space-between;">
                <small>Opacity</small> <small>Size</small>
            </div>
            <div style="display:flex; gap:10px;">
                <input type="range" min="0" max="100" value="50" oninput="updateOpacity(this.value)">
                <input type="range" min="10" max="300" value="80" oninput="updateSize(this.value)">
            </div>
            
            <button class="btn" onclick="toggleLock()">🔒 Lock / Unlock Dragging</button>
        </div>
    </div>

    <script>
        const video = document.getElementById('camera-video');
        const img = document.getElementById('trace-img');
        let isLocked = false;

        // 1. Start Camera
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {{
            navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'environment' }} }})
            .then((stream) => {{ video.srcObject = stream; }})
            .catch((err) => {{ console.log("Camera Error", err); }});
        }}

        // 2. UI Updates
        function updateOpacity(val) {{ img.style.opacity = val / 100; }}
        function updateSize(val) {{ img.style.width = val + '%'; }}
        function toggleLock() {{ 
            isLocked = !isLocked; 
            const btn = document.querySelector('.btn');
            btn.innerHTML = isLocked ? "🔓 Unlock Dragging" : "🔒 Lock Dragging";
            btn.style.background = isLocked ? "#333" : "#4A00E0";
        }}

        // 3. Simple Drag Logic
        let startX, startY, currentX = 0, currentY = 0;

        document.addEventListener('touchstart', function(e) {{
            if (isLocked) return;
            if (e.target.closest('.controls')) return;
            startX = e.touches[0].clientX - currentX;
            startY = e.touches[0].clientY - currentY;
        }});

        document.addEventListener('touchmove', function(e) {{
            if (isLocked) return;
            if (e.target.closest('.controls')) return;
            e.preventDefault(); 
            currentX = e.touches[0].clientX - startX;
            currentY = e.touches[0].clientY - startY;
            img.style.transform = `translate(${{currentX}}px, ${{currentY}}px)`;
        }}, {{ passive: false }});
    </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=670)

else:
    # Landing Page Placeholder
    st.markdown("""
    <div style='text-align: center; color: #64748b; margin-top: 50px;'>
        <h3>👈 Upload an image to start</h3>
        <p>Supports JPG, PNG • Best used on Mobile</p>
    </div>
    """, unsafe_allow_html=True)
