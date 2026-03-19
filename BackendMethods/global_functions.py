import streamlit as st
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled

# login_color_flag = 0
conf_file = ".streamlit/config.toml"
collection_page = "pages/collectionView.py"

removeCheck = False
#st_yled.init(css_path=backEnd.CURR_THEME)

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

# Sets the page width, title, and buttons for home, search, settings
# To be used at the start of any page
def page_initialization(user_data_dict:dict):
    st.set_page_config(layout="wide")
    st_yled.init()
    st_yled.title(_("Memorabiliacs"), text_alignment="center")
    config_changes_list = ("base", "backgroundColor", "textColor", "font")

    current_config_data = list()
    for data in config_changes_list:
        current_config_data.append(read_config_val(conf_file, data))

    for change in config_changes_list:
        if change == current_config_data[config_changes_list.index(change)]:
            update_config_val(conf_file, change, user_data_dict[change])
            st.rerun()
    # update_config_val(conf_file, "base", user_data_dict["base"])
    # update_config_val(conf_file, "backgroundColor", user_data_dict["backgroundColor"])
    # update_config_val(conf_file, "textColor", user_data_dict["textColor"])
    # if login_color_flag == 0:
    #     login_color_flag = 1
    #     st.rerun()

    with st.container(horizontal=True, vertical_alignment="top"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if st_yled.button(_("Home"), key="home_button"):
                st.switch_page("pages/home_page.py")
        with st.container(horizontal_alignment="center", vertical_alignment="top"):
            if st_yled.button(_("Search"), key="search_button"):
                st.switch_page("pages/search.py")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st_yled.button(_("Settings"), key="settings_button"):
                st.switch_page("pages/settings.py")
        

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
