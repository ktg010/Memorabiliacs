import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _, set_language
import st_yled
from time import sleep
import os
 
try:
    newdb = backEnd.get_firestore_client()
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

# st_yled.init(CURR_THEME)
st_yled.init()

is_test_mode = os.getenv("STREAMLIT_TEST_MODE", "false").lower() == "true"
# user sign-in check
if 'user_info' not in st.session_state:
    # Check if running in test mode (AppTest sets a marker)
    if is_test_mode:
        st.session_state.user_info = {
            "localId": "test_user_123",
            "email": "test@example.com"
        }
        st.session_state["muted"] = False  # Add this line
    else:
        st.switch_page("pages/login.py")
## -------------------------------------------------------------------------------------------------
## Logged in --------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:

    # Specifies the config file that will be read from and written to
    conf_file = os.path.join(os.path.dirname(__file__), '..',  '.streamlit', 'config.toml')
    #conf_file = ".streamlit/config.toml"

    user_id = st.session_state.user_info["localId"]

    # Creates header with Home and Logout options
    # This is separate from the usual page initialization because settings 
    # does not need a link to settings and we instead want to logout from settings
    with st.container(horizontal=True, vertical_alignment="top"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if st_yled.button(_("Home"), key="home_button"):
                st.switch_page("pages/home_page.py")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st_yled.button(_("Logout"), key="logout_button"):
                backEnd.set_collection("")
                authFuncs.sign_out()
                st.switch_page("pages/login.py")


    st_yled.title(_("Settings"), text_alignment="center")

    st.set_page_config(layout="wide")
    st_yled.init()


    # Language selector
    with st.container(horizontal_alignment="left", vertical_alignment="top"):
        lang_display_to_code = {"English": "en", "Español": "es", "Français": "fr", "中文": "zh_CN", "tlhIngan Hol": "tlh"}
        code_to_display = {v: k for k, v in lang_display_to_code.items()}
        current_lang = st.session_state.get('language', 'en')
        current_lang_display = code_to_display.get(current_lang, "English")
        selected_lang = st_yled.selectbox(_("Select Language:"), options=list(lang_display_to_code.keys()), index=list(lang_display_to_code.keys()).index(current_lang_display), key="language_selectbox")
        if selected_lang != current_lang_display:
            lang_code = lang_display_to_code[selected_lang]
            set_language(lang_code)
            # Save to database
            newdb.collection("Users").document(user_id).set({"language": lang_code}, merge=True)
            backEnd.get_user_data.clear(user_id)
            st.rerun()

    # Grabs settings from database
    # Also grabs current configuration data from config file
    db_settings = backEnd.get_user_data(user_id)
    current_base = gfuncs.read_config_val( "base")
    current_background_color = gfuncs.read_config_val( "backgroundColor")
    current_text_color = gfuncs.read_config_val( "textColor")
    current_font = gfuncs.read_config_val( "font")
    # Theme is special in that it exists in the database but not the config file
    current_theme = db_settings["theme"]
    #gfuncs.apply_css_theme(current_theme)

    # List of available themes and the dictionaries for the themes
    # (Currently hardcoded)
    theme_list = ["Original", "Memorabiliac", "Paper", "Logan", "Cooper", "Custom"]
    theme_original = {"base" : "dark", 
                      "backgroundColor" : "#1a1a1a",
                      "textColor" : "#dddddd",
                      "font" : "Roboto:https://fonts.cdnfonts.com/css/roboto",
                      "theme" : "Original"}
    theme_memorabiliac = {"base" : "dark", 
                      "backgroundColor" : "#636363",
                      "textColor" : "#00ff22",
                      "font" : "'Comic Sans MS':https://fonts.cdnfonts.com/css/sans-comic-sans",
                      "theme" : "Memorabiliac"}
    theme_paper = {"base" : "light", 
                      "backgroundColor" : "#f1e7c8",
                      "textColor" : "#242424",
                      "font" : "'Patrick Hand':https://fonts.cdnfonts.com/css/patrick-hand",
                      "theme" : "Paper"}
    theme_logan = {"base" : "light", 
                      "backgroundColor" : "#b1a8a8",
                      "textColor" : "#1733f7",
                      "font" : "Roboto:https://fonts.cdnfonts.com/css/roboto",
                      "theme" : "Logan"}
    theme_cooper = {"base" : "dark", 
                      "backgroundColor" : "#76767b",
                      "textColor" : "#ff9600",
                      "font" : "Roboto:https://fonts.cdnfonts.com/css/roboto",
                      "theme" : "Cooper"}
    theme_custom = {"base" : current_base,
                    "backgroundColor" : current_background_color,
                    "textColor" : current_text_color,
                    "font" : current_font,
                    "theme" : "Custom"}
    # Dictionary matching database name of dictionary to hardcoded dict
    theme_dict = {"Original" : theme_original,
                  "Memorabiliac" : theme_memorabiliac,
                  "Paper" : theme_paper,
                  "Logan" : theme_logan,
                  "Cooper" : theme_cooper,
                  "Custom" : theme_custom}

    css_dict = {"Original": ".streamlit/st-styled.css",
                "Memorabiliac": ".streamlit/memorabiliac.css"}
    
    font_dict = {'Noto Serif' : "'Noto Serif':https://fonts.cdnfonts.com/css/noto-serif",
                 'Roboto' : "Roboto:https://fonts.cdnfonts.com/css/roboto",
                 'Glook' : "Glook:https://fonts.cdnfonts.com/css/gloock-2",
                 'Rubik' : "Rubik:https://fonts.cdnfonts.com/css/rubik-2",
                 'JUMBOTRON' : "JUMBOTRON:https://fonts.cdnfonts.com/css/jumbotron"}
    font_name_list = list(font_dict.keys())


    # Select box for themes and a button to save theme choice
    with st.container(horizontal_alignment="left", vertical_alignment="top"):
        color_theme = st_yled.selectbox(_("Select color scheme:"), theme_list, index = theme_list.index(current_theme), key="theme_selectbox")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st_yled.button(_("Save Theme Choice"), key="save_theme_button"):
                #setTheme(css_dict[color_theme])
                gfuncs.update_settings(theme_dict[color_theme])
                newdb.collection("Users").document(user_id).set(theme_dict[color_theme], merge=True)
                #gfuncs.apply_css_theme(color_theme)
                backEnd.get_user_data.clear(user_id)
                sleep(0.25)
                st.rerun()
                


    # Popover button for advanced settings with editing available for 
    # Background color, text color, and font
    with st.popover(_("Advanced Settings")):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            background_color_choice = st.color_picker(_("Select the background color:"), current_background_color)
            text_color_choice = st.color_picker(_("Select the text color:"), current_text_color)
            font_choice = st_yled.selectbox(_("Select the font:"), font_name_list, 
                                            index=font_name_list.index(current_font) if current_font in font_name_list else 0,
                                            key = "theme_select")
            base_choice = gfuncs.base_theme_threshold(text_color_choice)

        # Save button both writes to config file to show changes, 
        # and writes changes to database for consistency between states
        with st.container(horizontal_alignment="right", vertical_alignment="bottom"):
            if st_yled.button(_("Save Changes"), key="save_advanced_button"):
                st.session_state["base"] = base_choice
                st.session_state["backgroundColor"] = background_color_choice
                st.session_state["textColor"] = text_color_choice
                st.session_state["font"] = font_dict[font_choice]
                # gfuncs.update_config_val(conf_file, "base", "dark" if base_choice=="dark" else "light")
                # gfuncs.update_config_val(conf_file, "backgroundColor", background_color_choice)
                # gfuncs.update_config_val(conf_file, "textColor", text_color_choice)
                # gfuncs.update_config_val(conf_file, "font", font_dict[font_choice])
                newdb.collection("Users").document(user_id).set({"base" : base_choice, 
                                                                "backgroundColor" : background_color_choice, 
                                                                "textColor" : text_color_choice,
                                                                "font" : font_choice,
                                                                "theme" : "Custom"},
                                                                merge=True)
                backEnd.get_user_data.clear(user_id)
                sleep(0.25)
                st.rerun()
    with st.popover(_("Background Image Settings")):
        new_image_URL = st.text_input(("URL of image to be used for background: "), value=db_settings["backgroundImageURL"])

        if st.checkbox(_("Toggle Background Image"), value=db_settings["backgroundImageFlag"], key="toggle_background"):
            newdb.collection("Users").document(user_id).set({"backgroundImageFlag" : True}, merge=True)
            st.session_state["backgroundImageFlag"] = True
        else:
            newdb.collection("Users").document(user_id).set({"backgroundImageFlag" : False}, merge=True)
            st.session_state["backgroundImageFlag"] = False

        if st_yled.button(_("Save Background Image Changes"), key="save_background_button"):
            if new_image_URL != "" and "https:" in new_image_URL: 
                newdb.collection("Users").document(user_id).set({"backgroundImageURL" : new_image_URL}, merge=True)
                st.session_state["backgroundImageURL"] = new_image_URL
            backEnd.get_user_data.clear(user_id)
            sleep(0.25)
            st.rerun()
