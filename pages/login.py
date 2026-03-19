###############################################################
#   Author(s): Cooper Wooten, Kieran Gilpin
#   Desc: Basic version of login page for memorabiliacs using streamlit
###############################################################
import json
import os

import streamlit as st
import BackendMethods.global_functions as gfuncs
from google.cloud import firestore
from BackendMethods.auth_functions import *
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled


st.secrets = access_secret_version()
# st_yled.init(css_path=".streamlit/st-styled.css")
# st_yled.init(backEnd.CURR_THEME)
st_yled.init()
st.set_page_config(layout="wide")
# Initialize Firestore client
# The credentials are grabbed from Streamlit secrets
try:
    db = firestore.Client.from_service_account_info(st.secrets["firebase"])
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

st_yled.title(_("Welcome to Memorabiliacs!"), text_alignment="center")

if 'user_info' not in st.session_state:
    generate_login_template(db)
## -------------------------------------------------------------------------------------------------
## Logged in --------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    gfuncs.login_color_flag = 0
    st.switch_page("pages/home_page.py")