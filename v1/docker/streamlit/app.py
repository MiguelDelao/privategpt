"""
PrivateGPT Legal AI - Authentication
Professional login interface for legal AI platform
"""

import streamlit as st
import time
from datetime import datetime
from utils.auth_client import AuthClient
from utils.logger import Logger
from pages_utils import (
    APP_TITLE,
    initialize_session_state,
    get_auth_client,
    get_logger
)

# Page configuration
st.set_page_config(
    page_title="PrivateGPT - Legal AI Platform",
    page_icon="🔐",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Initialize session state
initialize_session_state()

    # ChatGPT-style professional dark theme
st.markdown("""
<style>
    /* Hide ALL Streamlit UI elements */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppDeployButton {display: none;}
    [data-testid="stDecoration"] {display: none;}
    [data-testid="stHeader"] {display: none;}
    [data-testid="stToolbar"] {display: none;}
    [data-testid="stStatusWidget"] {display: none;}
    
    /* ChatGPT-style dark background */
    .stApp {
        background-color: #0D1117 !important;
        color: #E6EDF3 !important;
    }
    
    html, body, [class*="css"] {
        font-family: 'Söhne', -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif !important;
    }
    
    /* Main container styling */
    .main .block-container {
        padding-top: 4rem !important;
        padding-bottom: 2rem !important;
        max-width: 400px !important;
        margin: 0 auto !important;
    }
    
    /* Title styling - ChatGPT style */
    h1 {
        color: #E6EDF3 !important;
        font-size: 2rem !important;
        font-weight: 600 !important;
        text-align: center !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: -0.025em !important;
    }
    
    /* Subtitle styling */
    .stMarkdown p {
        color: #7D8590 !important;
        font-size: 0.875rem !important;
        text-align: center !important;
        margin-bottom: 2rem !important;
        font-weight: 400 !important;
    }
    
    /* Form container */
    .stForm {
        background-color: #161B22 !important;
        border: 1px solid #30363D !important;
        border-radius: 12px !important;
        padding: 2rem !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15) !important;
    }
    
    /* Input labels */
    .stTextInput label,
    .stForm label {
        color: #F0F6FC !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Input fields - ChatGPT style */
    .stTextInput input {
        background-color: #0D1117 !important;
        border: 1px solid #30363D !important;
        border-radius: 8px !important;
        color: #E6EDF3 !important;
        padding: 0.75rem !important;
        font-size: 0.875rem !important;
        transition: border-color 0.2s ease !important;
    }
    
    .stTextInput input:focus {
        border-color: #58A6FF !important;
        box-shadow: 0 0 0 2px rgba(88, 166, 255, 0.1) !important;
        outline: none !important;
    }
    
    /* Password field eye icon - subtle gray */
    .stTextInput button,
    button[data-testid="textInputButton"] {
        background-color: transparent !important;
        border: none !important;
        color: #7D8590 !important;
    }
    
    .stTextInput button:hover,
    button[data-testid="textInputButton"]:hover {
        color: #C9D1D9 !important;
    }
    
    .stTextInput button svg {
        fill: #7D8590 !important;
    }
    
    .stTextInput button:hover svg {
        fill: #C9D1D9 !important;
    }
    
    /* Sign In button - ChatGPT style */
    .stFormSubmitButton button,
    button[kind="primaryFormSubmit"] {
        background: linear-gradient(135deg, #2D333B 0%, #21262D 100%) !important;
        color: #E6EDF3 !important;
        border: 1px solid #444C56 !important;
        border-radius: 8px !important;
        padding: 0.75rem 1.5rem !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        width: 100% !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
    }
    
    .stFormSubmitButton button:hover,
    button[kind="primaryFormSubmit"]:hover {
        background: linear-gradient(135deg, #373E47 0%, #2D333B 100%) !important;
        border-color: #656C76 !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
    }
    
    .stFormSubmitButton button:active,
    button[kind="primaryFormSubmit"]:active {
        transform: translateY(0) !important;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.1) !important;
    }
    
    /* Error messages */
    .stAlert {
        background-color: #1F2937 !important;
        border: 1px solid #DC2626 !important;
        border-radius: 8px !important;
        color: #FCA5A5 !important;
    }
    
    /* Success messages */
    .stSuccess {
        background-color: #1F2937 !important;
        border: 1px solid #059669 !important;
        border-radius: 8px !important;
        color: #6EE7B7 !important;
    }
    
    /* Spinner */
    .stSpinner {
        color: #58A6FF !important;
    }
    
    /* Remove any unwanted margins and padding */
    .css-1d391kg {
        padding: 0 !important;
    }
    
    /* Center everything */
    .main {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 100vh !important;
    }
    
    /* Hide sidebar completely for login */
    .stSidebar {
        display: none !important;
    }
    
         /* Placeholder text styling */
     .stTextInput input::placeholder {
         color: #7D8590 !important;
         opacity: 1 !important;
     }
     
     /* Hide "Press Enter to apply" tooltip */
     .stTextInput [data-testid="InputInstructions"] {
         display: none !important;
     }
     
     .stTextInput .instructions {
         display: none !important;
     }
     
     [data-testid="stTextInputInstructions"] {
         display: none !important;
     }
     
     /* Hide any floating instruction text */
     .stTextInput [title*="Press Enter"],
     .stTextInput [title*="enter"],
     [data-baseweb="input"] [data-testid="instructions"] {
         display: none !important;
     }
     
     /* Hide tooltip/hint messages */
     .stTooltip,
     [data-testid="stTooltip"],
     [data-testid="tooltip"] {
         display: none !important;
     }
</style>

<script>
    // Disable Enter key form submission
    document.addEventListener('DOMContentLoaded', function() {
        // Function to disable Enter key on forms
        function disableEnterKey() {
            const form = document.querySelector('form[data-testid="stForm"]');
            const inputs = document.querySelectorAll('.stTextInput input');
            
            // Add event listener to each input field
            inputs.forEach(function(input) {
                input.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' || e.keyCode === 13) {
                        e.preventDefault();
                        e.stopPropagation();
                        return false;
                    }
                });
            });
            
            // Also add listener to the form itself
            if (form) {
                form.addEventListener('keypress', function(e) {
                    if (e.key === 'Enter' || e.keyCode === 13) {
                        // Only prevent if not clicking the submit button
                        if (e.target.type !== 'submit') {
                            e.preventDefault();
                            e.stopPropagation();
                            return false;
                        }
                    }
                });
            }
        }
        
        // Run initially
        disableEnterKey();
        
        // Re-run when page updates (Streamlit re-renders)
        const observer = new MutationObserver(function(mutations) {
            disableEnterKey();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    });
</script>
""", unsafe_allow_html=True)

def display_login_page():
    """Display the clean login interface"""
    auth_client = get_auth_client()
    logger = get_logger()

    # Redirect if already authenticated
    if st.session_state.get("authenticated", False):
        st.switch_page("pages/dashboard.py")
        return

    # Simple Streamlit header
    st.title("PrivateGPT")

    # Login form
    with st.form(key="login_form", clear_on_submit=False):
        email = st.text_input(
            label="Email",
            placeholder="Enter your email address",
            key="login_email_input",
            value=st.session_state.get("login_form_email", "admin@admin.com")
        )
        
        password = st.text_input(
            label="Password",
            type="password",
            placeholder="Enter your password",
            key="login_password_input",
            value=st.session_state.get("login_form_password", "admin")
        )

        # Store form values in session state
        st.session_state.login_form_email = email
        st.session_state.login_form_password = password

        submitted = st.form_submit_button("Sign In", type="primary")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Signing in..."):
                    try:
                        response = auth_client.login(email, password)
                        if response and response.get("access_token"):
                            # Set authentication state
                            st.session_state.authenticated = True
                            st.session_state.access_token = response["access_token"]
                            user_data = response.get("user", {})
                            st.session_state.user_email = user_data.get("email", email)
                            st.session_state.user_role = user_data.get("role", "user")
                            st.session_state.login_time = datetime.now()
                            
                            # Clear form data
                            if "login_form_email" in st.session_state:
                                del st.session_state.login_form_email
                            if "login_form_password" in st.session_state:
                                del st.session_state.login_form_password
                            if "login_error_message" in st.session_state:
                                del st.session_state.login_error_message

                            # Log successful login
                            logger.log_user_login(user_email=email, success=True)
                            
                            st.switch_page("pages/dashboard.py")
                        else:
                            error_message = response.get("detail", "Invalid credentials.")
                            st.session_state.login_error_message = error_message
                            logger.log_user_login(user_email=email, success=False, error_message=error_message)
                    except Exception as e:
                        error_msg = f"{str(e)}"
                        st.session_state.login_error_message = error_msg
                        logger.log_user_login(user_email=email, success=False, error_message=error_msg)

    # Display error if exists
    if "login_error_message" in st.session_state and st.session_state.login_error_message:
        st.error(st.session_state.login_error_message)
        if st.button("Dismiss", key="dismiss_login_error"):
            del st.session_state.login_error_message
            st.rerun()

if __name__ == "__main__":
    display_login_page()

    # Handle post-login redirect
    if st.session_state.get("authenticated"):
        st.switch_page("pages/dashboard.py") 