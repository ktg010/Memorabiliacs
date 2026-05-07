import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
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
    # backend collection check
    if backEnd.CURR_COLL == "":
        st.switch_page(gfuncs.home_page)

    # local variables
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    views = backEnd.collection_views(backEnd.CURR_COLL)
    ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
    subRef = ref.collection("Sub Collections").document(backEnd.SUB_COLL)
    view_mode = ref.get().to_dict()['settings']['collection view']
    items = backEnd.get_sub_collection_items(backEnd.CURR_COLL, backEnd.SUB_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]

    # page initialization
    st_yled.init()
    gfuncs.page_initialization(user_data_dict)
    gfuncs.apply_collectionpage_css()

    # return to main collection
    if st.button(_("Back")):
        backEnd.set_sub_collection("")
        st.switch_page(gfuncs.collection_page)

    # session state for adding items
    if "itemsToAdd"  in st.session_state:
        del st.session_state["itemsToAdd"]


    ### dialog popups ###
    # item adding 
    @st.fragment
    @st.dialog("Add to Sub Collection")
    def addToSub():
        # setup
        totalSize = backEnd.get_sub_coll_size(backEnd.SUB_COLL, backEnd.CURR_COLL)
        firstPass = False
        if "itemsToAdd" not in st.session_state:
            st.session_state["itemsToAdd"] = {}   
            firstPass = True
        itemsToAdd = st.session_state["itemsToAdd"]
        
        # if opening initially, creates list for items
        if firstPass:
            for item in items:
                itemsToAdd[item] = int(items[item]["quantity"])
            firstPass = False

        with st.container(horizontal_alignment="center"):
            fullItems = backEnd.get_collection_items(backEnd.CURR_COLL)
            cols = st.columns(3, width="stretch") 
            totalQaunt = 0

            # gets total amount of items currently in sub coll
            for item in itemsToAdd.keys(): 
                totalQaunt += itemsToAdd[item]

            # displays items
            for i, key in enumerate(fullItems.keys()):
                col = cols[i % 3]
                curr_item = fullItems[key]

                with col.container(horizontal_alignment="center"):
                    st.write(f"{curr_item['info'].get('Name')}")

                    if key not in itemsToAdd:
                        itemsToAdd[key] = 0

                    # image
                    st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)

                    # amount in sub coll compared to total amount
                    itemQuant = int(curr_item.get("quantity"))
                    st.write(f"{itemsToAdd[key]}/{itemQuant}")
                    
                    # plus button for adding items 
                    if st.button("", icon=":material/add:", key=f"{key}_add"):
                        if totalQaunt == totalSize:
                            st.warning("Sub Collection full")
                        elif itemsToAdd[key] == itemQuant:
                            st.warning("Not enough of that item")
                        else:
                            itemsToAdd[key] += 1
                            st.rerun(scope="fragment")
            
            # checks total size of added compared to size contraint
            totalQaunt = 0
            for item in itemsToAdd.keys(): 
                totalQaunt += itemsToAdd[item]
            st.write(f"{totalQaunt}/{totalSize}")

            # adds items
            if st.button("Save"):
                for item in itemsToAdd.keys(): 
                    if itemsToAdd[item] != 0:
                        backEnd.add_item_sub_coll(item, fullItems[item].get("notes"), itemsToAdd[item], backEnd.SUB_COLL, backEnd.CURR_COLL)
                del st.session_state["itemsToAdd"]
                st.rerun()
    
    # displays item's information
    @st.dialog("Item Info")
    def viewItem(item, index):
        field_text = ""

        # per item info
        with st_yled.badge_card_one(title=items[item]['info']["Name"], 
                                    text=field_text, badge_text="Attributes", 
                                    width="stretch", badge_color="primary", 
                                    background_color=gfuncs.read_config_val("backgroundColor"), 
                                    card_shadow=True, border_style="solid", 
                                    border_color=gfuncs.read_config_val("textColor"), 
                                    border_width=1):
            # image display
            try:
                image = gfuncs.get_image_from_URL(items[item]["info"]["Image"])
            except Exception:
                image = items[item]["info"]["Image"]
            st.image(image, width="stretch")

            # data display
            dataframe_dict = {}
            for key in items[item]['info'].keys():
                if key not in ("Name", "Image", 'id'):
                    if views[key]:
                        # splits lists and dicts to be more readable  
                        if isinstance(items[item]['info'][key], list):
                            dataframe_dict[key] = "".join(str(items[item]['info'][key])).replace("[", "").replace("]", "").replace("{", "").replace("}", "\n").replace(",", "\n")
                        elif isinstance(items[item]['info'][key], dict):
                            dataframe_dict[key] = "".join(str(items[item]['info'][key])).replace("{", "").replace("}", "\n").replace(",", "\n")
                        else:
                            dataframe_dict[key] = items[item]['info'][key]
            st.dataframe(dataframe_dict, height=500, width="stretch", row_height=(500//len(dataframe_dict)) if len(dataframe_dict) > 0 else 500)
            st.divider()

            # per user info
            st.header(_("Personal Fields"))

            notes = items[item].get("notes")
            if notes != "Enter notes here":
                st.write(f"Notes: {notes}")
            else:
                st.write(_("Notes: "))

            st.write(f"Number in Sub Collection: {items[item].get("quantity")}")
            st.divider()

            # removes item
            if st.button(_("Remove From Sub Collection")):
                sleep(1)
                backEnd.del_item_sub_coll(item, 1, backEnd.SUB_COLL, backEnd.CURR_COLL)
                st.rerun()


    ### Main Page Display ###
    # title
    st_yled.text(f"{backEnd.SUB_COLL}", text_alignment="center", font_size="1.75rem")

    # item displays
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        cols = st.columns(3, width="stretch") 
        for i, key in enumerate(items.keys()):
            curr_item = items[key]

            # display either grid or column view
            if view_mode == _("grid"):
                col = cols[i % 3]
            else: 
                col = cols[1]
                
            # item information
            with col.container(horizontal_alignment="center"):
                name = curr_item['info'].get('Name')

                # image
                image = gfuncs.get_image_from_URL(curr_item["info"]["Image"])

                moreText = ""
                if views["Notes"]:
                    notes = curr_item.get("notes")
                    if notes == "Enter notes here" or notes == "Your notes here":
                        notes = ""
                    moreText = f"**Notes:** {notes}"

                if views["Quantity"]:
                    quantity = f"x{curr_item.get("quantity")}"
                    if moreText == "":
                        moreText = f"**Quantity:** {quantity}"
                    else: 
                        moreText += f" | **Quantity:** {quantity}"

                # display
                with st_yled.image_card_one(
                                            image_path=image,
                                            title=name,
                                            text=f"**Notes:** {notes} | **Quantity:** {quantity}",
                                            background_color=gfuncs.read_config_val("backgroundColor"),
                                            width=275,
                                            height="content",
                                            border_style="solid",
                                            border_color=gfuncs.read_config_val("textColor"),
                                            border_width=1,
                                            card_shadow=True,
                                            key=f"{key.replace(' ', '-')}_card"
                                            ):
                    # buttom for more data
                    if st_yled.button("View More", key=f"{curr_item["info"]["Name"]}_{key.replace(' ', '-')}_view", width="stretch"):
                        viewItem(key, i)
                    
                    # animation
                    gfuncs.apply_collection_icon_animation(f"{key.replace(' ', '-')}_card")
                st.space("medium")

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        if st.button("Add Items to Sub Collection"):
            addToSub()

