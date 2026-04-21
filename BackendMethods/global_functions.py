import streamlit as st
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled
from time import sleep
import os
import requests
from PIL import Image
from io import BytesIO

conf_file = ".streamlit/config.toml"
collection_page = "pages/collectionView.py"
sub_coll_page = "pages/subCollView.py"
home_page = "pages/home_page.py"

#st_yled.init(css_path=backEnd.CURR_THEME)
removeCheck = False

thumbnails_path = os.path.join(os.path.dirname(__file__), 'thumbnails')

sounds_path = os.path.join(os.path.dirname(__file__), 'sounds')

THUMNAIL_URLS = {
    "Pokemon": os.path.join(thumbnails_path, "pikachu.jpeg"),
    "Digimon": os.path.join(thumbnails_path, "agumon.jpeg"),
    "Dragonball": os.path.join(thumbnails_path, "goku.jpeg"),
    "Movies": os.path.join(thumbnails_path, "movies.jpeg"),
    "OnePiece": os.path.join(thumbnails_path, "luffy.jpeg"),
    "Custom": os.path.join(thumbnails_path, "barcode.jpeg"),
    "Music": os.path.join(thumbnails_path, "vinyl.jpeg")
}

DEFAULT_SOUNDS = {
    "Delete" : os.path.join(sounds_path, "fading-scream.mp3"),
    "add" : os.path.join(sounds_path, "add.wav"),
}


# Opens file and writes new value for specified variable
def update_config_val(conf:str, var:str, new:str) -> None:
    with open(conf, "r") as f:
        config_lines = f.readlines()

        line_number = 0
        for line in config_lines:
            if var in line:
                config_lines[line_number] = f"{var}=\"{new}\"\n"
            line_number += 1

    with open(conf, "w") as f:
        f.writelines(config_lines)


# A check to not adjust "theme" in config file (should be in database)
def update_settings(conf:str, diction:dict) -> None:
    for setting in diction:
        if setting != "theme":
            update_config_val(conf, setting, diction[setting])


# Opens config file and reads the value of a specified variable
def read_config_val(conf:str, var:str) -> str:
    with open(conf, "r") as f:
        config_lines = f.readlines()

        for line in config_lines:
            if var in line:
                result_list = line.split('"')

    return result_list[1]


# Updates config data to match database data
def db_settings_to_config(user_data_dict:dict):
    # list of variables in both db and config
    variables_to_update = ["base", "backgroundColor", "textColor", "font"]

    # list of values of variables above
    config_data = []
    db_data = []
    for var in variables_to_update:
        config_data.append(read_config_val(conf_file, var))
        db_data.append(user_data_dict[var])


    for i in range(len(variables_to_update)):
        if config_data[i] != db_data[i]:
            update_config_val(conf_file, variables_to_update[i], db_data[i])

    sleep(0.25)
    if config_data != db_data:
        st.rerun()

background_image_flag = True



# Sets the page width, title, and buttons for home, search, settings
# To be used at the start of any page
def page_initialization(user_data_dict:dict):
    is_test_mode = os.getenv("STREAMLIT_TEST_MODE", "false").lower() == "true"
    # Check if running in test mode (AppTest sets a marker)
    if is_test_mode:
        user_data_dict = {"backgroundImageURL": "https://i.ytimg.com/vi/DE6wyfsTfFI/maxresdefault.jpg"}
    
    css = f'''
        <style>
            .stApp {{
                background-image: linear-gradient(to top, {read_config_val(conf_file, "textColor")}, transparent),
                url({user_data_dict["backgroundImageURL"]});
                background-size: cover;

            }}
            .stApp > header {{
                background-color: transparent;
            }}

            .stAudio {{
                display: none;
            }}

            .stPageLink {{
                color: {read_config_val(conf_file, "textColor")};
                background-color: {read_config_val(conf_file, "backgroundColor")};
            }}
        </style>
        '''
    icon_cols = st.columns([1, 1, 1], width=100)
    with icon_cols[0]:
        if st.button("", icon=":material/no_sound:", type="secondary", key="mute_button"):
            st.session_state.muted = True
    with icon_cols[1]:
        if st.button("", icon=":material/sound_detection_loud_sound:", type="secondary", key="unmute_button"):
            st.session_state.muted = False
            st.rerun()
        else:
            if not st.session_state.muted:
                with icon_cols[2]:
                    st.audio(os.path.join(sounds_path, "ambient.mp3"), autoplay=True, loop=True, width=1)

    st.set_page_config(layout="wide")
    st_yled.init()
    if background_image_flag is True:
        st.markdown(css, unsafe_allow_html=True)

    st_yled.title(_("Memorabiliacs"), text_alignment="center")

    with st.container(horizontal=True, vertical_alignment="top"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if st_yled.button(_("Home"), key="home_button"):
                backEnd.set_collection("")
                backEnd.set_sub_collection("")
                st.switch_page("pages/home_page.py")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st_yled.button(_("Search"), key="search_button"):
                st.switch_page("pages/search.py")

def base_theme_threshold(hex_num:str) -> str:
    r = int(hex_num[1:3], 16)
    g = int(hex_num[3:5], 16)
    b = int(hex_num[5:], 16)
    brightness = ((r*299)+(g*587)+(b*114))/1000
    return "dark" if brightness >= 128 else "light"


def apply_css_theme(theme):
    st_yled.init()
    match theme:
        case "Original": 
            st_yled.set("button", "background_color", "#3498db")
            st_yled.set("button", "border_style", "solid")
        case "Memorabiliac":
            st_yled.set("button", "background_color", "#e74c3c")
            st_yled.set("button", "border_style", "dashed")
        case "Logan":
            st_yled.set("button", "background_color", "#2ecc71")
            st_yled.set("button", "border_style", "dotted")
        case "Cooper":
            st_yled.set("button", "background_color", "#9b59b6")
            st_yled.set("button", "border_style", "double")
        case "Custom":
            st_yled.set("button", "background_color", "#ffff00")
            st_yled.set("button", "border_style", "solid")


# Used for input sanitation of collection names
def collection_input_sanitation(coll_name:str):
    valid = True
    if coll_name.__contains__("_"):
        return not valid
    if coll_name.__contains__("/"):
        return not valid
    if coll_name.__contains__("\\"):
        return not valid
    if coll_name.__contains__("-"):
        return not valid

    return valid


# Ensures url is of proper types
@st.cache_data(show_spinner=False, ttl=3600)
def get_image_from_URL(url:str):
    r = requests.get(url)
    return Image.open(BytesIO(r.content))
