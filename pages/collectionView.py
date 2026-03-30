import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
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
    #st_yled.init(CURR_THEME)
    st_yled.init()
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    gfuncs.page_initialization(user_data_dict)


    # cloud_image_url = backEnd.get_cloud_storage_image("pikachu.jpeg")  # Example usage of cached image retrieval

    # st.image(cloud_image_url, width=200)  # Display the image from Cloud Storage


    items = backEnd.get_collection_items(backEnd.CURR_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]
    
    @st.dialog("Collection Views")
    def viewCollSettings():
        with st.container(horizontal_alignment="center"):
            views = backEnd.collection_views(backEnd.CURR_COLL, db)
            for view in views.keys():
                if view != "name" or view != "image":
                    st.checkbox(f"Hide {view}", key=view, value=(not views[view]))

            if st.button("Save"):
                newViews = {}
                for view in views.keys():
                    newViews[view] = not st.session_state[view]
                backEnd.update_collection_views(backEnd.CURR_COLL, newViews, db)
                st.rerun()
    
    @st.dialog("Item Info")
    def viewItem(item):
        views = backEnd.collection_views(backEnd.CURR_COLL, db)
        field_text = ""
        with st_yled.badge_card_one(title=items[item]['info']["name"], text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
            for key in items[item]['info'].keys():
                if key not in ("name", "image", "rarity", "id"):
                    if views[key]:
                        st.write(f"**{key}**: **{items[item]['info'][key]}**")
            if st_yled.button(_("Remove From Collection")):
                backEnd.delete_reference(item, db)

    st.space("small")
    st.subheader(backEnd.CURR_COLL.split("_")[0], text_alignment="center")
    if st.button("", icon=":material/settings:", type="tertiary"):
        viewCollSettings()
    st.space("small")

    # view selection radio buttons
    view_mode = st.radio(_("Display mode"), [_("grid"), _("column")], horizontal=True)

    # display either grid or column view
    if view_mode == _("grid"):
            with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
                cols = st.columns(3, width="stretch")  # grid view
                for i, key in enumerate(items.keys()):
                    col = cols[i % 3]
                    curr_item = items[key]
                    with col.container(horizontal_alignment="center"):
                        st_yled.subheader(f"{curr_item['info'].get('name')}", text_alignment="center")

                        if backEnd.CURR_COLL.split("_")[1] == "Pokemon":
                            st.image(gfuncs.get_image_from_URL(curr_item["info"]["images"]['small']), width=200)
                        else:
                            st.image(gfuncs.get_image_from_URL(curr_item["info"]["image"]), width=200)

                        info = st.text_input("Notes", value = curr_item.get('notes'), key = f"notes_{key}", width=250)
                        
                        if info != items[key].get('notes'):
                            backEnd.update_notes(key, info, db)
                            st.success("Updated!")

                        if st_yled.button("View More", key=f"{curr_item["info"]["name"]}_view"):
                            viewItem(key)
                        st.space("medium")
    else:
        with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
            cols = st.columns(3, width="stretch")  # grid view
            for key in items.keys():
                curr_item = items[key]
                with cols[1].container(horizontal_alignment="center"):
                    st_yled.subheader(f"{curr_item['info'].get('name')}", text_alignment="center")

                    if backEnd.CURR_COLL.split("_")[1] == "Pokemon":
                        st.image(gfuncs.get_image_from_URL(curr_item['info']['images']['small']), width=200)
                    else:
                        st.image(gfuncs.get_image_from_URL(curr_item["info"]["image"]), width=200)
    
                    info = st.text_input("Notes", value = curr_item.get('notes'), key = f"notes_{key}", width=250)
                    
                    if info != items[key].get('notes'):
                        backEnd.update_notes(key, info, db)
                        st.success("Updated!")
                        
                    if st_yled.button("View More", key=f"{curr_item['info'].get('name')}_view"):
                        viewItem(key)
                    st.space("medium")


    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        # Text box for input
        # item_id = st_yled.text_input(_("Enter Item ID"))
        # new_string = ""
        # for i in range(len(item_id)):
        #     if item_id[i] == "-":
        #          new_string+="_"
        #     else:
        #         new_string+=item_id[i]
        # Add to collection button. Must input Id for now
        # if st_yled.button(_("Add To Collection"), key="add_to_collection"):
        #     backEnd.add_reference_collectionView(new_string, item_id, db)
        collection = {
            "name" : backEnd.CURR_COLL.split("_")[0],
            "type" : backEnd.CURR_COLL.split("_")[1]
        }

        # TODO
        #  Translate string 
        st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)
            
