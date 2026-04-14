import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
from time import sleep
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
    views = backEnd.collection_views(backEnd.CURR_COLL, db)
    ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
    view_mode = ref.get().to_dict()['settings']['collection view']

    if st.button("Back"):
        backEnd.set_sub_collection("")
        st.switch_page(gfuncs.collection_page)

    items = backEnd.get_sub_collection_items(backEnd.CURR_COLL, backEnd.SUB_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]

    if "itemsToAdd"  in st.session_state:
        del st.session_state["itemsToAdd"]

    @st.dialog("Collection Views")
    def viewCollSettings():
        with st.container(horizontal_alignment="center"):
            for view in views.keys():
                if view != "Name" or view != "Image":
                    st.checkbox(f"Hide {view}", key=view, value=(not views[view]))

            if st.button("Save"):
                newViews = {}
                for view in views.keys():
                    newViews[view] = not st.session_state[view]
                backEnd.update_collection_views(backEnd.CURR_COLL, newViews, db)
                st.rerun()
    
    @st.fragment
    @st.dialog("Add to Sub Collection")
    def addToSub():
        totalSize = backEnd.get_sub_coll_size(backEnd.SUB_COLL, backEnd.CURR_COLL)
        firstPass = False
        if "itemsToAdd" not in st.session_state:
            st.session_state["itemsToAdd"] = {}   
            firstPass = True
        itemsToAdd = st.session_state["itemsToAdd"]

        if firstPass:
            for item in items:
                itemsToAdd[item] = int(items[item]["quantity"])
            firstPass = False

        with st.container(horizontal_alignment="center"):
            fullItems = backEnd.get_collection_items(backEnd.CURR_COLL)
            cols = st.columns(3, width="stretch") 
            totalQaunt = 0
            for item in itemsToAdd.keys(): 
                totalQaunt += itemsToAdd[item]
            for i, key in enumerate(fullItems.keys()):
                col = cols[i % 3]
                curr_item = fullItems[key]
                with col.container(horizontal_alignment="center"):
                    st_yled.subheader(f"{curr_item['info'].get('Name')}", text_alignment="center")
                    if key not in itemsToAdd:
                        itemsToAdd[key] = 0

                    if backEnd.CURR_COLL.split("_")[1] == "Custom":
                        if curr_item["info"]["image"] is not None:
                            st.image(curr_item["info"]["image"], width=200)
                        else:
                            st.image(gfuncs.THUMNAIL_URLS["Custom"], width=200)
                    else:
                        st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)

                    itemQuant = int(curr_item.get("quantity"))
                    st.write(f"{itemsToAdd[key]}/{itemQuant}")
                    
                    if st.button("", icon=":material/add:", key=f"{key}_add"):
                        if totalQaunt == totalSize:
                            st.warning("Sub Collection full")
                        elif itemsToAdd[key] == itemQuant:
                            st.warning("Not enough of that item")
                        else:
                            itemsToAdd[key] += 1
                            st.rerun(scope="fragment")
                    
            totalQaunt = 0
            for item in itemsToAdd.keys(): 
                totalQaunt += itemsToAdd[item]
            st.write(f"{totalQaunt}/{totalSize}")

            if st.button("Save"):
                for item in itemsToAdd.keys(): 
                    if itemsToAdd[item] != 0:
                        backEnd.add_item_sub_coll(item, fullItems[item].get("Notes"), itemsToAdd[item], backEnd.SUB_COLL, backEnd.CURR_COLL)
                del st.session_state["itemsToAdd"]
                st.rerun()
    
    @st.dialog("Item Info")
    def viewItem(item):
        field_text = ""
        with st_yled.badge_card_one(title=items[item]['info']["Name"], text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
            for key in items[item]['info'].keys():
                if key not in ("Name", "Image"):
                    if views[key]:
                        st.write(f"**{key}**: **{items[item]['info'][key]}**")
            if st.button(_("Remove From Collection")):
                backEnd.del_item_sub_coll(item, 1, backEnd.SUB_COLL, backEnd.CURR_COLL)
                st.rerun()


    st.subheader(backEnd.SUB_COLL, text_alignment="center")

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

                if views["Quantity"]:
                    st.subheader(f"x{curr_item.get("quantity")}", text_alignment="right")

                if views["Notes"]:
                    notes = curr_item.get("notes")
                    if notes != "Enter notes here":
                        st.subheader(notes)

                if st_yled.button("View More", key=f"{curr_item["info"]["Name"]}_view"):
                    viewItem(key)
                st.space("medium")


    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        if st.button("Add Items to Sub Collection"):
            addToSub()

