###############################################################
#   Author(s): Cooper Wooten, Kieran Gilpin
#   Desc: Basic version of login page for memorabiliacs using streamlit
###############################################################
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled


#st.secrets = authFuncs.access_secret_version()
# st_yled.init(css_path=".streamlit/st-styled.css")
# st_yled.init(backEnd.CURR_THEME)
st_yled.init()
    
background_image = "https://gamewardbound.com/wp-content/uploads/2020/11/ikea-kallax-shelves-complete-second-shelf.jpg"
css = f'''
    <style>
        .stApp {{
            background-image: linear-gradient(to top, {gfuncs.read_config_val( "textColor")}, transparent),
            url({background_image});
            background-size: cover;

        }}
        .stApp > header {{
            background-color: transparent;
        }}
    </style>
    '''
st.markdown(css, unsafe_allow_html=True)
st.set_page_config(layout="wide")
# Initialize Firestore client
# The credentials are grabbed from Streamlit secrets
try:
    db = backEnd.get_firestore_client()
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

st_yled.title(_("Welcome to Memorabiliacs!"), text_alignment="center")

if 'user_info' not in st.session_state:
    authFuncs.generate_login_template(db)
## -------------------------------------------------------------------------------------------------
## Logged in --------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    gfuncs.login_color_flag = 0
    st.session_state.muted = False
    st.switch_page("pages/home_page.py")