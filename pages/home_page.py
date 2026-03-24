import streamlit as st
from google.cloud import firestore
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
from BackendMethods.translations import set_language
import st_yled

# Connects to db
try:
    db = backEnd.get_firestore_client()
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()

# user sign-in check
if 'user_info' not in st.session_state:
    st.switch_page("pages/login.py")
## -------------------------------------------------------------------------------------------------
## Logged in ---------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    # variables
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    collections_docs = backEnd.get_user_collections(user_id)
    backEnd.set_collection("")
    fullCollections = []
    removedCollections = []
    
    gfuncs.db_settings_to_config(user_data_dict)
    gfuncs.page_initialization(user_data_dict)
    # st_yled.init(css_path=backEnd.CURR_THEME)
    st_yled.init()

    image = 'https://pbs.twimg.com/media/F9pQLNmXYAAKAn4.jpg'

    css = f'''
    <style>
        .stApp {{
            background-image: linear-gradient(to top, {gfuncs.read_config_val(gfuncs.conf_file, "textColor")}, transparent),
            url({image});
            background-size: cover;

        }}
        .stApp > header {{
            background-color: transparent;
        }}
    </style>
    '''
    st.markdown(css, unsafe_allow_html=True)
    # Set language from database
    user_lang = user_data_dict.get('language', 'en')
    set_language(user_lang)    

    ## -------------------------------------------------------------------------------------------------
    ## Main Page Setup ---------------------------------------------------------------------------------
    ## -------------------------------------------------------------------------------------------------
    st.space("small")
    #st_yled.init(css_path=backEnd.CURR_THEME)
    st_yled.init()
    st_yled.subheader(f"{_('Your Collections')}\n {_('Hello')}, {st.session_state.user_info['email']}", text_alignment="center")
    # DEGUB:{st.session_state.user_info}
    st.space("small")

    # Center section for collections
    with st.container(horizontal=True, horizontal_alignment="center"):

        # Edit dialog to change the name of the collection
        @st.dialog(_("Edit")) 
        def edit_collection(coll):
            itemSettings, rename = st.columns([3,2])
            with itemSettings:
                hidden = st.checkbox(_("Hide Collection"))
                fields = coll["settings"]
                # TODO
                # Add things for other setting when we figure out 
                # how to do it
                ref = db.collection("Users").document(user_id).collection("Collections").document(coll["id"])
                ref.update({"settings.hidden" : hidden})
            with rename:
                st_yled.subheader(f"{_('Rename')} {coll["id"].split('_')[0]}?", text_alignment="center")
                coll_rename = st.text_input(" ")
            with st.container(horizontal=True, horizontal_alignment="right"):
                if st_yled.button(_("Save")):
                    if coll_rename != "":
                        if backEnd.rename_collection(coll, coll_rename, db):
                            st_yled.error(_("Collection name already exists"))
                        else:
                            backEnd.get_user_collections.clear(user_id)
                            st.rerun()
                    else:
                        st.rerun()

        # Add collection dialog for adding a new collection to the db
        @st.dialog(_("Add"))
        def add_collection():
            name = st.text_input(_("Name the Collection"))
            collType = st.selectbox(_("Type"), backEnd.get_collection_types())
            if st_yled.button(_("Add"), key="makeColl") and name is not None and collType is not None:
                if gfuncs.collection_input_sanitation(name):
                    if backEnd.create_collection(name, collType, db):
                        st_yled.error(_("Collection name already exists"))
                    else:
                        backEnd.get_user_collections.clear(user_id)
                        st.rerun()
                else: 
                    st_yled.error(_("Invalid character in name: '_', '-', '\\', '/'"))

        # Remove collection dialog to remove a collection from the db
        @st.dialog(_("Remove")) 
        def remove_collections():
            
            st_yled.subheader(f"{_('Are you sure you want to remove')} {_('the following collections:')}", text_alignment="center")
            for coll in removedCollections:
                st.write(coll.split("_")[0])
            with st.container(horizontal=True, horizontal_alignment="center"):
                if st_yled.button(_("Yes"), key="confirmRemove", width="content"):
                    for coll in removedCollections:
                        ref = db.collection("Users").document(user_id).collection("Collections").document(coll)
                        ref.delete()
                    removedCollections.clear()
                    backEnd.get_user_collections.clear(user_id)
                    st.rerun()
                
                if st_yled.button(_("No"), key="cancelRemove", width="content"):
                    gfuncs.removeCheck = False
                    st.rerun()

        # iterate through collections
        for doc in collections_docs:
            collInfo = doc['id'].split('_')
            if collInfo[0] != "DefaultCollection" : fullCollections.append(doc['id'])
            if backEnd.coll_visability(doc['id'], db):
                with st.container(width="content", horizontal_alignment="center"):
                    with st.container(horizontal=True):
                        #st.subheader(f"{collInfo[0]}", text_alignment="center")
                        if gfuncs.removeCheck:
                            if st.checkbox(" ", key=f"remove_{collInfo[0]}", width="content"):
                                removedCollections.append(doc['id'])
                    with st_yled.image_card_one(title=f"{collInfo[0]}", image_path=gfuncs.THUMNAIL_URLS[collInfo[1]], text=f"**Type: {collInfo[1]}**", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), width=250, height=350, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                        if st_yled.button(_("View Collection"), key=f"{collInfo[0]}_link", width="stretch", border_width=5):
                            backEnd.set_collection(doc['id'])
                            st.switch_page(gfuncs.collection_page)
                        st_yled.space("small")
                        if st_yled.button(_("Edit"), key=f"edit_{collInfo[0]}", width="stretch", border_width=5):
                            edit_collection(doc)

                    st.space("medium")
                st.space("small")

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right"):
        # add collection button
        if st_yled.button(_("Add Collection"), key="add_collection_button"):
            add_collection()
    
        if st.button(_("Remove")):
            gfuncs.removeCheck = not gfuncs.removeCheck
            if not removedCollections == []:
                remove_collections()
            else:
                st.rerun()

    with st.sidebar:
        st.space("small")
        st.title(_("All Collections:"))
        for coll in fullCollections:
            if st.button(f"{coll.split("_")[0]}", type="tertiary"):
                backEnd.set_collection(coll)
                st.switch_page(gfuncs.collection_page)
