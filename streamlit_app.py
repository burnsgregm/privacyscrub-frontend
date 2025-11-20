import streamlit as st
import requests, time

# --- INFRASTRUCTURE CONFIGURATION (Injected by Deployment Script) ---
# The deployment script will replace this placeholder with the actual Cloud Run URL
API_URL = "https://privacyscrub-api-whbrskh54q-uc.a.run.app"
API_KEY = "secret"
# --------------------------------------------------------------------

st.set_page_config("PrivacyScrub Console", layout="wide")
st.title("PrivacyScrub Enterprise Console")

# Sidebar - Privacy Controls
st.sidebar.header("Privacy Controls")
profile = st.sidebar.selectbox("Compliance Profile", ["NONE", "GDPR", "CCPA", "HIPAA_SAFE_HARBOR"])
mode = st.sidebar.radio("Redaction Mode", ["blur", "pixelate", "black_box"])

# Sidebar - Granular Targets (Restored)
st.sidebar.subheader("Targets (Profile Override)")
t_faces = st.sidebar.checkbox("Faces", True)
t_plates = st.sidebar.checkbox("Plates", True)
t_logos = st.sidebar.checkbox("Logos", False)
t_text = st.sidebar.checkbox("Text (OCR)", False)

headers = {"X-API-KEY": API_KEY}
tab1, tab2 = st.tabs(["Single Image", "Video Job"])

with tab1:
    st.subheader("Image Anonymization")
    img = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
    if img and st.button("Process Image"):
        if "REPLACE" in API_URL:
            st.error("⚠️ System not fully deployed. API URL is missing.")
        else:
            with st.spinner("Redacting PII..."):
                files = {"file": img.getvalue()}
                # Sending granular checkbox values to backend
                data = {
                    "profile": profile, "mode": mode,
                    "target_faces": t_faces, "target_plates": t_plates,
                    "target_logos": t_logos, "target_text": t_text
                }
                try:
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
        if "REPLACE" in API_URL:
            st.error("⚠️ System not fully deployed. API URL is missing.")
        else:
            with st.spinner("Initializing Cloud Job..."):
                try:
                    files = {"file": vid.getvalue()}
                    # Sending profile (video endpoint uses profile defaults for targets)
                    data = {"profile": profile}
                    r = requests.post(f"{API_URL}/v1/anonymize-video", headers=headers, files=files, data=data)
                    if r.status_code == 200:
                        job_id = r.json()["job_id"]
                        st.success(f"Job Started: {job_id}")
                        
                        status_ph = st.empty()
                        bar = st.progress(0)
                        while True:
                            time.sleep(3)
                            stat = requests.get(f"{API_URL}/v1/jobs/{job_id}", headers=headers).json()
                            s = stat['status']
                            p = stat.get('progress', 0.0)
                            status_ph.info(f"Status: {s} | Progress: {int(p*100)}%")
                            bar.progress(p)
                            
                            if s == "COMPLETED":
                                st.success("Processing Complete!")
                                st.markdown(f"[Download Result]({stat['output_url']})")
                                break
                            if s in ["FAILED", "CANCELLED"]:
                                st.error(f"Job Failed: {stat.get('error_message')}")
                                break
                    else:
                        st.error(f"API Error: {r.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
