import streamlit as st
import requests, time

st.set_page_config("PrivacyScrub Console", layout="wide")
st.title("PrivacyScrub Enterprise Console")

# Configuration Sidebar
st.sidebar.header("Connection")

# [FIX] Auto-clean URL to enforce HTTPS (prevents header stripping on redirects)
raw_url = st.sidebar.text_input("API URL", placeholder="https://your-cloud-run-url.run.app")
if raw_url:
    API_URL = raw_url.strip().rstrip("/")
    if API_URL.startswith("http://"):
        API_URL = API_URL.replace("http://", "https://")
else:
    API_URL = ""

# [FIX] Default value set to 'secret' to match backend default
API_KEY = st.sidebar.text_input("API Key", value="secret", type="password")

st.sidebar.header("Privacy Settings")
profile = st.sidebar.selectbox("Compliance Profile", ["NONE", "GDPR", "CCPA", "HIPAA_SAFE_HARBOR"])
mode = st.sidebar.radio("Redaction Mode", ["blur", "pixelate", "black_box"])

tab1, tab2 = st.tabs(["Single Image", "Video Job"])
headers = {"X-API-KEY": API_KEY}

with tab1:
    st.subheader("Image Anonymization")
    img = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
    if img and st.button("Process Image"):
        if not API_URL:
            st.error("Please enter the API URL from the Deployment Output.")
        else:
            with st.spinner("Redacting PII..."):
                files = {"file": img.getvalue()}
                data = {"profile": profile, "mode": mode}
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
        if not API_URL:
            st.error("Please enter the API URL from the Deployment Output.")
        else:
            with st.spinner("Uploading and initializing job..."):
                try:
                    files = {"file": vid.getvalue()}
                    data = {"profile": profile}
                    r = requests.post(f"{API_URL}/v1/anonymize-video", headers=headers, files=files, data=data)
                    if r.status_code == 200:
                        job_id = r.json()["job_id"]
                        st.success(f"Job Initialized: {job_id}")
                        
                        status_placeholder = st.empty()
                        bar = st.progress(0)
                        
                        while True:
                            time.sleep(3)
                            stat = requests.get(f"{API_URL}/v1/jobs/{job_id}", headers=headers).json()
                            status = stat['status']
                            prog = stat.get('progress', 0.0)
                            
                            status_placeholder.info(f"Status: {status} | Progress: {int(prog*100)}%")
                            bar.progress(prog)
                            
                            if status == "COMPLETED":
                                st.success("Processing Complete!")
                                st.markdown(f"[Download Anonymized Video]({stat['output_url']})")
                                break
                            if status in ["FAILED", "CANCELLED"]:
                                st.error(f"Job Failed: {stat.get('error_message')}")
                                break
                    else:
                        st.error(f"API Error: {r.text}")
                except Exception as e:
                    st.error(f"Connection Error: {e}")
