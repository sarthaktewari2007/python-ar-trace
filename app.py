import streamlit as st
import cv2
import numpy as np
from PIL import Image, ImageEnhance
import base64
from io import BytesIO

# 1. Page Configuration
st.set_page_config(
    page_title="Glass Canvas | Ultimate", 
    page_icon="🎨", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- CUSTOM CSS ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;500;700&display=swap');
        .stApp {
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            font-family: 'Space Grotesk', sans-serif;
        }
        h1 { color: #fff; text-align: center; font-size: 3rem !important; margin-bottom: 0; }
        .subtitle { text-align: center; color: #a5b4fc; margin-bottom: 2rem; }
        .glass-card {
            background: rgba(255, 255, 255, 0.05); backdrop-filter: blur(10px);
            border-radius: 15px; border: 1px solid rgba(255, 255, 255, 0.1);
            padding: 20px; margin-bottom: 20px;
        }
        .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; background: #4A00E0; color: white; border: none; }
        .stButton>button:hover { background: #8E2DE2; }
        .stMarkdown, .stText, label, .stExpander { color: #e2e8f0 !important; }
        div[data-testid="stExpander"] div[role="button"] p { font-size: 1.1rem; }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE INITIALIZATION ---
if 'rotation' not in st.session_state: st.session_state.rotation = 0
if 'flip_h' not in st.session_state: st.session_state.flip_h = False
if 'flip_v' not in st.session_state: st.session_state.flip_v = False

# --- HELPER FUNCTIONS ---
def get_image_base64(image_array):
    if len(image_array.shape) > 2:
        img_rgb = cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB)
    else:
        img_rgb = image_array
    pil_img = Image.fromarray(img_rgb)
    buff = BytesIO()
    pil_img.save(buff, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buff.getvalue()).decode()}"

def rotate_image(image, angle):
    if angle == 0: return image
    k = angle // 90
    return np.rot90(image, k=k)

def flip_image(image, h, v):
    if h: image = cv2.flip(image, 1)
    if v: image = cv2.flip(image, 0)
    return image

def adjust_brightness_contrast(image, alpha, beta):
    # Alpha = Contrast (1.0-3.0), Beta = Brightness (0-100)
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

def draw_grid(image, grid_size=3):
    h, w = image.shape[:2]
    color = (0, 255, 0) if len(image.shape) > 2 else 128
    # Vertical
    for i in range(1, grid_size):
        x = int(w * i / grid_size)
        cv2.line(image, (x, 0), (x, h), color, 2)
    # Horizontal
    for i in range(1, grid_size):
        y = int(h * i / grid_size)
        cv2.line(image, (0, y), (w, y), color, 2)
    return image

def process_image(pil_image, mode, t1, t2, rotation, flip_h, flip_v, brightness, contrast, show_grid):
    # 1. Convert PIL to OpenCV
    img_array = np.array(pil_image.convert('RGB'))
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 2. Geometric Transforms
    img_cv = rotate_image(img_cv, rotation)
    img_cv = flip_image(img_cv, flip_h, flip_v)

    # 3. Color Corrections (Before filters for better edge detection)
    img_cv = adjust_brightness_contrast(img_cv, contrast, brightness)

    # 4. Filters
    if mode == "Original":
        final_img = img_cv
    elif mode == "Grayscale":
        final_img = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
    elif mode == "Magic Outline":
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(blurred, t1, t2)
        final_img = cv2.bitwise_not(edges)
    elif mode == "Pencil Sketch":
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        inv = cv2.bitwise_not(gray)
        blur = cv2.GaussianBlur(inv, (21, 21), 0)
        sketch = cv2.divide(gray, 255 - blur, scale=256)
        final_img = cv2.cvtColor(sketch, cv2.COLOR_GRAY2BGR)
    elif mode == "Negative":
        final_img = cv2.bitwise_not(img_cv)
    elif mode == "Sepia":
        kernel = np.array([[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]])
        final_img = cv2.transform(img_cv, kernel)
        final_img = np.clip(final_img, 0, 255).astype(np.uint8)
    else:
        final_img = img_cv

    # 5. Grid
    if show_grid:
        final_img = draw_grid(final_img)

    return final_img

# --- HEADER ---
st.markdown("<h1>GLASS CANVAS</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Ultimate AR Tracing Studio • Batch-53</div>", unsafe_allow_html=True)

# --- MAIN UI ---
with st.container():
    st.markdown("<div class='glass-card'>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("📂 Upload Reference Image", type=['jpg', 'png', 'jpeg'])
    st.markdown("</div>", unsafe_allow_html=True)

if uploaded_file:
    image = Image.open(uploaded_file)
    
    # --- EDITOR CONTROLS ---
    st.markdown("### 🛠️ Studio Tools")
    
    # Row 1: Filters & Basics
    c1, c2 = st.columns([1, 1])
    with c1:
        mode = st.selectbox("Filter Mode", ["Original", "Grayscale", "Magic Outline", "Pencil Sketch", "Sepia", "Negative"])
        
    with c2:
        # Mini Toolbar
        rc1, rc2, rc3 = st.columns(3)
        if rc1.button("↺"): st.session_state.rotation = (st.session_state.rotation + 1) % 4
        if rc2.button("↔"): st.session_state.flip_h = not st.session_state.flip_h
        if rc3.button("↕"): st.session_state.flip_v = not st.session_state.flip_v

    # Row 2: Sliders
    with st.expander("🎚️ Advanced Adjustments", expanded=False):
        ac1, ac2 = st.columns(2)
        brightness = ac1.slider("Brightness", -100, 100, 0)
        contrast = ac2.slider("Contrast", 0.5, 3.0, 1.0, 0.1)
        
        t1, t2 = 100, 200
        if mode == "Magic Outline":
            st.caption("Edge Detection Sensitivity")
            t1 = st.slider("Min Threshold", 0, 500, 50)
            t2 = st.slider("Max Threshold", 0, 500, 150)
            
        show_grid = st.checkbox("Show Artist Grid (3x3)")

    # --- PROCESS IMAGE ---
    processed_img = process_image(
        image, mode, t1, t2, 
        st.session_state.rotation, st.session_state.flip_h, st.session_state.flip_v,
        brightness, contrast, show_grid
    )
    img_b64 = get_image_base64(processed_img)

    # --- PREVIEW & DOWNLOAD ---
    with st.expander("👁️ View Result", expanded=True):
        if len(processed_img.shape) > 2:
            st.image(processed_img, channels="BGR", use_container_width=True)
            pil_result = Image.fromarray(cv2.cvtColor(processed_img, cv2.COLOR_BGR2RGB))
        else:
            st.image(processed_img, use_container_width=True)
            pil_result = Image.fromarray(processed_img)
            
        # Download Button
        buf = BytesIO()
        pil_result.save(buf, format="PNG")
        st.download_button(
            label="💾 Download Processed Image",
            data=buf.getvalue(),
            file_name="glass_canvas_trace.png",
            mime="image/png"
        )

    # --- CAMERA OVERLAY ---
    st.markdown("---")
    st.markdown("### 📱 AR Tracing Surface")
    st.info("Scroll down. Use the Flashlight if needed.")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; background: #000; font-family: 'Space Grotesk', sans-serif; overflow: hidden; }}
        .container {{ position: relative; width: 100%; height: 600px; border-radius: 12px; border: 2px solid #6366f1; overflow: hidden; }}
        video {{ width: 100%; height: 100%; object-fit: cover; }}
        #overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; display: flex; justify-content: center; align-items: center; }}
        #trace-img {{ width: 80%; opacity: 0.5; mix-blend-mode: normal; filter: invert(0); }}
        .controls {{ 
            position: absolute; bottom: 10px; left: 10px; right: 10px; 
            background: rgba(0,0,0,0.7); backdrop-filter: blur(5px);
            padding: 15px; border-radius: 12px; color: white; border: 1px solid #444; pointer-events: auto;
        }}
        .btn {{ flex: 1; padding: 12px; border: none; border-radius: 8px; font-weight: bold; cursor: pointer; color: white; }}
        .btn-lock {{ background: #4f46e5; }}
        .btn-torch {{ background: #f59e0b; color: black; }}
    </style>
    </head>
    <body>
    <div class="container">
        <video id="video" autoplay playsinline></video>
        <div id="overlay"><img id="trace-img" src="{img_b64}"></div>
        
        <div class="controls">
            <div style="display: flex; gap: 10px; margin-bottom: 10px;">
                <input type="range" min="0" max="100" value="50" oninput="document.getElementById('trace-img').style.opacity = this.value/100" style="width:50%">
                <input type="range" min="10" max="300" value="80" oninput="document.getElementById('trace-img').style.width = this.value+'%'" style="width:50%">
            </div>
            <div style="display: flex; gap: 10px;">
                <button class="btn btn-lock" onclick="toggleLock()">🔒 Lock Drag</button>
                <button class="btn btn-torch" onclick="toggleTorch()">🔦 Flashlight</button>
            </div>
        </div>
    </div>
    <script>
        const video = document.getElementById('video');
        const img = document.getElementById('trace-img');
        let isLocked = false;
        let stream = null;

        navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'environment' }} }}).then(s => {{
            stream = s;
            video.srcObject = s;
        }});

        function toggleTorch() {{
            const track = stream.getVideoTracks()[0];
            const capabilities = track.getCapabilities();
            if (capabilities.torch) {{
                track.applyConstraints({{ advanced: [{{ torch: !track.getSettings().torch }}] }});
            }} else {{
                alert("Flashlight not available on this device.");
            }}
        }}

        let startX, startY, currentX=0, currentY=0;
        document.addEventListener('touchstart', e => {{
            if(isLocked || e.target.closest('.controls')) return;
            startX = e.touches[0].clientX - currentX;
            startY = e.touches[0].clientY - currentY;
        }});
        document.addEventListener('touchmove', e => {{
            if(isLocked || e.target.closest('.controls')) return;
            e.preventDefault();
            currentX = e.touches[0].clientX - startX;
            currentY = e.touches[0].clientY - startY;
            img.style.transform = `translate(${{currentX}}px, ${{currentY}}px)`;
        }}, {{ passive: false }});

        function toggleLock() {{
            isLocked = !isLocked;
            document.querySelector('.btn-lock').innerText = isLocked ? "🔓 Unlock Drag" : "🔒 Lock Drag";
            document.querySelector('.btn-lock').style.background = isLocked ? "#ef4444" : "#4f46e5";
        }}
    </script>
    </body>
    </html>
    """
    st.components.v1.html(html_code, height=620)
else:
    st.info("👆 Please upload an image to begin.")
