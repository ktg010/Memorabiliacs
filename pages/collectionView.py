import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled
import os
import time

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
    # local variables
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    views = backEnd.collection_views(backEnd.CURR_COLL)
    ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
    view_mode = ref.get().to_dict()['settings']['collection view']
    items = backEnd.get_collection_items(backEnd.CURR_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]
    settings_page_flag = False
    viewing_flag = False
    num_of_fields = 0
    background = ref.get().to_dict().get("settings").get("background")
    st.session_state.createCustomItemPopup = False

    # page initialization
    st_yled.init()
    gfuncs.page_initialization(user_data_dict)
    gfuncs.apply_collectionpage_css()

    ### Dialog Popups ###
    # editing sub collections
    @st.dialog(_("Edit")) 
    def edit_sub_collection(sub):
        global ref
        subRef = ref.collection("Sub Collections").document(sub)

        # splits settings popup
        itemSettings, rename = st.columns([3,2])
        with itemSettings:
            # background image
            background = subRef.get().to_dict().get("settings").get("background")
            new_image_URL = st.text_input(_("URL of image to be used for background: "), value=background)

            # size 
            currSize = backEnd.get_sub_coll_size(sub, backEnd.CURR_COLL)
            newSize = st.text_input(_("Change size of collection?"), value=currSize)

            # remove sub collection button
            if st.button(_("Remove Sub Collection")):
                backEnd.delete_sub_collection(sub, backEnd.CURR_COLL)
                st.rerun()
        
        with rename:
            st_yled.subheader(f"{_('Rename')} {sub}?", text_alignment="center")
            sub_rename = st.text_input(" ")

        with st.container(horizontal=True, horizontal_alignment="right"):
            # updates settings
            if st.button(_("Save")):
                # size number check
                if newSize.isdigit():
                    if int(newSize) < currSize:
                        st.warning(_("Cannot change size to be smaller than current size"))
                    elif int(newSize) > currSize:
                        subRef.update({"settings.size": int(newSize)})
                else:
                    st.warning(_("Size must be a whole number"))

                # image check
                if new_image_URL != "" and "https:" in new_image_URL: 
                    subRef.update({"settings.background" : new_image_URL})

                # rename check
                if sub_rename != "":
                    if backEnd.rename_sub_collection(backEnd.CURR_COLL, sub, sub_rename):
                        st_yled.error(_("Sub Collection name already exists"))
                    else:
                        backEnd.get_sub_collections.clear(backEnd.CURR_COLL)
                        st.rerun()
                else:
                    st.rerun()
    
    # collection settings
    @st.fragment
    @st.dialog(_("Collection Setting"))
    def viewCollSettings():
        global settings_page_flag

        # split for different pages
        if settings_page_flag:
            # wider collection settings
            global ref
            st.header(_("Collection Settings"), text_alignment="center")
            st.space("small")

            view_mode = st.radio(_("Display mode"), [_("grid"), _("column")], horizontal=True)
            hidden = st.checkbox(_("Hide Collection"), value=ref.get().to_dict()['settings']['hidden'])

            # updates settings
            if st.button(_("Save")):
                ref.update({"settings.hidden" : hidden})
                ref.set({"settings" : {"collection view" : view_mode}}, merge=True)
                st.rerun()
        else: 
            # item view toggles
            st.header(_("Collection Views"), text_alignment="center")
            with st.container(horizontal_alignment="center"):
                # views on main display page
                st.subheader(_("Main Item View"), text_alignment="center")
                st.space("small")
                for name in ["Quantity" , "Notes"]:
                    st.checkbox(f"Hide {name}", key=name, value=(not views[name]))
                st.divider()

                # views for more data
                st.subheader(_("Additional Data"), text_alignment="center")
                st.space("small")
                for view in views.keys():
                    if view not in ["Name", "Image", "Quantity" , "Notes"]:
                        st.checkbox(f"Hide {view}", key=view, value=(not views[view]))

            with st.container(horizontal_alignment="right"):
                # updates settings
                if st.button(_("Save")):
                    newViews = {}
                    for view in views.keys():
                        newViews[view] = not st.session_state[view]
                    backEnd.update_collection_views(backEnd.CURR_COLL, newViews)
                    st.rerun()

        # arrows to change pages
        with st.container(horizontal=True, horizontal_alignment="center"):
            if st.button("", icon=":material/arrow_back_ios:"):
                settings_page_flag = False
                st.rerun(scope="fragment")

            if st.button("", icon=":material/arrow_forward_ios:"):
                settings_page_flag = True
                st.rerun(scope="fragment")
    
    # viewing more about item
    @st.fragment
    @st.dialog(_("Item Info"))
    def viewItem(item, index):
        global viewing_flag

        # split for viewing and editing
        if viewing_flag:
            # custom check, can edit everything about item
            if coll_type == "Custom":
                new_info = {}
                itemVals = items[item]['info']["items"][list(items[item]['info']['items'].keys())[index]]
                custom_name = itemVals["Name"]

                with st_yled.badge_card_one(
                    title=f"Edit {custom_name}",text="",badge_text="Attributes",width="stretch",badge_color="primary",background_color=gfuncs.read_config_val("backgroundColor"),card_shadow=True,border_style="solid",border_color=gfuncs.read_config_val("textColor"),border_width=1, key=f'Edit {item}'):
                    for key in itemVals:
                        if views[key]:
                            if 'user_uploads' in itemVals[key]:
                                value = st.text_input(f"**{key}**:", value='Uploaded Image', key=f"{item}_{key}")
                            else:
                                value = st.text_input(f"**{key}**:", value=itemVals[key], key=f"{item}_{key}")
                            new_info[key] = value
                    notes = st.text_input("Notes: ", value=items[item]['notes'], key=f"{item}_{key}notes")

                    # updates changes
                    if st.button(_("Save Changes")):
                        backEnd.get_collection_items.clear(backEnd.CURR_COLL)
                        db.collection('Custom').document(backEnd.CURR_COLL).update({f"items.{itemVals['Name']}": new_info})
                        db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL).update({f"items.{item}.notes": notes})
                        viewing_flag = False
                        st.rerun()

                    if st.button(_("Cancel")):
                        st.rerun()

            # normal items, can only edit user's notes
            else:
                ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
                note = st.text_input(_("Item Note"), value=ref.get().to_dict()["items"][item].get('notes'), key="notes")

                # updates changes
                if st.button(_("Save")):
                    backEnd.update_notes(item, note, backEnd.CURR_COLL)
                    viewing_flag = False
                    st.rerun()
        else:
            # viewing more about items
            field_text = ""

            # check for custom items
            if items[item]['info'].get("items"):
                custom_name = items[item]['info']["items"][list(items[item]['info']['items'].keys())[index]]["Name"]

                # per item info
                with st_yled.badge_card_one(title=custom_name, 
                                            text=field_text, 
                                            badge_text="Attributes", 
                                            width="stretch", 
                                            badge_color="primary", 
                                            background_color=gfuncs.read_config_val("backgroundColor"), 
                                            card_shadow=True, 
                                            border_style="solid", 
                                            border_color=gfuncs.read_config_val("textColor"), 
                                            border_width=1):
                    # data display
                    dataframe_dict = {}
                    for key in items[item]['info']['items'][custom_name].keys():
                        if key not in ("Name", "Image"):
                            if views[key]:
                                # splits lists and dicts to be more readable
                                if isinstance(items[item]['info']['items'][custom_name][key], list):
                                        dataframe_dict[key] = "".join(str(items[item]['info']['items'][custom_name][key])).replace("[", "").replace("]", "").replace("{", "").replace("}", "\n").replace(",", "\n")
                                elif isinstance(items[item]['info']['items'][custom_name][key], dict):
                                        dataframe_dict[key] = "".join(str(items[item]['info']['items'][custom_name][key])).replace("{", "").replace("}", "\n").replace(",", "\n")
                                else:
                                    dataframe_dict[key] = items[item]['info']['items'][custom_name][key]

                    st.dataframe(dataframe_dict, height=500, width="stretch", row_height=(500//len(dataframe_dict)) if len(dataframe_dict) > 0 else 500)
                    st.divider()

                    # per user info
                    st.header(_("Personal Fields"))
                    notes = items[item].get("notes")

                    if notes != "Enter notes here":
                        st.write(f"Notes: {notes}")
                    else:
                        st.write(_("Notes: "))

                    st.write(f"Number owned: {items[item].get('quantity')}")
                    st.divider()

                    # change to edit item
                    if st.button(_("Edit Item")):
                        viewing_flag = True
                        st.rerun(scope="fragment")

                    # removes item
                    if st.button(_("Remove From Collection")):
                        time.sleep(1)
                        backEnd.delete_reference(item, backEnd.CURR_COLL)
                        st.rerun()
            
            # normal items
            else:
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

                    st.write(f"Number owned: {items[item].get("quantity")}")
                    st.divider()

                    # change to edit note
                    if st.button(_("Edit Note")):
                        viewing_flag = True
                        st.rerun(scope="fragment")

                    # removes item
                    if st.button(_("Remove From Collection")):
                        time.sleep(1)
                        backEnd.delete_reference(item, backEnd.CURR_COLL)
                        st.rerun()

    # create sub collection
    @st.dialog(_("Create Sub Collection"))
    def subColl():
        # user input
        name = st.text_input(_("Name your sub collection"))
        size = st.text_input(_("What is the size of the collection"))

        # trys to create sub collection
        if st.button(_("Save")):
            if size.isdigit():
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, size)
                st.rerun()
            elif size == "":
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, 999)
                st.rerun()
            else:
                st.error(_("Size needs to be a whole number"))

    # template creation for custom items
    @st.fragment
    @st.dialog(_("Template Info"))
    def createCustomTemplate():
        global num_of_fields
        template = ["Image", "Name"]

        # empty, asks for number of attributes
        if num_of_fields == 0:
            with st_yled.badge_card_one(title=_('Create Custom Template'), text='', 
                                        badge_text=_("Attributes"), width="stretch", 
                                        badge_color="primary", 
                                        background_color=gfuncs.read_config_val("backgroundColor"),
                                        card_shadow=True, border_style="solid", 
                                        border_color=gfuncs.read_config_val("textColor"), 
                                        border_width=1):
                num_of_fields = st.number_input(_("Enter number of attributes: "), value=num_of_fields, key="numoffields")

                if st.button(_("Create"), key='Create'):
                    st.rerun(scope='fragment')
        
        # ask user to input attribute information
        elif num_of_fields > 0:
            with st_yled.badge_card_one(title=_('Create Custom Template'), 
                                        text='', badge_text=_("Attributes"), 
                                        width="stretch", badge_color="primary", 
                                        background_color=gfuncs.read_config_val("backgroundColor"), 
                                        card_shadow=True, border_style="solid", 
                                        border_color=gfuncs.read_config_val("textColor"), 
                                        border_width=1):
                tempName = st.text_input(_("Enter template name: "), value="here")
                st.divider()
                st.warning("Name and Image are already created")

                for index in range(num_of_fields):
                    value = (st.text_input(_("Enter attribute name: "), value="here", key=index))
                    if value != "here" and value != "Name" and value != "name":
                        template.append(value.title())

            # makes template
            if st.button(_("Create Template"), key='CT'):
                # Make Template arrays in both locations
                db.collection('Custom').document(backEnd.CURR_COLL).update({f"templates.{tempName}" : template})

                for key in template:
                    db.collection('Custom').document(backEnd.CURR_COLL).update({f'settings.views.{key}': 'True'})
                    db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).update({f'settings.views.{key}': 'True'})
                
                db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).update({f"templates.{tempName}": template})
                backEnd.get_template_types.clear()
                num_of_fields = 0
                st.rerun()
    
    # created custom item from template
    @st.dialog(_("Item Info"))
    def createCustomItem(template):
        attributes = {}
        db = backEnd.get_firestore_client()
        user_id = st.session_state.user_info["localId"]
        template = db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).get().to_dict()['templates'][template]
       
        # list to fill out item's info
        with st_yled.badge_card_one(title=_("Enter values"), 
                                    text='', badge_text=_("Attributes"), 
                                    width="stretch", badge_color="primary", 
                                    background_color=gfuncs.read_config_val("backgroundColor"), 
                                    card_shadow=True, border_style="solid", 
                                    border_color=gfuncs.read_config_val( "textColor"), 
                                    border_width=1):
            
            if "name" not in template and "Name" not in template:
                name = st.text_input(_("Name"), value="", key="force_name")

            if "quantity" not in template and "Quantity" not in template:
                quantity = st.text_input(_("Quantity"), value=1, key="force_quantity") # value default to 1

            for i in range(len(template)):
                attribute = st.text_input(_(template[i]), value="", key=i)
                if template[i] == "name" or template[i] == "Name":
                    name = attribute

                if template[i] == "quantity" or template[i] == "Quantity":
                    quantity = attribute

                if template[i] == "Image":
                    uploaded = st.file_uploader("Upload image to GCS", type=["png", "jpg", "jpeg", "webp"])
                    user_id = st.session_state.user_info["localId"]

                    if uploaded:
                        blob_name = backEnd.upload_user_image(uploaded)
                        attribute= blob_name
                        st.success(_("Image uploaded."))
                        attribute = blob_name
                    else:
                        attribute = ''

                if attribute != "":
                    attributes[template[i]] = attribute
            
            # creates item
            if st_yled.button(_("Create"), key="CreateKey"):
                new_item_id = db.collection('Custom').document(backEnd.CURR_COLL)
                db.collection('Custom').document(backEnd.CURR_COLL).set({
                    "items": {name: attributes}
                }, merge=True)
                db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).set({
                    "items":
                            {name: {
                                "notes": "Your notes here",
                                "ref": new_item_id,
                                'quantity' : quantity  # Default to 1 if quantity is not set   
                                }
                            }
                    }, merge=True)
                st.session_state.createCustomItemPopup = False
                backEnd.get_collection_items.clear(backEnd.CURR_COLL)
                st.rerun()
    
    # adds wishilsted item to collection
    @st.dialog("Add to Collection")
    def add_item_to_coll(item, name, collection):
        # user input
        st.write(name)
        notes = st.text_input("Add notes", value="Enter notes here")
        quantity = st.text_input("How many", value="1")

        # updates collection
        if st.button("Save"):
            if quantity.isdigit():
                backEnd.add_item(item, notes, int(quantity), collection)
                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=name, collection=collection.split('_')[0]))
                st.rerun()
            else:
                st.error("Quantity must be a whole number")


    ### Main Page Display ###
    # title
    st_yled.text(f"{backEnd.CURR_COLL.split('_')[0]}", text_alignment="center", font_size="1.75rem")
    with st.container(horizontal_alignment="right"):
        # collection settings
        if st.button(_("Collection Settings"), icon=":material/settings:", type="tertiary"):
            settings_page_flag = False
            viewCollSettings()

    # sub collections
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        for subCollection in backEnd.get_sub_collections(backEnd.CURR_COLL):

            # displays sub collection
            with st.container(width="content", horizontal_alignment="center"):
                with st_yled.badge_card_one(badge_text="Sub Collection", 
                                            title=f"{subCollection}", 
                                            text=f"**{_('Type')}: {coll_type}**", 
                                            background_color=gfuncs.read_config_val("backgroundColor"), 
                                            width=250, 
                                            height=350, 
                                            border_style="solid", 
                                            border_color=gfuncs.read_config_val("textColor"), 
                                            border_width=1):
                    # button to go to sub collection
                    if st_yled.button(_("View Collection"), border_width=5, key=f"{subCollection}_link", width="stretch"):
                        backEnd.set_sub_collection(subCollection)
                        st.switch_page(gfuncs.sub_coll_page)

                    # button for editing some sub collection settings
                    if st_yled.button(_("Edit"), border_width=5, key=f"edit_{subCollection}", width="stretch"):
                        edit_sub_collection(subCollection)
    st.space("large")

    # displays all items
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        # display spacing
        cols = st.columns(3, width="stretch") 
        for i, key in enumerate(items.keys()):
            curr_item = items[key]

            # display either grid or column view
            if view_mode == _("grid"):
                col = cols[i % 3]
            else: 
                col = cols[1]

            # custom item check
            if curr_item["info"].get("items"):
                # gets item information
                with col.container(horizontal_alignment="center", key=f"{key.replace(' ', '-')}_container"):
                    name = f"{curr_item['info'].get('Name', list(curr_item["info"]["items"].keys())[i])}"
                    
                    # image
                    if curr_item["info"].get("items"):
                        image = backEnd.get_cloud_storage_image(curr_item["info"]["items"][list(curr_item["info"]["items"].keys())[i]]["Image"])
                    else:
                        #UPC Item
                        image = curr_item["info"]["Image"]
            
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

                    # diplay
                    with st_yled.image_card_one(
                                                title=f"{name}",
                                                image_path=image,
                                                text=moreText,
                                                background_color=gfuncs.read_config_val("backgroundColor"),
                                                width=275,
                                                height="content",
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
                                                key=f"{key.replace(' ', '-')}_card"
                                                ):
                        # botton for more data
                        if st_yled.button(_("View More"), key=f"{curr_item['info'].get('Name', key)}_{key}_view", width="stretch"):
                            viewItem(key, i)

                        # animation
                        gfuncs.apply_collectionpage_icon_animation(f"{key.replace(' ', '-')}_card")
                    st.space("medium")
            
            # normal items
            else:
                # gets item information
                with col.container(horizontal_alignment="center", key=f"{key}_container"):
                    name = curr_item['info'].get('Name')

                    # imagae
                    try:
                        image = gfuncs.get_image_from_URL(curr_item["info"]["Image"])
                    except Exception:
                        image = curr_item["info"]["Image"]

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
                                                title=f"{name}",
                                                image_path=image,
                                                text=moreText,
                                                background_color=gfuncs.read_config_val("backgroundColor"),
                                                width=275,
                                                height="content",
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
                                                key=f"{key.replace(' ', '-')}_card"
                                                ):
                        # botton for more data
                        if st_yled.button(_("View More"), key=f"{curr_item["info"]["Name"]}_{key}_view", width="stretch"):
                            viewItem(key, i)

                        # animation 
                        gfuncs.apply_collectionpage_icon_animation(f"{key}_card")
                    st.space("medium")
        st.space("medium")
    st.space("large")

    # wishlisted items
    wishlist = backEnd.get_collection_wishlisted(backEnd.CURR_COLL)
    # displays if has items
    if wishlist != {}:
        st.divider()
        st.subheader(_("Wishlisted Items"), text_alignment="center")
        st.space("small")

        with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
            # item spacing
            wishCols = st.columns(3, width="stretch") 
            for i, key in enumerate(wishlist.keys()):
                if view_mode == _("grid"):
                    col = wishCols[i % 3]
                else: 
                    col = wishCols[1]
                
                # item display
                with col.container(horizontal_alignment="center"):
                    name = wishlist[key].get("Name")
                    image = gfuncs.image_grayscale(wishlist[key].get("Image"))
                    with st_yled.image_card_one(
                                                title=f"{name}",
                                                image_path=image,
                                                text=f"**Item ID:** {key.replace("_", "-")}",
                                                background_color=gfuncs.read_config_val("backgroundColor"),
                                                width=275,
                                                height="content",
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
                                                key=f"{key.replace('_', '-')}_wishlist_card"
                                                ):
                        # adds to collection
                        if st_yled.button(_("Quick Add"), key=f"{wishlist[key].get('Name', key)}_{key}_wishlist_add", width="stretch"):
                            add_item_to_coll(key.replace("_", "-"), name, backEnd.CURR_COLL)
                            pass
    

    # Container in bottom right buttons
    with st.container(horizontal_alignment="right", vertical_alignment="bottom"):
        # collection naming
        collection = {
            "name" : backEnd.CURR_COLL.split("_")[0],
            "type" : backEnd.CURR_COLL.split("_")[1]
        }

        # template and item adding for custom
        if coll_type == "Custom":
            types = backEnd.get_template_types()

            if types != ['UPC ITEMS']:     
                template = st.selectbox(_("Type"), types, key="template_select")

                if st_yled.button(_("New Custom Template"), key="NCT"):
                    createCustomTemplate()

                # Make function to display list of templates
                if st_yled.button(_("New Custom Item"), key="NCI"):
                    st.session_state.createCustomItemPopup = True

                if st.session_state.createCustomItemPopup:
                    if template != "No Custom Template":
                        createCustomItem(template)
                    else:
                        st.warning(_("Please select (or create) a template to create an item"))
            else:    
                # switches to search page with pre-filled fields
                st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)

        else:    
            # switches to search page with pre-filled fields
            st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)
        
        # sub collection creation
        if st.button(_("Create Sub Collection")):
            backEnd.get_template_types.clear()
            subColl()
            