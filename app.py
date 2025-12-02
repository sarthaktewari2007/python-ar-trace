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

def rotate_image(image, k):
    # k is the number of 90-degree turns (0, 1, 2, 3)
    if k % 4 == 0: return image
    return np.rot90(image, k=k)

def crop_image(image, left_p, right_p, top_p, bottom_p):
    h, w = image.shape[:2]
    x_start = int(w * (left_p / 100))
    x_end = int(w * (1 - right_p / 100))
    y_start = int(h * (top_p / 100))
    y_end = int(h * (1 - bottom_p / 100))
    
    # Ensure valid crop
    if x_start >= x_end or y_start >= y_end:
        return image
    return image[y_start:y_end, x_start:x_end]

def adjust_brightness_contrast(image, alpha, beta):
    return cv2.convertScaleAbs(image, alpha=alpha, beta=beta)

def draw_grid(image, grid_size=3):
    h, w = image.shape[:2]
    color = (0, 255, 0) if len(image.shape) > 2 else 128
    for i in range(1, grid_size):
        x = int(w * i / grid_size)
        cv2.line(image, (x, 0), (x, h), color, 2)
    for i in range(1, grid_size):
        y = int(h * i / grid_size)
        cv2.line(image, (0, y), (w, y), color, 2)
    return image

# Split processing into two stages for better UI response
def apply_geometric_transforms(pil_image, rotation, crop_vals):
    # 1. Convert PIL to OpenCV
    img_array = np.array(pil_image.convert('RGB'))
    img_cv = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    
    # 2. Rotate & Crop
    img_cv = rotate_image(img_cv, rotation)
    img_cv = crop_image(img_cv, *crop_vals)
    return img_cv

