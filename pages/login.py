###############################################################
#   Author(s): Cooper Wooten, Kieran Gilpin
#   Desc: Basic version of login page for memorabiliacs using streamlit
###############################################################
import json
import os

import streamlit as st
import BackendMethods.global_functions as gfuncs
from google.cloud import firestore
from BackendMethods.auth_functions import (
    create_account,
    delete_account,
    reset_password,
    sign_in,
    generate_login_template,
    sign_out,
)
from BackendMethods.backendfuncs import (
    get_cards2,
    search_internetarchive,
    generate_collection,
    search_movies,
    access_secret_version,
)
st.secrets = access_secret_version()

st.set_page_config(layout="wide")
# Initialize Firestore client
# The credentials are grabbed from Streamlit secrets
try:
    db = firestore.Client.from_service_account_info(st.secrets["firebase"])
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

st.title("Welcome to Memorabiliacs!", text_alignment="center")

if 'user_info' not in st.session_state:
    generate_login_template(db)
## -------------------------------------------------------------------------------------------------
## Logged in --------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    gfuncs.login_color_flag = 0
    st.switch_page("pages/home_page.py")