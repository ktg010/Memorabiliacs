import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
from BackendMethods.translations import set_language
import st_yled
import os
from time import sleep

# Connects to db
try:
    db = backEnd.get_firestore_client()
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

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
## Logged in ---------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    # page variables
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    collections_docs = backEnd.get_user_collections(user_id)
    fullCollections = [doc['id'] for doc in collections_docs if doc['id'].split("_")[0] != "DefaultCollection"]
    removedCollections = []

    # page initialization
    backEnd.set_collection("")
    user_lang = user_data_dict.get('language', 'en')
    set_language(user_lang)
    gfuncs.db_settings_to_session_state(user_data_dict)
    st_yled.init()
    gfuncs.page_initialization(user_data_dict)
    gfuncs.apply_homepage_css()

    ### Sidebar ###
    with st.sidebar:
        st.space("small")

        # displays all collections as button to traverse
        st.header(_("All Collections:"))
        for coll in fullCollections:
            if st.button(f"{coll.split("_")[0]}", type="tertiary", width="stretch"):
                backEnd.set_collection(coll)
                sleep(0.5)
                st.switch_page(gfuncs.collection_page)
        st.space("small")

        # user settings button
        if st.button(icon=":material/settings:", label=_("Settings")):
            st.switch_page("pages/settings.py")

        # VERY IMPORTANT ANIMATION
        gfuncs.apply_marty_animation()


    ### Dialog Popups ###
    # change the name of the collection
    @st.dialog(_("Edit")) 
    def edit_collection(coll):
        # Split view for different settings
        itemSettings, rename = st.columns([3,2])

        with itemSettings:
            ref = db.collection("Users").document(user_id).collection("Collections").document(coll["id"])

            # hidden select
            hidden = st.checkbox(_("Hide Collection"))

            # background image
            new_image_URL = st.text_input(_("URL of image to be used for background: "), value=ref.get().to_dict().get("settings").get("background"))

        with rename:
            st_yled.subheader(f"{_('Rename')} {coll["id"].split('_')[0]}?", text_alignment="center") 
            coll_rename = st.text_input(" ")

        with st.container(horizontal=True, horizontal_alignment="right"):
            # Updates all changes to db
            if st.button(_("Save")):
                ref.update({"settings.hidden" : hidden})

                # background image 
                if new_image_URL != "" and "https:" in new_image_URL: 
                    ref.update({"settings.background" : new_image_URL})

                # rename checks
                if coll_rename != "":
                    if backEnd.rename_collection(coll["id"], coll_rename):
                        st_yled.error(_("Collection name already exists"))
                    else:
                        backEnd.get_user_collections.clear(user_id)
                        st.rerun()
                else:
                    st.rerun()
                
    # adding a new collection to the db
    @st.dialog(_("Add"))
    def add_collection():
        name = st.text_input(_("Name the Collection"))
        collType = st.selectbox(_("Type"), backEnd.get_collection_types())

        if st_yled.button(_("Add"), key="makeColl") and name is not None and collType is not None:
            # checks for proper characters in name
            if gfuncs.collection_input_sanitation(name):
                
                # split for custom collection
                if collType == "Custom":
                    if backEnd.create_custom_collection(name, collType):
                        st_yled.error(_("Collection name already exists"))
                    else:
                        backEnd.get_user_collections.clear(user_id)
                        st.rerun()
                else:
                    if backEnd.create_collection(name, collType):
                        st_yled.error(_("Collection name already exists"))
                    else:
                        backEnd.get_user_collections.clear(user_id)
                        st.rerun()
            else: 
                st_yled.error(_("Invalid character in name: '_', '-', '\\', '/'"))

    # remove a collection from the db
    @st.dialog(_("Remove")) 
    def remove_collections(): 
        # Displays all selected collections
        st_yled.subheader(f"{_('Are you sure you want to remove')} {_('the following collections:')}", text_alignment="center")
        for coll in removedCollections:
            st.write(coll.split("_")[0])
        
        with st.container(horizontal=True, horizontal_alignment="center"):
            # iterates through list to delete all collections
            if st_yled.button(_("Yes"), key="confirmRemove", width="content"):
                for coll in removedCollections:
                    coll_type = coll.split("_")[1]
                    if coll_type == "Custom":
                        db.collection("Custom").document(coll).delete()
                    backEnd.delete_collection(coll)
                removedCollections.clear()
                backEnd.get_user_collections.clear()
                st.rerun()

            if st_yled.button(_("No"), key="cancelRemove", width="content"):
                gfuncs.removeCheck = False
                st.rerun()


    ### Main Page Display ###
    # title
    st.space("small")
    with st.container( horizontal_alignment="center"):
        st_yled.text(f"{_('Your Collections')}", text_alignment="center", font_size="1.75rem")
        st_yled.text(f"{_('Hello')}, {st.session_state.user_info['email']}!", text_alignment="center", font_size="1rem")
    st.space("small")
    
    # Center section for collections
    with st.container(horizontal=True, horizontal_alignment="center"):
        # iterate through collections
        for doc in collections_docs:
            collInfo = doc['id'].split('_')

            # gets local list of all collections
            if collInfo[0] != "DefaultCollection": 
                fullCollections.append(doc['id'])
            
            # only display collection if it is marked as visable
            if backEnd.coll_visability(doc["id"]):
                with st.container(width="content", horizontal_alignment="center"):
                    with st.container(horizontal=True):
                        # adds checkbox for multi-select removing
                        if gfuncs.removeCheck:
                            if st.checkbox(" ", key=f"remove_{collInfo[0].replace(' ', '')}", width="content"):
                                removedCollections.append(doc['id'])

                    # display cards for collections
                    with st_yled.image_card_one(
                                                title=f"{collInfo[0]}",
                                                image_path=gfuncs.THUMNAIL_URLS[collInfo[1]],
                                                text=f"**{_('Type')}: {collInfo[1]}**",
                                                background_color=gfuncs.read_config_val("backgroundColor"),
                                                width=275,
                                                height=350,
                                                border_style="solid",
                                                border_color=gfuncs.read_config_val("textColor"),
                                                border_width=1,
                                                card_shadow=True,                                        # adds drop shadow
                                                title_font_size=18,                                      # larger title
                                                title_font_weight="bold",
                                                title_color=gfuncs.read_config_val("textColor"),         # explicit title color
                                                text_font_size=13,                                       # smaller type label
                                                text_font_weight="normal",
                                                text_color=gfuncs.read_config_val("textColor"),          # explicit text color
                                                key=f"{collInfo[0].replace(' ', '')}_card"
                                            ):
                        # animation
                        gfuncs.apply_collection_icon_animation(f"{collInfo[0].replace(' ', '')}_card")

                        # button to go to collection
                        if st_yled.button(_("View Collection"), key=f"{collInfo[0].replace(' ', '')}_link", width="stretch"):
                            backEnd.set_collection(doc['id'])
                            sleep(0.5)
                            st.switch_page(gfuncs.collection_page)
                        st_yled.space("small")

                        # button for editing some collection settings
                        if st_yled.button(_("Edit"), key=f"edit_{collInfo[0].replace(' ', '')}", width="stretch"):
                            edit_collection(doc)

                    st.space("medium")
                st.space("small")

    # Container in bottom right for add button
    with st.container(horizontal_alignment="right"):
        # add collection button
        if st_yled.button(_("Add Collection"), key="add_collection_button"):
            add_collection()
        
        # remove collection button
        if st.button(_("Remove Collections")):
            gfuncs.removeCheck = not gfuncs.removeCheck
            # if any selected, removes selected, else skips
            if not removedCollections == []:
                remove_collections()
            else:
                st.rerun()


