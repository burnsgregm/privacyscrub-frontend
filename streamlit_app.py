import streamlit as st
import requests, time

# --- INFRASTRUCTURE CONFIGURATION (Updated) ---
# 1. Update this to the "gateway_url" output from your Terraform apply
API_URL = "https://privacyscrub-gateway-whbrskh54q-uc.a.run.app"
API_KEY = "secret" # Note: V5 Gateway currently allows open access (auth is a future step)
# -----------------------------------------------------

st.set_page_config("PrivacyScrub Console", layout="wide")
st.title("PrivacyScrub Enterprise Console")

# Sidebar - Privacy Controls
st.sidebar.header("Privacy Controls")
profile = st.sidebar.selectbox("Compliance Profile", ["NONE", "GDPR", "CCPA", "HIPAA_SAFE_HARBOR"])
mode = st.sidebar.radio("Redaction Mode", ["blur", "pixelate", "black_box"])

# Sidebar - Granular Targets
st.sidebar.subheader("Targets (Profile Override)")
t_faces = st.sidebar.checkbox("Faces", True)
t_plates = st.sidebar.checkbox("Plates", True)
t_logos = st.sidebar.checkbox("Logos", False)
t_text = st.sidebar.checkbox("Text (OCR)", False)

headers = {"X-API-KEY": API_KEY}
tab1, tab2 = st.tabs(["Single Image", "Video Job"])

with tab1:
    st.subheader("Image Anonymization")
    st.info("ℹ️ V5 Deployment Note: Image endpoint is currently pending backend implementation.")
    img = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
    if img and st.button("Process Image"):
        # This will 404 until /v1/anonymize-image is added to gateway/main.py
        with st.spinner("Redacting PII..."):
            files = {"file": img.getvalue()}
            data = {
                "profile": profile, "mode": mode,
                "target_faces": t_faces, "target_plates": t_plates,
                "target_logos": t_logos, "target_text": t_text
            }
            try:
                # 2. Note: This endpoint is missing in current V5 Gateway
                r = requests.post(f"{API_URL}/v1/anonymize-image", headers=headers, files=files, data=data)
                if r.status_code == 200:
                    c1, c2 = st.columns(2)
                    c1.image(img, caption="Original")
                    c2.image(r.content, caption="Anonymized")
                else:
                    st.error(f"API Error: {r.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")

with tab2:
    st.subheader("Batch Video Processing")
    vid = st.file_uploader("Upload Video", type=['mp4'])
    if vid and st.button("Start Processing Job"):
        with st.spinner("Initializing Cloud Job..."):
            try:
                files = {"file": vid.getvalue()}
                data = {"webhook_url": ""} # V5 expects this field form-encoded
                
                # 3. Update: Endpoint changed from /v1/anonymize-video to /v1/video
                r = requests.post(f"{API_URL}/v1/video", headers=headers, files=files, data=data)
                
                if r.status_code == 200:
                    job_id = r.json()["job_id"]
                    st.success(f"Job Started: {job_id}")
                    
                    status_ph = st.empty()
                    bar = st.progress(0)
                    
                    while True:
                        time.sleep(3)
                        try:
                            stat = requests.get(f"{API_URL}/v1/jobs/{job_id}", headers=headers).json()
                            s = stat.get('status', 'UNKNOWN')
                            
                            # 4. Update: Calculate progress from raw chunks
                            chunks_total = stat.get('chunks_total', 0)
                            chunks_completed = stat.get('chunks_completed', 0)
                            
                            if chunks_total > 0:
                                p = chunks_completed / chunks_total
                            else:
                                p = 0.0
                                
                            status_ph.info(f"Status: {s} | Chunks: {chunks_completed}/{chunks_total}")
                            bar.progress(min(p, 1.0))
                            
                            if s == "COMPLETED":
                                st.success("Processing Complete!")
                                # Output URL from V5 backend
                                output_url = stat.get('output_url', '#')
                                st.markdown(f"[Download Result]({output_url})")
                                break
                                
                            if s in ["FAILED", "CANCELLED"]:
                                st.error(f"Job Failed: {stat.get('error_message', 'Unknown error')}")
                                break
                        except Exception as e:
                             st.warning(f"Polling warning: {e}")
                else:
                    st.error(f"API Error: {r.status_code} - {r.text}")
            except Exception as e:
                st.error(f"Connection Error: {e}")
