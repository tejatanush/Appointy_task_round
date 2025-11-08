import streamlit as st
import requests
import mimetypes
BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="Synapse Brain", layout="wide")


def api_signup(name, email, password):
    """Call the /signup API"""
    payload = {"name": name, "email": email, "password": password}
    try:
        res = requests.post(f"{BASE_URL}/signup", json=payload)
        res.raise_for_status() # Raises an error for 4xx or 5xx responses
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, err.response.json().get("detail", "Error in signup")
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def api_login(email, password):
    """Call the /login API"""
    payload = {"email": email, "password": password}
    try:
        res = requests.post(f"{BASE_URL}/login", json=payload)
        res.raise_for_status()
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, err.response.json().get("detail", "Invalid credentials")
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def api_add_data(token, data_payload, file_payload=None):
    """Call the /add API (handles all data types)"""
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.post(
            f"{BASE_URL}/add", 
            headers=headers, 
            data=data_payload, 
            files=file_payload
        )
        res.raise_for_status()
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, err.response.json().get("detail", "Failed to add data")
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

def api_search_data(token, query, limit):
    """Call the /data/search API"""
    headers = {"Authorization": f"Bearer {token}"}
    params = {"query": query, "limit": limit}
    try:
        res = requests.get(f"{BASE_URL}/data/search", headers=headers, params=params)
        res.raise_for_status()
        return res.json(), None
    except requests.exceptions.HTTPError as err:
        return None, err.response.json().get("detail", "Failed to search")
    except Exception as e:
        return None, f"An unexpected error occurred: {e}"

if "token" not in st.session_state:
    st.session_state.token = None
    st.session_state.user_email = None
    st.session_state.user_id = None

if st.session_state.token is None:
    st.title("Welcome to Synapse Brain")
    st.markdown("Please log in or register to continue.")

    login_tab, signup_tab = st.tabs(["Login", "Sign Up"])
    with login_tab:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            login_submitted = st.form_submit_button("Login")

            if login_submitted:
                if not email or not password:
                    st.error("Please enter both email and password.")
                else:
                    data, error = api_login(email, password)
                    if error:
                        st.error(error)
                    else:
                        # 🚀 SUCCESS! Store token in session state
                        st.session_state.token = data.get("access_token")
                        st.session_state.user_email = data.get("email")
                        st.session_state.user_id = data.get("user_id")
                        st.success(data.get("message", "Login successful!"))
                        st.rerun() # Re-run the script to show the main app

    # --- Signup Form ---
    with signup_tab:
        with st.form("signup_form"):
            name = st.text_input("Name")
            new_email = st.text_input("Email")
            new_password = st.text_input("Password", type="password")
            signup_submitted = st.form_submit_button("Sign Up")

            if signup_submitted:
                if not name or not new_email or not new_password:
                    st.error("Please fill out all fields.")
                else:
                    data, error = api_signup(name, new_email, new_password)
                    if error:
                        st.error(error)
                    else:
                        st.success(data.get("message", "Registration successful! Please log in."))

# --- 5. Main Application UI (Logged-in User) ---

else:
    # --- Sidebar for Navigation & Logout ---
    st.sidebar.header(f"Welcome, {st.session_state.user_email}!")
    if st.sidebar.button("Logout"):
        # Clear the session state
        st.session_state.token = None
        st.session_state.user_email = None
        st.session_state.user_id = None
        st.rerun() # Re-run to go back to login page

    page = st.sidebar.radio("Navigation", ["Add Data", "Search Data"], horizontal=True)

    # --- "Add Data" Page ---
    if page == "Add Data":
        st.header("Add to your Synapse Brain 🧠")
        
        add_text, add_url, add_image = st.tabs([
            "📝 Add Text", "🔗 Add URL", "🖼️ Add Image"
        ])

        # --- Add Text Form ---
        with add_text:
            with st.form("text_form", clear_on_submit=True):
                text_content = st.text_area("Enter your text snippet:")
                submit_text = st.form_submit_button("Save Text")

                if submit_text and text_content:
                    data_payload = {"data_type": "text", "text": text_content}
                    res, error = api_add_data(st.session_state.token, data_payload)
                    if error:
                        st.error(error)
                    else:
                        st.success(res.get("status", "Successfully added text!"))
                        st.json(res) 

        # --- Add URL Form ---
        with add_url:
            with st.form("url_form", clear_on_submit=True):
                url_content = st.text_input("Enter the URL:")
                submit_url = st.form_submit_button("Save URL")

                if submit_url and url_content:
                    data_payload = {"data_type": "url", "url": url_content}
                    res, error = api_add_data(st.session_state.token, data_payload)
                    if error:
                        st.error(error)
                    else:
                        st.success(res.get("status", "Successfully added URL!"))
                        st.json(res)

        # --- Add Image Form ---
        with add_image:
            with st.form("image_form", clear_on_submit=True):
                uploaded_file = st.file_uploader("Upload an image", type=["png", "jpg", "jpeg", "webp"])
                submit_image = st.form_submit_button("Save Image")

                if submit_image and uploaded_file is not None:
                    # 'files' payload needs to be in a specific format
                    file_payload = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data_payload = {"data_type": "image"}
                    
                    res, error = api_add_data(st.session_state.token, data_payload, file_payload)
                    if error:
                        st.error(error)
                    else:
                        st.success(res.get("status", "Successfully added image!"))
                        st.json(res)
    
    elif page == "Search Data":
        st.header("Search your Synapse Brain 🔍")

        query = st.text_input("What are you looking for?")
        limit = st.slider("Number of results to return", 1, 10, 5)

        if st.button("Search"):
            if not query:
                st.warning("Please enter a search query.")
            else:
                with st.spinner("Searching..."):
                    results, error = api_search_data(st.session_state.token, query, limit)
                    if error:
                        st.error(error)
                    else:
                        st.success(f"Found {results.get('results_found', 0)} results for '{results.get('query')}'")
                        st.divider()
                        if not results.get("results"):
                            st.info("No matching data found.")
                        
                        for res in results.get("results", []):
                            score = res.get('score', 0)
                            with st.expander(f"**{res.get('title', 'Result')}** (Type: {res.get('type')}, Score: {score:.4f})"):
                                st.markdown(f"**Summary:** {res.get('summary', 'N/A')}")
                                
                                if res.get('tags'):
                                    st.write(f"**Tags:** `{'`, `'.join(res.get('tags'))}`")
                                
                                if res.get('category'):
                                    st.write(f"**Category:** {res.get('category')}")
                                
                                if res.get('media_url'):
                                    if res.get('type') == 'image':
                                        st.image(res.get('media_url'), width=200)
                                    else:
                                        st.write(f"**Link:** {res.get('media_url')}")
                                
                                st.write(f"**Saved on:** {res.get('created_at', 'N/A')}")