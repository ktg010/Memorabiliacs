import streamlit as st
import BackendMethods.global_functions as gfuncs
from google.cloud import firestore
import BackendMethods.auth_functions as authFuncs
from BackendMethods.backendfuncs import (
    get_cards2,
    search_internetarchive,
    generate_collection,
    search_movies,
    generate_login_template,
    setCollection
)

try:
    newdb = firestore.Client.from_service_account_info(st.secrets["firebase"])
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

if 'user_info' not in st.session_state:
    st.switch_page("pages/login.py")
## -------------------------------------------------------------------------------------------------
## Logged in --------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:

    # Specifies the config file that will be read from and written to
    conf_file = ".streamlit/config.toml"

    user_id = st.session_state.user_info["localId"]

    # Creates header with Home and Logout options
    # This is separate from the usual page initialization because settings 
    # does not need a link to settings and we instead want to logout from settings
    with st.container(horizontal=True, vertical_alignment="top"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if st.button("Home"):
                st.switch_page("pages/home_page.py")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st.button("Logout"):
                setCollection("")
                authFuncs.sign_out()
                st.switch_page("pages/login.py")


    st.title("Settings", text_alignment="center")

    st.set_page_config(layout="wide")

    # Grabs settings from database
    # Also grabs current configuration data from config file
    db_settings = newdb.collection("Users").document(user_id).get().to_dict()
    current_base = gfuncs.read_config_val(conf_file, "base")
    current_background_color = gfuncs.read_config_val(conf_file, "backgroundColor")
    current_text_color = gfuncs.read_config_val(conf_file, "textColor")
    current_font = gfuncs.read_config_val(conf_file, "font")
    # Theme is special in that it exists in the database but not the config file
    current_theme = db_settings["theme"]

    # List of available themes and the dictionaries for the themes
    # (Currently hardcoded)
    theme_list = ["Original", "Memorabiliac", "Paper", "Logan", "Cooper", "Custom"]
    theme_original = {"base" : "dark", 
                      "backgroundColor" : "#cacaca",
                      "textColor" : "#4caeff",
                      "font" : "sans-serif",
                      "theme" : "Original"}
    theme_memorbiliac = {"base" : "dark", 
                      "backgroundColor" : "#636363",
                      "textColor" : "#00ff22",
                      "font" : "sans-serif",
                      "theme" : "Memorabiliac"}
    theme_paper = {"base" : "light", 
                      "backgroundColor" : "#ffe598",
                      "textColor" : "#000000",
                      "font" : "serif",
                      "theme" : "Paper"}
    theme_logan = {"base" : "light", 
                      "backgroundColor" : "#b1a8a8",
                      "textColor" : "#1733f7",
                      "font" : "sans-serif",
                      "theme" : "Logan"}
    theme_cooper = {"base" : "dark", 
                      "backgroundColor" : "#76767b",
                      "textColor" : "#ff9600",
                      "font" : "sans-serif",
                      "theme" : "Cooper"}
    theme_custom = {"base" : current_base,
                    "backgroundColor" : current_background_color,
                    "textColor" : current_text_color,
                    "font" : current_font,
                    "theme" : "Custom"}
    # Dictionary matching database name of dictionary to hardcoded dict
    theme_dict = {"Original" : theme_original,
                  "Memorabiliac" : theme_memorbiliac,
                  "Paper" : theme_paper,
                  "Logan" : theme_logan,
                  "Cooper" : theme_cooper,
                  "Custom" : theme_custom}


    # Select box for themes and a button to save theme choice
    with st.container(horizontal_alignment="left", vertical_alignment="top"):
        color_theme = st.selectbox("Select color scheme: ", theme_list, index = theme_list.index(current_theme))
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st.button("Save Theme Choice"):
                gfuncs.update_settings(conf_file, theme_dict[color_theme])
                newdb.collection("Users").document(user_id).set(theme_dict[color_theme], merge=True)
                st.rerun()


    # Popover button for advanced settings with editing available for 
    # Background color, text color, and font
    with st.popover("Advanced Settings"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if current_base == "dark":
                base_choice = st.selectbox("Select base theme for app: ", ("Dark", "Light")).lower()
            else:
                base_choice = st.selectbox("Select base theme for app: ", ("Light", "Dark")).lower()

            background_color_choice = st.color_picker("Select the background color: ", current_background_color)
            text_color_choice = st.color_picker("Select the text color: ", current_text_color)
            font_choice = st.selectbox("Select the font: ", ("serif", "sans-serif"), index=0 if current_font == "serif" else 1)

        # Save button both writes to config file to show changes, 
        # and writes changes to database for consistency between states
        with st.container(horizontal_alignment="right", vertical_alignment="bottom"):
            if st.button("Save Changes"):
                gfuncs.update_config_val(conf_file, "base", "dark" if base_choice=="dark" else "light")
                gfuncs.update_config_val(conf_file, "backgroundColor", background_color_choice)
                gfuncs.update_config_val(conf_file, "textColor", text_color_choice)
                gfuncs.update_config_val(conf_file, "font", font_choice)
                newdb.collection("Users").document(user_id).set({"base" : base_choice, 
                                                                "backgroundColor" : background_color_choice, 
                                                                "textColor" : text_color_choice,
                                                                "font" : font_choice,
                                                                "theme" : "Custom"},
                                                                merge=True)
                st.rerun()

