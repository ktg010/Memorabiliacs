import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled
import os
import time
import numpy as np


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
    #st_yled.init(CURR_THEME)
    st_yled.init()
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    gfuncs.page_initialization(user_data_dict)
    views = backEnd.collection_views(backEnd.CURR_COLL, db)
    ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
    view_mode = ref.get().to_dict()['settings']['collection view']
    items = backEnd.get_collection_items(backEnd.CURR_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]
    settings_page_flag = False
    viewing_flag = False

    background = ref.get().to_dict().get("settings").get("background")
    if background != "":
        gfuncs.apply_background_image(background)
        

    @st.dialog(_("Edit")) 
    def edit_collection(sub):
        global ref
        subRef = ref.collection("Sub Collections").document(sub)
        itemSettings, rename = st.columns([3,2])
        with itemSettings:
            new_image_URL = st.text_input(("URL of image to be used for background: "), value=subRef.get().to_dict().get("settings").get("background"))
            currSize = backEnd.get_sub_coll_size(sub, backEnd.CURR_COLL)
            newSize = st.text_input("Change size of collection?", value=currSize)
            if newSize.isdigit():
                if int(newSize) < currSize:
                    st.warning("Cannot change size to be smaller than current size")
                elif int(newSize) > currSize:
                    subRef.update({"settings.size": int(newSize)})
            else:
                st.warning("Size must be a whole number")
            if st.button("Remove Sub Collection"):
                backEnd.delete_sub_collection(sub, backEnd.CURR_COLL)
                st.rerun()
        with rename:
            st_yled.subheader(f"{_('Rename')} {sub}?", text_alignment="center")
            sub_rename = st.text_input(" ")
        with st.container(horizontal=True, horizontal_alignment="right"):
            if st.button(_("Save")):
                if new_image_URL != "" and "https:" in new_image_URL: 
                    subRef.update({"settings.background" : new_image_URL})
                if sub_rename != "":
                    if backEnd.rename_sub_collection(backEnd.CURR_COLL, sub, sub_rename, db):
                        st_yled.error(_("Sub Collection name already exists"))
                    else:
                        backEnd.get_sub_collections.clear(backEnd.CURR_COLL)
                        st.rerun()
                else:
                    st.rerun()
    
    @st.fragment
    @st.dialog("Collection Setting")
    def viewCollSettings():
        global settings_page_flag
        if settings_page_flag:
            st.header("Settings", text_alignment="center")
            st.subheader("New page", text_alignment="center")
            global ref
            view_mode = st.radio(_("Display mode"), [_("grid"), _("column")], horizontal=True)
            hidden = st.checkbox(_("Hide Collection"), value=ref.get().to_dict()['settings']['hidden'])
            if st.button("Save"):
                ref.update({"settings.hidden" : hidden})
                ref.set({"settings" : {"collection view" : view_mode}}, merge=True)
                st.rerun()
        else: 
            st.header("Collection Views", text_alignment="center")
            with st.container(horizontal_alignment="center"):
                st.subheader("Main Page View", text_alignment="center")
                for name in ["Name", "Image", "Quantity" , "Notes"]:
                    st.checkbox(f"Hide {name}", key=name, value=(not views[name]))
                st.divider()

                st.subheader("Additional Data", text_alignment="center")
                for view in views.keys():
                    if view not in ["Name", "Image", "Quantity" , "Notes"]:
                        st.checkbox(f"Hide {view}", key=view, value=(not views[view]))

            with st.container(horizontal_alignment="right"):
                if st.button("Save"):
                    newViews = {}
                    for view in views.keys():
                        newViews[view] = not st.session_state[view]
                    backEnd.update_collection_views(backEnd.CURR_COLL, newViews, db)
                    st.rerun()

        # Arrows
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button("", icon=":material/arrow_back_ios:"):
                settings_page_flag = False
                st.rerun(scope="fragment")
            if st.button("", icon=":material/arrow_forward_ios:"):
                settings_page_flag = True
                st.rerun(scope="fragment")
    
    @st.fragment
    @st.dialog("Item Info")
    def viewItem(item):
        global viewing_flag
        if viewing_flag:
            ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
            note = st.text_input("Item Note", value=ref.get().to_dict()["items"][item].get('notes'), key="notes")
            if st.button("Save"):
                backEnd.update_notes(item, note, db)
                viewing_flag = False
                st.rerun()
        else:
            field_text = ""
            with st_yled.badge_card_one(title=items[item]['info']["Name"], text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                for key in items[item]['info'].keys():
                    if key not in ("Name", "Image", "Rarity", "id"):
                        if views[key]:
                            st.write(f"**{key}**: **{items[item]['info'][key]}**")
                if st.button("Edit Note"):
                    viewing_flag = True
                    st.rerun(scope="fragment")
                if st.button(_("Remove From Collection")):
                    st.audio(gfuncs.DEFAULT_SOUNDS["Delete"], autoplay=True, width=1, start_time=0)
                    time.sleep(1)
                    backEnd.delete_reference(item, db)
                    st.rerun()

    @st.dialog("Create Sub Collection")
    def subColl():
        name = st.text_input("Name your sub collection")
        size = st.text_input("What is the size of the collection")
        if st.button("Save"):
            if size.isdigit():
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, size, db)
                st.rerun()
            elif size == "":
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, 999, db)
                st.rerun()
            else:
                st.error("Size needs to be a whole number")

    st.subheader(backEnd.CURR_COLL.split("_")[0], text_alignment="center")
    with st.container(horizontal_alignment="right"):
        if st.button("Collection Settings", icon=":material/settings:", type="tertiary"):
            settings_page_flag = False
            viewCollSettings()


    # Sub collections
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        for subCollection in backEnd.get_sub_collections(backEnd.CURR_COLL):
            with st.container(width="content", horizontal_alignment="center"):
                with st_yled.image_card_one(title=f"{subCollection}", image_path=gfuncs.THUMNAIL_URLS[coll_type], text=f"**{_('Type')}: {coll_type}**", background_color=gfuncs.read_config_val( "backgroundColor"), width=250, height=350, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                    if st_yled.button(_("View Collection"), border_width=5, key=f"{subCollection}_link", width="stretch"):
                        backEnd.set_sub_collection(subCollection)
                        st.switch_page(gfuncs.sub_coll_page)
                    if st_yled.button(_("Edit"), border_width=5, key=f"edit_{subCollection}", width="stretch"):
                            edit_collection(subCollection)

    # all items
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        cols = st.columns(3, width="stretch") 
        for i, key in enumerate(items.keys()):
            # display either grid or column view
            if view_mode == _("grid"):
                col = cols[i % 3]
            else: 
                col = cols[1]
            curr_item = items[key]
            with col.container(horizontal_alignment="center"):
                if views["Name"]:
                    st_yled.subheader(f"{curr_item['info'].get('Name')}", text_alignment="center")

                if views["Image"]:
                    if backEnd.CURR_COLL.split("_")[1] == "Custom":
                        if curr_item["info"]["image"] is not None:
                            st.image(curr_item["info"]["image"], width=200)
                        else:
                            st.image(gfuncs.THUMNAIL_URLS["Custom"], width=200)
                    else:
                        st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)
                itemCols = st.columns(2, width="stretch")
                with itemCols[1].container(horizontal_alignment="right"):
                    if views["Quantity"]:
                        st.subheader(f"x{curr_item.get("quantity")}", text_alignment="right")
                with itemCols[0].container(horizontal_alignment="left"):
                    if views["Notes"]:
                        notes = curr_item.get("Notes")
                        if notes != "Enter notes here":
                            st.subheader(notes)
                    
                if st_yled.button("View More", key=f"{curr_item['info']['Name']}_{key}_view"):
                    viewItem(key)
    
    st.space("large")
    st.divider()
    st.subheader("Wishlisted Items", text_alignment="center")
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        st.space("small")
        wishCols = st.columns(3, width="stretch") 
        wishlist = backEnd.get_collection_wishlisted(backEnd.CURR_COLL)
        for i, key in enumerate(wishlist.keys()):
            if view_mode == _("grid"):
                col = wishCols[i % 3]
            else: 
                col = wishCols[1]
            with col.container(horizontal_alignment="center"):
                st.header(wishlist[key].get("Name"),text_alignment="center")
                st.image(gfuncs.image_grayscale(wishlist[key].get("Image")))  
                st.write(f'<a style="text-align: center"> {key.replace("_", "-")} </a>', unsafe_allow_html=True)
    

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        collection = {
            "name" : backEnd.CURR_COLL.split("_")[0],
            "type" : backEnd.CURR_COLL.split("_")[1]
        }
        st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)

        if st.button("Create subColl"):
            subColl()
            
