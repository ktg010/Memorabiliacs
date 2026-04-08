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

    if st.button("Back"):
        backEnd.set_sub_collection("")
        st.switch_page(gfuncs.collection_page)

    items = backEnd.get_sub_collection_items(backEnd.CURR_COLL, backEnd.SUB_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]

    

    @st.dialog("Collection Views")
    def viewCollSettings():
        with st.container(horizontal_alignment="center"):
            views = backEnd.collection_views(backEnd.CURR_COLL, db)
            for view in views.keys():
                if view != "Name" or view != "Image":
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
        with st_yled.badge_card_one(title=items[item]['info']["Name"], text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
            for key in items[item]['info'].keys():
                if key not in ("Name", "Image"):
                    if views[key]:
                        st.write(f"**{key}**: **{items[item]['info'][key]}**")
            if st_yled.button(_("Remove From Collection")):
                backEnd.delete_reference(item, db)

    @st.dialog("Create Sub Collection")
    def subColl():
        name = st.text_input("Name your sub collection")
        if st.button("Save"):
            backEnd.create_sub_collection(name, backEnd.CURR_COLL, db)
            st.rerun()

    st.space("small")
    st.subheader(backEnd.SUB_COLL, text_alignment="center")
    # if st.button("", icon=":material/settings:", type="tertiary"):
    #     viewCollSettings()

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
                    st_yled.subheader(f"{curr_item['info'].get('Name')}", text_alignment="center")

                    if backEnd.CURR_COLL.split("_")[1] == "Custom":
                        if curr_item["info"]["image"] is not None:
                            st.image(curr_item["info"]["image"], width=200)
                        else:
                            st.image(gfuncs.THUMNAIL_URLS["Custom"], width=200)
                    else:
                        st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)
                        
                    info = st.text_input("Notes", value = curr_item.get('notes'), key = f"notes_{key}", width=250)
                    
                    if info != items[key].get('notes'):
                        backEnd.update_notes(key, info, db)
                        st.success("Updated!")

                    if st_yled.button("View More", key=f"{curr_item["info"]["Name"]}_view"):
                        viewItem(key)
                    st.space("medium")
    else:
        with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
            cols = st.columns(3, width="stretch")  # grid view
            for key in items.keys():
                curr_item = items[key]
                with cols[1].container(horizontal_alignment="center"):
                    st_yled.subheader(f"{curr_item['info'].get('Name')}", text_alignment="center")

                    if backEnd.CURR_COLL.split("_")[1] == "Custom":
                        if curr_item["info"]["image"] is not None:
                            st.image(curr_item["info"]["image"], width=200)
                        else:
                            st.image(gfuncs.THUMNAIL_URLS["Custom"], width=200)
                    else:
                        st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)
    
                    info = st.text_input("Notes", value = curr_item.get('notes'), key = f"notes_{key}", width=250)
                    
                    if info != items[key].get('notes'):
                        backEnd.update_notes(key, info, db)
                        st.success("Updated!")
                        
                    if st_yled.button("View More", key=f"{curr_item['info'].get('Name')}_view"):
                        viewItem(key)
                    st.space("medium")


    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        pass

