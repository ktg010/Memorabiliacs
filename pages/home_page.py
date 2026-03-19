import streamlit as st
from google.cloud import firestore
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled

# Connects to db
try:
    db = firestore.Client.from_service_account_info(st.secrets["firebase"])
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
    user_data_dict = db.collection("Users").document(user_id).get().to_dict()
    collections = db.collection("Users").document(user_id).collection("Collections")
    fullCollections = []
    removedCollections = []
    
    
    gfuncs.page_initialization(user_data_dict)
    # st_yled.init(css_path=backEnd.CURR_THEME)
    st_yled.init()

    # Set language from database
    from BackendMethods.translations import set_language
    user_lang = user_data_dict.get('language', 'en')
    set_language(user_lang)
    
    # Updates user configs
    gfuncs.update_config_val(conf_file, "base", user_data_dict["base"])
    gfuncs.update_config_val(conf_file, "backgroundColor", user_data_dict["backgroundColor"])
    gfuncs.update_config_val(conf_file, "textColor", user_data_dict["textColor"])
    if gfuncs.login_color_flag == 0:
        gfuncs.login_color_flag = 1
        gfuncs.removeCheck = False
        st.rerun()
    

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
            itemSettings, rename = st.columns([3,1])
            with itemSettings:
                hidden = st.checkbox("Hide Collection")
                fields = doc.to_dict()["settings"]
                # TODO
                # Add things for other setting when we figure out 
                # how to do it
                doc.reference.update({"settings.hidden" : hidden})
            with rename:
                st_yled.subheader(f"Rename {coll.id.split('_')[0]}?", text_alignment="center")
                coll_rename = st.text_input(" ")
            with st.container(horizontal=True, horizontal_alignment="right"):
                if st_yled.button("Save"):
                    if coll_rename != "":
                        if backEnd.rename_collection(coll, coll_rename, db):
                            st_yled.error("Collection name already exist")
                    else:
                        st.rerun()

        # Add collection dialog for adding a new collection to the db
        @st.dialog(_("Add"))
        def add_collection():
            name = st_yled.text_input(_("Name the Collection"))
            collType = st.selectbox("Type", backEnd.get_collection_types(db))
            if st_yled.button("Add", key="makeColl") and name is not None and collType is not None:
                if gfuncs.collection_input_sanitation(name):
                    if backEnd.create_collection(name, collType, db):
                        st_yled.error("Collection name already exist")
                    else:
                        st.rerun()
                else: 
                    st_yled.error("Invalid Character in name: \n '_', '-', '\\', '/'")

        # Remove collection dialog to remove a collection from the db
        @st.dialog(_("Remove")) 
        def remove_collections():
            
            st_yled.subheader(_("Are you sure you want to remove the following collections:"), text_alignment="center")
            for coll in removedCollections:
                st.write(coll.split("_")[0])
            with st.container(horizontal=True, horizontal_alignment="center"):
                if st_yled.button("Yes", key=f"confirmRemove", width="content"):
                    for coll in removedCollections:
                        ref = db.collection("Users").document(user_id).collection("Collections").document(coll)
                        ref.delete()
                    removedCollections.clear()
                    st.rerun()
                
                if st_yled.button("No", key=f"cancelRemove", width="content"):
                    gfuncs.removeCheck = False
                    st.rerun()

        # iterate through collections
        for doc in collections.stream():
            collInfo = doc.id.split('_')
            if collInfo[0] != "DefaultCollection" : fullCollections.append(doc.id)
            if backEnd.coll_visability(doc.id, db):
                with st.container(width="content", horizontal_alignment="center"):
                    with st.container(horizontal=True):
                        st_yled.subheader(f"{collInfo[0]}", text_alignment="center")
                        if gfuncs.removeCheck:
                            if st.checkbox(" ", key=f"remove_{collInfo[0]}", width="content"):
                                removedCollections.append(doc.id)

                    if st_yled.button("View Collection", key=f"{collInfo[0]}_link"):
                        backEnd.set_collection(doc.id)
                        st.switch_page(collection_page)

                    if st_yled.button("Edit", key=f"edit_{collInfo[0]}"):
                        edit_collection(doc)


                    st.space("medium")
                st.space("small")

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right"):
        # add collection button
        if st_yled.button(_("Add Collection"), key="add_collection_button"):
            add_collection()
    
        if st.button("Remove"):
            gfuncs.removeCheck = not gfuncs.removeCheck
            if not removedCollections == []:
                remove_collections()
            else:
                st.rerun()

    with st.sidebar:
        st.space("small")
        st.title("All Collections:")
        for coll in fullCollections:
            if st.button(f"{coll.split("_")[0]}", type="tertiary"):
                backEnd.set_collection(coll)
                st.switch_page(collection_page)
