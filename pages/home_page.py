import streamlit as st
from google.cloud import firestore
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd

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
    gfuncs.page_initialization()
    
    # variables
    conf_file = ".streamlit/config.toml"
    collection_page = "pages/collectionView.py"
    user_id = st.session_state.user_info["localId"]
    user_data_dict = db.collection("Users").document(user_id).get().to_dict()
    collections = list(db.collection("Users").document(user_id).collections())
    
    # Updates user configs
    gfuncs.update_config_val(conf_file, "base", user_data_dict["base"])
    gfuncs.update_config_val(conf_file, "backgroundColor", user_data_dict["backgroundColor"])
    gfuncs.update_config_val(conf_file, "textColor", user_data_dict["textColor"])
    if gfuncs.login_color_flag == 0:
        gfuncs.login_color_flag = 1
        st.rerun()

    ## -------------------------------------------------------------------------------------------------
    ## Main Page Setup ---------------------------------------------------------------------------------
    ## -------------------------------------------------------------------------------------------------
    st.space("small")
    st.subheader(f"Your Collections\n Hello {st.session_state.user_info['email']}", text_alignment="center")
    # DEGUB:{st.session_state.user_info}
    st.space("small")

    # Center section for collections
    with st.container(horizontal=True, horizontal_alignment="center"):

        # Edit dialog to change the name of the collection
        @st.dialog("Edit") 
        def edit_collection(coll):
            with st.container(horizontal=True, horizontal_alignment="center"):
                st.subheader(f"Rename {coll.id.split('_')[0]}?", text_alignment="center")
                coll_rename = st.text_input(" ")
                if st.button ("Rename", key=f"rename_{coll.id.split('_')[0]}", width="content"):
                    if backEnd.rename_collection(coll, coll_rename, db):
                        st.error("Collection name already exist")
                    else: 
                        st.rerun()

        # Add collection dialog for adding a new collection to the db
        @st.dialog("Add")
        def add_collection():
            name = st.text_input("Name the Collection")
            collType = st.text_input("Give Collection Type") # will be dropdown
            if st.button("Add", key="makeColl") and name is not None and collType is not None:
                if backEnd.create_collection(name, collType, db):
                    st.error("Collection name already exist")
                else:
                    st.rerun()

        # Remove collection dialog to remove a collection from the db
        @st.dialog("Remove") 
        def remove_collection(coll):
            with st.container(horizontal=True, horizontal_alignment="center"):
                st.subheader(f"Are you sure you want to remove \"{coll.split('_')[0]}\"?", text_alignment="center")
                if st.button("Yes", key=f"confirmRemove", width="content"):
                    ref = db.collection("Users").document(user_id).collection("Collections").document(coll)
                    ref.delete()
                    st.rerun()
                
                if st.button("No", key=f"cancelRemove", width="content"):
                    st.rerun()

        # iterate through collections
        for coll in collections:
            for doc in list(coll.stream()):
                collInfo = doc.id.split('_')
                if not collInfo[0] == "DefaultCollection":
                    with st.container(width="content", horizontal_alignment="center"):
                        st.subheader(f"{collInfo[0]}", text_alignment="center")

                        if st.button("View Collection", key=f"{collInfo[0]}_link"):
                            backEnd.setCollection(doc.id)
                            st.switch_page(collection_page)

                        if st.button("Edit", key=f"edit_{collInfo[0]}"):
                            edit_collection(doc)

                        if st.button("Remove", key=f"remove_{collInfo[0]}", width="content"):
                            remove_collection(doc.id)

                        st.space("medium")
                    st.space("small")

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right"):
        # add collection button
        if st.button("Add Collection"):
            add_collection()
    