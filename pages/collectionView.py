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

    user_id = st.session_state.user_info["localId"]
    collectionData = backEnd.generate_collection(backEnd.CURR_COLL, db)
    st.space("small")
    st.subheader(backEnd.CURR_COLL.split("_")[0], text_alignment="center")
    st.space("small")

    # view selection radio buttons
    view_mode = st.radio("Display mode", ["grid", "column"], horizontal=True)

    
        # iterate through collections and collect item info
    items = []
    for id, ref in collectionData.items():
        if id == "Info":
            continue
        doc = ref.get()
        if doc.exists:
            info = doc.to_dict()
            items.append(info)

    # display either grid or column view
    if view_mode == "grid":
        with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
            cols = st.columns(3, width="stretch")  # grid view
            for idx, info in enumerate(items):
                col = cols[idx % 3]
                with col.container(horizontal_alignment="center"):
                    st.subheader(f"{info.get('name','')}", text_alignment="center")
                    st.image(info.get('image',''), width="content")
                    for key, val in info.items():
                        if key not in ("name", "image"):
                            st.write(f"{key}: {val}")
                    st.space("medium")
    else:
        with st.container(horizontal=False, horizontal_alignment="center", width="stretch"):
            cols = st.columns([0.2,0.8,0.2], width="stretch")  # column view (default)
            for info in items:
                with cols[1].container(width="stretch", horizontal_alignment="center"):
                    st.subheader(f"{info.get('name','')}", text_alignment="center")
                    st.image(info.get('image',''), width=300)
                    for key, val in info.items():
                        if key not in ("name", "image"):
                            st.markdown(f"<p style='text-align: center;'>{key}: {val}</p>", unsafe_allow_html=True)
                    st.space("medium")
                st.space("small")



    # Container in bottom right for add button
    
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        # Text box for input
        item_id = st.text_input("Enter Item ID")
        new_string = ""
        for i in range(len(item_id)):
            if item_id[i] == "-":
                 new_string+="_"
            else:
                new_string+=item_id[i]
        # Add to collection button. Must input Id for now
        if st.button("Add To Collection"):
            backEnd.add_reference_collectionView(db, user_id, new_string, item_id)
        if st.button("Remove From Collection"):
            backEnd.delete_reference(db, user_id, new_string)