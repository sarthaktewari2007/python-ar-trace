import streamlit as st
import cv2
import numpy as np
from PIL import Image
import base64
from io import BytesIO

# 1. Page Configuration
st.set_page_config(page_title="AR Trace Master", page_icon="✏️", layout="centered")

# --- Helper: Convert OpenCV Image to Base64 for HTML ---
def get_image_base64(image_array):
    # Convert BGR (OpenCV) to RGB (PIL)
    if len(image_array.shape) > 2:
        img_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = image_array
        
    pil_img = Image.fromarray(img_rgb)
    buff = BytesIO()
    pil_img.save(buff, format="PNG")
    img_str = base64.b64encode(buff.getvalue()).decode()
    return f"data:image/png;base64,{img_str}"

# --- Helper: Image Processing Filters ---
def process_image(pil_image, mode, t1=100, t2=200):
    # Convert PIL image to OpenCV format
    img_array = np.array(pil_image.convert('RGB'))
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)

    if mode == "Original":
        return img_cv
    
    elif mode == "Grayscale":
        return cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    
    elif mode == "Edge Detection (Line Art)":
        # Convert to gray, blur to remove noise, then find edges
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, t1, t2)
        # Invert colors (Black lines on White background)
        return cv2.bitwise_not(edges)

# --- App Interface ---
st.title("✏️ AR Tracing Assistant")
st.markdown("Upload a photo, process it with Python, and trace it on paper using your phone camera.")

# Step 1: Upload
uploaded_file = st.file_uploader("Upload Image to Trace", type=['jpg', 'png', 'jpeg'])

if uploaded_file:
    image = Image.open(uploaded_file)
    
    # Step 2: Processing Controls
    st.subheader("1. Prepare Your Image")
    
    col1, col2 = st.columns(2)
    with col1:
        mode = st.selectbox("Filter Mode", ["Original", "Grayscale", "Edge Detection (Line Art)"])
    
    t1, t2 = 100, 200
    if mode == "Edge Detection (Line Art)":
        with col2:
            st.write("Edge Sensitivity:")
            t1 = st.slider("Min Threshold", 0, 500, 50)
            t2 = st.slider("Max Threshold", 0, 500, 150)

    # Run the Python Processing
    processed_img = process_image(image, mode, t1, t2)
    
    # Show Preview
    st.image(processed_img, caption="Processed Preview", use_container_width=True)
    
    # Convert to Base64 for the Camera View
    img_b64 = get_image_base64(processed_img)

    # Step 3: The Camera View (HTML/JS Injection)
    st.subheader("2. Start Tracing")
    st.info("Scroll down. Place your phone on a glass or stand above your paper.")

    # We inject specific HTML/JS to handle the camera locally on the phone
    # This prevents the 'lag' of sending video back and forth to the server
    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
        body {{ margin: 0; overflow: hidden; background: #000; font-family: sans-serif; }}
        .container {{ position: relative; width: 100%; height: 600px; overflow: hidden; border-radius: 12px; }}
        #camera-video {{ 
            width: 100%; height: 100%; object-fit: cover; 
            transform: scaleX(-1); /* Mirror effect for easier alignment */
        }}
        #overlay-wrapper {{
            position: absolute; top: 0; left: 0; width: 100%; height: 100%;
            display: flex; align-items: center; justify-content: center;
            pointer-events: none; /* Let touches pass through to gesture layer */
        }}
        #trace-img {{
            width: 80%;
            opacity: 0.5;
            transform-origin: center;
            /* Filter to make white transparent if it's line art (optional visual hack) */
            mix-blend-mode: multiply; 
        }}
        .controls {{
            position: absolute; bottom: 10px; left: 10px; right: 10px;
            background: rgba(255, 255, 255, 0.8);
            padding: 10px; border-radius: 10px;
            display: flex; flex-direction: column; gap: 5px;
            pointer-events: auto;
        }}
        input[type=range] {{ width: 100%; }}
        label {{ font-size: 12px; font-weight: bold; color: #333; }}
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
            <label>Opacity</label>
            <input type="range" min="0" max="100" value="50" oninput="updateOpacity(this.value)">
            
            <label>Size</label>
            <input type="range" min="10" max="200" value="80" oninput="updateSize(this.value)">
            
            <button onclick="toggleLock()" style="margin-top:5px; padding:8px; background:#333; color:white; border:none; border-radius:4px;">🔒 Lock / Unlock Dragging</button>
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
            alert(isLocked ? "Image Locked" : "Image Unlocked"); 
        }}

        // 3. Simple Drag Logic (Touch)
        let startX, startY, initLeft = 0, initTop = 0;
        const wrapper = document.getElementById('overlay-wrapper');

        // Center initially
        let currentX = 0;
        let currentY = 0;

        document.addEventListener('touchstart', function(e) {{
            if (isLocked) return;
            // Only drag if touching the upper container area, not the controls
            if (e.target.closest('.controls')) return;

            startX = e.touches[0].clientX - currentX;
            startY = e.touches[0].clientY - currentY;
        }});

        document.addEventListener('touchmove', function(e) {{
            if (isLocked) return;
            if (e.target.closest('.controls')) return;
            e.preventDefault(); // Prevent scrolling

            currentX = e.touches[0].clientX - startX;
            currentY = e.touches[0].clientY - startY;

            img.style.transform = `translate(${{currentX}}px, ${{currentY}}px)`;
        }}, {{ passive: false }});

    </script>
    </body>
    </html>
    """
    
    st.components.v1.html(html_code, height=620)