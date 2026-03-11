import streamlit as st
import BackendMethods.auth_functions as authFuncs

login_color_flag = 0


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
def page_initialization():
    st.set_page_config(layout="wide")
    st.title("Memorabiliacs", text_alignment="center")
    with st.container(horizontal=True, vertical_alignment="top"):
        with st.container(horizontal_alignment="left", vertical_alignment="top"):
            if st.button("Home"):
                st.switch_page("pages/home_page.py")
        with st.container(horizontal_alignment="center", vertical_alignment="top"):
            if st.button("Search"):
                st.switch_page("pages/search.py")
        with st.container(horizontal_alignment="right", vertical_alignment="top"):
            if st.button("Settings"):
                st.switch_page("pages/settings.py")
        