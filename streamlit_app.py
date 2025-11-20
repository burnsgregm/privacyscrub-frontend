import streamlit as st
import requests, time, os

st.set_page_config(page_title="PrivacyScrub V4", layout="wide")

# Config
API_URL = st.secrets.get("SERVICE_URL", os.environ.get("SERVICE_URL", "http://localhost:8080"))

# --- Sidebar: V4 Configuration ---
st.sidebar.title("V4 Controls")

profile = st.sidebar.selectbox(
    "Compliance Profile", 
    ["NONE", "GDPR", "CCPA", "HIPAA_SAFE_HARBOR"],
    help="Enforces strict preset configurations for regulatory compliance."
)

st.sidebar.subheader("Overrides")
mode = st.sidebar.radio("Mode", ["blur", "pixelate", "black_box"])
target_faces = st.sidebar.checkbox("Redact Faces", True)
target_plates = st.sidebar.checkbox("Redact Plates", True)
target_text = st.sidebar.checkbox("Redact Text (OCR)", False)
target_logos = st.sidebar.checkbox("Redact Logos", False)
coords_only = st.sidebar.checkbox("Coordinates Only (JSON)", False)

st.sidebar.subheader("Advanced")
roi_input = st.sidebar.text_input("ROI (x1,y1,x2,y2)", placeholder="0.0,0.0,1.0,1.0")

# --- Main UI ---
st.title("PrivacyScrub V4")
st.caption(f"Backend Active: {API_URL}")

tab1, tab2 = st.tabs(["Image Analysis", "Video Pipeline"])

# Tab 1: Image
with tab1:
    img_file = st.file_uploader("Upload Image", type=["jpg", "png"])
    if img_file and st.button("Process Image"):
        with st.spinner("Running V4 Multi-Model Inference..."):
            try:
                files = {"file": img_file.getvalue()}
                data = {
                    "profile": profile, "mode": mode, 
                    "target_faces": target_faces, "target_plates": target_plates,
                    "target_text": target_text, "target_logos": target_logos,
                    "coordinates_only": coords_only, "roi": roi_input
                }
                resp = requests.post(f"{API_URL}/v1/anonymize-image", files=files, data=data)
                
                if resp.status_code == 200:
                    if coords_only:
                        st.json(resp.json())
                    else:
                        col1, col2 = st.columns(2)
                        col1.image(img_file, caption="Original")
                        col2.image(resp.content, caption="Anonymized (Metadata Stripped)")
                else:
                    st.error(f"Failed: {resp.text}")
            except Exception as e: st.error(f"Error: {e}")

# Tab 2: Video
with tab2:
    vid_file = st.file_uploader("Upload Video", type=["mp4"])
    if vid_file and st.button("Start Job"):
        with st.spinner("Uploading & Dispatching..."):
            try:
                files = {"file": vid_file.getvalue()}
                resp = requests.post(f"{API_URL}/v1/anonymize-video", files=files, data={"profile": profile})
                
                if resp.status_code == 200:
                    job_id = resp.json()["job_id"]
                    st.success(f"Job Dispatched: {job_id}")
                    
                    # Poll Status
                    status_placeholder = st.empty()
                    bar = st.progress(0)
                    
                    while True:
                        time.sleep(3)
                        job_data = requests.get(f"{API_URL}/v1/jobs/{job_id}").json()
                        status = job_data.get("status")
                        
                        if status == "COMPLETED":
                            bar.progress(100)
                            status_placeholder.success("Processing Complete")
                            st.video(job_data.get("output_url"))
                            break
                        elif status == "FAILED":
                            status_placeholder.error(f"Job Failed: {job_data.get('error_message')}")
                            break
                        else:
                            # Estimate progress based on chunks
                            total = job_data.get("chunks_total", 1)
                            done = job_data.get("chunks_completed", 0)
                            if total > 0: bar.progress(int((done / total) * 90))
                            status_placeholder.info(f"Status: {status} (Chunks: {done}/{total})")
            except Exception as e: st.error(f"Error: {e}")