def apply_artistic_filters(img_cv, mode, t1, t2, brightness, contrast, show_grid):
    # 3. Color Corrections
    img_cv = adjust_brightness_contrast(img_cv, contrast, brightness)

    # 4. Filters
    final_img = img_cv
    
    if mode == "Grayscale":
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
        
    elif mode == "Crayon Drawing":
        final_img = cv2.bilateralFilter(img_cv, 9, 75, 75)
        gray = cv2.cvtColor(final_img, cv2.COLOR_BGR2GRAY)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        final_img = cv2.bitwise_and(final_img, final_img, mask=edges)

    elif mode == "Abstract":
        final_img = cv2.pyrMeanShiftFiltering(img_cv, 21, 51)
        
    elif mode == "Negative":
        final_img = cv2.bitwise_not(img_cv)
        
    elif mode == "Sepia":
        kernel = np.array([[0.272, 0.534, 0.131], [0.349, 0.686, 0.168], [0.393, 0.769, 0.189]])
        final_img = cv2.transform(img_cv, kernel)
        final_img = np.clip(final_img, 0, 255).astype(np.uint8)

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
    original_image = Image.open(uploaded_file)
    
    # --- STEP 1: GEOMETRY ---
    st.markdown("### ✂️ Step 1: Crop & Rotate")
    with st.container():
        c_rot1, c_rot2 = st.columns(2)
        if c_rot1.button("↺ Rotate Left"): st.session_state.rotation = (st.session_state.rotation + 1) % 4
        if c_rot2.button("↻ Rotate Right"): st.session_state.rotation = (st.session_state.rotation - 1) % 4
        
        st.write("**Crop Edges (%)**")
        cr1, cr2 = st.columns(2)
        crop_top = cr1.slider("Top Cut", 0, 50, 0)
        crop_bottom = cr2.slider("Bottom Cut", 0, 50, 0)
        cr3, cr4 = st.columns(2)
        crop_left = cr3.slider("Left Cut", 0, 50, 0)
        crop_right = cr4.slider("Right Cut", 0, 50, 0)

        geo_img = apply_geometric_transforms(
            original_image, 
            st.session_state.rotation, 
            (crop_left, crop_right, crop_top, crop_bottom)
        )
        
        # Show Geometric Preview
        with st.expander("Show Crop Preview", expanded=False):
            st.image(cv2.cvtColor(geo_img, cv2.COLOR_BGR2RGB), caption="Cropped Layout", use_container_width=True)

    # --- STEP 2: ARTISTIC FILTERS ---
    st.markdown("### 🎨 Step 2: Filters & Effects")
    # Expander is now closer to the AR surface
    with st.expander("Filter Controls", expanded=True):
        mode = st.selectbox("Select Filter", ["Original", "Grayscale", "Magic Outline", "Pencil Sketch", "Crayon Drawing", "Abstract", "Sepia", "Negative"])
        
        ac1, ac2 = st.columns(2)
        brightness = ac1.slider("Brightness", -100, 100, 0)
        contrast = ac2.slider("Contrast", 0.5, 3.0, 1.0, 0.1)

        t1, t2 = 100, 200
        if mode == "Magic Outline":
            t1 = st.slider("Edge Min", 0, 500, 50)
            t2 = st.slider("Edge Max", 0, 500, 150)
            
        show_grid = st.checkbox("Show Artist Grid (3x3)")

    # Processing happens here to feed into Step 3 immediately
    final_processed_img = apply_artistic_filters(
        geo_img, mode, t1, t2, brightness, contrast, show_grid
    )
    img_b64 = get_image_base64(final_processed_img)

    # --- STEP 3: AR TRACING SURFACE ---
    st.markdown("### 📱 Step 3: AR Tracing Surface")
    st.info("Controls below video. Use 'Record' to capture your process.")

    html_code = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;700&display=swap" rel="stylesheet">
    <style>
        body {{ margin: 0; background: #000; font-family: 'Space Grotesk', sans-serif; overflow: hidden; }}
        .container {{ position: relative; width: 100%; height: 600px; border-radius: 12px; border: 2px solid #6366f1; overflow: hidden; background: #000; }}
        
        /* Full Screen Class */
        .fullscreen {{
            position: fixed !important;
            top: 0 !important;
            left: 0 !important;
            width: 100vw !important;
            height: 100vh !important;
            z-index: 9999 !important;
            border-radius: 0 !important;
            border: none !important;
        }}

        video {{ width: 100%; height: 100%; object-fit: cover; }}
        #overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; display: flex; justify-content: center; align-items: center; }}
        #trace-img {{ width: 80%; opacity: 0.5; transition: transform 0.2s; }}
        
        .controls {{ 
            position: absolute; bottom: 0; left: 0; right: 0;
            background: rgba(0,0,0,0.85); backdrop-filter: blur(8px);
            padding: 15px; border-top: 1px solid #444; color: white; pointer-events: auto;
            display: flex; flex-direction: column; gap: 10px;
        }}
        
        .row {{ display: flex; gap: 10px; justify-content: space-between; }}
        
        button {{ 
            flex: 1; padding: 12px; border: none; border-radius: 8px; 
            font-weight: bold; cursor: pointer; color: white; font-size: 14px;
            background: #334155; transition: 0.2s;
        }}
        button:active {{ transform: scale(0.95); }}
        
        .btn-lock {{ background: #4f46e5; }}
        .btn-torch {{ background: #f59e0b; color: black; }}
        .btn-flip {{ background: #0ea5e9; }}
        .btn-max {{ background: #ec4899; }}
        .btn-rec {{ background: #ef4444; }}
        .btn-rec.recording {{ background: #fff; color: #ef4444; animation: pulse 1s infinite; }}
        
        @keyframes pulse {{
            0% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0.7); }}
            70% {{ box-shadow: 0 0 0 10px rgba(255, 255, 255, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(255, 255, 255, 0); }}
        }}
        
        input[type=range] {{ width: 100%; accent-color: #8E2DE2; }}
        label {{ font-size: 12px; color: #cbd5e1; }}
    </style>
    </head>
    <body>
    <div id="app-container" class="container">
        <video id="video" autoplay playsinline></video>
        <div id="overlay"><img id="trace-img" src="{img_b64}"></div>
        
        <div class="controls">
            <!-- Row 1: Sliders -->
            <div class="row">
                <div style="flex:1">
                    <label>Opacity</label>
                    <input type="range" min="0" max="100" value="50" oninput="updateStyle('opacity', this.value/100)">
                </div>
                <div style="flex:1">
                    <label>Size</label>
                    <input type="range" min="10" max="300" value="80" oninput="updateStyle('width', this.value+'%')">
                </div>
            </div>
            
            <!-- Row 2: Flips & Max -->
            <div class="row">
                <button class="btn-flip" onclick="flip('h')">↔ Flip H</button>
                <button class="btn-flip" onclick="flip('v')">↕ Flip V</button>
                <button class="btn-max" onclick="toggleFullScreen()">⛶ Max</button>
            </div>
            
            <!-- Row 3: Tools -->
            <div class="row">
                <button class="btn-lock" onclick="toggleLock()">🔒 Lock</button>
                <button class="btn-torch" onclick="toggleTorch()">🔦 Light</button>
                <button class="btn-rec" onclick="toggleRecord()">🔴 Record</button>
            </div>
        </div>
    </div>
    <script>
        const container = document.getElementById('app-container');
        const video = document.getElementById('video');
        const img = document.getElementById('trace-img');
        let isLocked = false;
        let isFull = false;
        let stream = null;
        let scaleX = 1; 
        let scaleY = 1;
        
        // Recording Vars
        let mediaRecorder;
        let recordedChunks = [];
        let isRecording = false;

        // Camera Init
        navigator.mediaDevices.getUserMedia({{ video: {{ facingMode: 'environment' }} }}).then(s => {{
            stream = s;
            video.srcObject = s;
        }});

        // UI Updates
        function updateStyle(prop, val) {{
            img.style[prop] = val;
        }}

        function flip(axis) {{
            if(axis === 'h') scaleX *= -1;
            if(axis === 'v') scaleY *= -1;
            updateTransform();
        }}
        
        // Touch Drag Logic
        let startX, startY, currentX=0, currentY=0;
        
        function updateTransform() {{
            img.style.transform = `translate(${{currentX}}px, ${{currentY}}px) scale(${{scaleX}}, ${{scaleY}})`;
        }}

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
            updateTransform();
        }}, {{ passive: false }});

        function toggleLock() {{
            isLocked = !isLocked;
            const btn = document.querySelector('.btn-lock');
            btn.innerText = isLocked ? "🔓 Unlock" : "🔒 Lock";
            btn.style.background = isLocked ? "#ef4444" : "#4f46e5";
        }}

        function toggleTorch() {{
            const track = stream.getVideoTracks()[0];
            const cap = track.getCapabilities();
            if (cap.torch) {{
                track.applyConstraints({{ advanced: [{{ torch: !track.getSettings().torch }}] }});
            }} else {{ alert("Flashlight not available"); }}
        }}

        function toggleFullScreen() {{
            isFull = !isFull;
            if (isFull) {{
                container.classList.add('fullscreen');
                document.querySelector('.btn-max').innerText = "↘ Min";
            }} else {{
                container.classList.remove('fullscreen');
                document.querySelector('.btn-max').innerText = "⛶ Max";
            }}
        }}
        
        function toggleRecord() {{
            const btn = document.querySelector('.btn-rec');
            if (!isRecording) {{
                // Start Recording
                recordedChunks = [];
                // Record the camera stream
                mediaRecorder = new MediaRecorder(stream, {{ mimeType: 'video/webm' }});
                
                mediaRecorder.ondataavailable = function(event) {{
                    if (event.data.size > 0) {{
                        recordedChunks.push(event.data);
                    }}
                }};
                
                mediaRecorder.onstop = function() {{
                    const blob = new Blob(recordedChunks, {{ type: 'video/webm' }});
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    document.body.appendChild(a);
                    a.style = 'display: none';
                    a.href = url;
                    a.download = 'glass_canvas_recording.webm';
                    a.click();
                    window.URL.revokeObjectURL(url);
                }};
                
                mediaRecorder.start();
                isRecording = true;
                btn.innerText = "⬛ Stop";
                btn.classList.add('recording');
            }} else {{
                // Stop Recording
                mediaRecorder.stop();
                isRecording = false;
                btn.innerText = "🔴 Record";
                btn.classList.remove('recording');
            }}
        }}
    </script>
    </body>
    </html>
    """
    st.components.v1.html(html_code, height=620)

    # --- FINAL PREVIEW & DOWNLOAD (Moved to bottom) ---
    st.markdown("---")
    with st.expander("💾 Download & Preview", expanded=False):
        if len(final_processed_img.shape) > 2:
            st.image(final_processed_img, channels="BGR", use_container_width=True)
            pil_result = Image.fromarray(cv2.cvtColor(final_processed_img, cv2.COLOR_BGR2RGB))
        else:
            st.image(final_processed_img, use_container_width=True)
            pil_result = Image.fromarray(final_processed_img)
            
        buf = BytesIO()
        pil_result.save(buf, format="PNG")
        st.download_button(
            label="💾 Download Processed Image",
            data=buf.getvalue(),
            file_name="glass_canvas_trace.png",
            mime="image/png"
        )
else:
    st.info("👆 Please upload an image to begin.")
