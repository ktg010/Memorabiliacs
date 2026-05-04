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
    #st_yled.init(CURR_THEME)
    st_yled.init()
    user_id = st.session_state.user_info["localId"]
    user_data_dict = backEnd.get_user_data(user_id)
    gfuncs.page_initialization(user_data_dict)
    gfuncs.apply_collectionpage_css()
    views = backEnd.collection_views(backEnd.CURR_COLL, db)
    ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
    view_mode = ref.get().to_dict()['settings']['collection view']
    items = backEnd.get_collection_items(backEnd.CURR_COLL)  # Use cached function
    coll_type = backEnd.CURR_COLL.split("_")[1]
    settings_page_flag = False
    viewing_flag = False
    st.session_state.createCustomItemPopup = False

    background = ref.get().to_dict().get("settings").get("background")
    if background != "" and user_data_dict["backgroundImageFlag"]:
        gfuncs.apply_background_image(background, user_data_dict["gradientBool"])
        

    @st.dialog(_("Edit")) 
    def edit_collection(sub):
        global ref
        subRef = ref.collection("Sub Collections").document(sub)
        itemSettings, rename = st.columns([3,2])
        with itemSettings:
            background = subRef.get().to_dict().get("settings").get("background")
            new_image_URL = st.text_input(_("URL of image to be used for background: "), value=background)
            currSize = backEnd.get_sub_coll_size(sub, backEnd.CURR_COLL)
            newSize = st.text_input(_("Change size of collection?"), value=currSize)
            if newSize.isdigit():
                if int(newSize) < currSize:
                    st.warning(_("Cannot change size to be smaller than current size"))
                elif int(newSize) > currSize:
                    subRef.update({"settings.size": int(newSize)})
            else:
                st.warning(_("Size must be a whole number"))
            if st.button(_("Remove Sub Collection")):
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
    @st.dialog(_("Collection Setting"))
    def viewCollSettings():
        global settings_page_flag
        if settings_page_flag:
            st.header(_("Settings"), text_alignment="center")
            st.subheader(_("New page"), text_alignment="center")
            global ref
            view_mode = st.radio(_("Display mode"), [_("grid"), _("column")], horizontal=True)
            hidden = st.checkbox(_("Hide Collection"), value=ref.get().to_dict()['settings']['hidden'])
            if st.button(_("Save")):
                ref.update({"settings.hidden" : hidden})
                ref.set({"settings" : {"collection view" : view_mode}}, merge=True)
                st.rerun()
        else: 
            st.header(_("Collection Views"), text_alignment="center")
            with st.container(horizontal_alignment="center"):
                st.subheader(_("Main Page View"), text_alignment="center")
                for name in ["Name", "Image", "Quantity" , "Notes"]:
                    st.checkbox(f"Hide {name}", key=name, value=(not views[name]))
                st.divider()

                st.subheader(_("Additional Data"), text_alignment="center")
                for view in views.keys():
                    if view not in ["Name", "Image", "Quantity" , "Notes"]:
                        st.checkbox(f"Hide {view}", key=view, value=(not views[view]))

            with st.container(horizontal_alignment="right"):
                if st.button(_("Save")):
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
    @st.dialog(_("Item Info"))
    def viewItem(item, index):
        global viewing_flag
        if viewing_flag:
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
                    if st.button(_("Save Changes")):
                        backEnd.get_collection_items.clear(backEnd.CURR_COLL)
                        db.collection('Custom').document(backEnd.CURR_COLL).update({f"items.{itemVals['Name']}": new_info})
                        db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL).update({f"items.{item}.notes": notes})
                        st.rerun()
                    if st.button(_("Cancel")):
                        st.rerun()
            else:
                ref = db.collection("Users").document(user_id).collection("Collections").document(backEnd.CURR_COLL)
                note = st.text_input(_("Item Note"), value=ref.get().to_dict()["items"][item].get('notes'), key="notes")
                if st.button(_("Save")):
                    backEnd.update_notes(item, note, db)
                    viewing_flag = False
                    st.rerun()
        else:
            field_text = ""
            if items[item]['info'].get("items"):
                custom_name = items[item]['info']["items"][list(items[item]['info']['items'].keys())[index]]["Name"]
                with st_yled.badge_card_one(title=custom_name, text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                    # try:
                    #     st.image(gfuncs.get_image_from_URL(items[item]['info']["Image"]), width=200)
                    # except Exception:
                    #     st.image(items[item]['info']["Image"], width="stretch")
                    for key in items[item]['info']['items'][custom_name].keys():
                        if key not in ("Name", "Image"):
                            if views[key]:
                                st.write(f"**{key}**: **{items[item]['info']['items'][custom_name][key]}**")
                    st.divider()
                    st.header(_("Personal Fields"))
                    notes = items[item].get("notes")
                    if notes != "Enter notes here":
                        st.write(f"Notes: {notes}")
                    else:
                        st.write(_("Notes: "))
                    st.write(f"Number owned: {items[item].get('quantity')}")
                    st.divider()
                    if st.button(_("Edit Note")):
                        viewing_flag = True
                        st.rerun(scope="fragment")
                    if st.button(_("Remove From Collection")):
                        st.audio(gfuncs.DEFAULT_SOUNDS["Delete"], autoplay=True, width=1, start_time=0)
                        time.sleep(1)
                        backEnd.delete_reference(item, db)
                        st.rerun()
            else:
                with st_yled.badge_card_one(title=items[item]['info']["Name"], text=field_text, badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                    for key in items[item]['info'].keys():
                        if key not in ("Name", "Image", 'id'):
                            if coll_type == "Custom":
                                st.write(f"**{key}**: **{items[item]['info'][key]}**")
                            else:
                                if views[key]:
                                    st.write(f"**{key}**: **{items[item]['info'][key]}**")
                    st.divider()
                    st.header(_("Personal Fields"))
                    notes = items[item].get("notes")
                    if notes != "Enter notes here":
                        st.write(f"Notes: {notes}")
                    else:
                        st.write(_("Notes: "))
                    st.write(f"Number owned: {items[item].get("quantity")}")
                    st.divider()
                    if st.button(_("Edit Note")):
                        viewing_flag = True
                        st.rerun(scope="fragment")
                    if st.button(_("Remove From Collection")):
                        st.audio(gfuncs.DEFAULT_SOUNDS["Delete"], autoplay=True, width=1, start_time=0)
                        time.sleep(1)
                        backEnd.delete_reference(item, db)
                        st.rerun()

    @st.dialog(_("Create Sub Collection"))
    def subColl():
        name = st.text_input(_("Name your sub collection"))
        size = st.text_input(_("What is the size of the collection"))
        if st.button(_("Save")):
            if size.isdigit():
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, size, db)
                st.rerun()
            elif size == "":
                backEnd.create_sub_collection(name, backEnd.CURR_COLL, 999, db)
                st.rerun()
            else:
                st.error(_("Size needs to be a whole number"))

    st_yled.text(f"{backEnd.CURR_COLL.split('_')[0]}", text_alignment="center", font_size="1.75rem")
    with st.container(horizontal_alignment="right"):
        if st.button(_("Collection Settings"), icon=":material/settings:", type="tertiary"):
            settings_page_flag = False
            viewCollSettings()

    num_of_fields = 0
    @st.fragment
    @st.dialog(_("Template Info"))
    def createCustomTemplate():
        global num_of_fields
        template = ["Image", "Name"]
        if num_of_fields == 0:
            with st_yled.badge_card_one(title=_('Create Custom Template'), text='', badge_text=_("Attributes"), width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                num_of_fields = st.number_input(_("Enter number of attributes: "), value=num_of_fields, key="numoffields")
                if st.button(_("Create"), key='Create'):
                    st.rerun(scope='fragment')
        elif num_of_fields > 0:
            with st_yled.badge_card_one(title=_('Create Custom Template'), text='', badge_text=_("Attributes"), width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
                tempName = st.text_input(_("Enter template name: "), value="here")
                st.divider()
                for index in range(0,num_of_fields):
                    value = (st.text_input(_("Enter attribute name: "), value="here", key=index))
                    if value != "here" and value != "Name" and value != "name":
                        template.append(value.title())
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
    
    if "createCustomItemPopup" not in st.session_state:
        st.session_state.createCustomItemPopup = False
    # Make function give popup based on selected template with text inputs
    
    @st.dialog(_("Item Info"))
    def createCustomItem(template):
        attributes = {}
        db = backEnd.get_firestore_client()
        user_id = st.session_state.user_info["localId"]
        template = db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).get().to_dict()['templates'][template]
       
        with st_yled.badge_card_one(title=_("Enter values"), text='', badge_text=_("Attributes"), width="stretch", badge_color="primary", background_color=gfuncs.read_config_val( "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val( "textColor"), border_width=1):
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
                    db = backEnd.get_firestore_client()
                    user_id = st.session_state.user_info["localId"]
                    if uploaded:
                        blob_name = backEnd.upload_user_image(uploaded, user_id, db)
                        attribute= blob_name
                        st.success(_("Image uploaded."))
                        attribute = blob_name
                    else:
                        attribute = ''
                if attribute != "":
                    attributes[template[i]] = attribute
                        
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

    st.space("large")
    # all items for custom
    with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
        cols = st.columns(3, width="stretch") 
        for i, key in enumerate(items.keys()):
            # display either grid or column view
            if view_mode == _("grid"):
                col = cols[i % 3]
            else: 
                col = cols[1]
            curr_item = items[key]
            if curr_item["info"].get("items"):
                with col.container(horizontal_alignment="center", key=f"{key.replace(' ', '-')}_container"):
                    if views["Name"]:
                        st_yled.text(f"{curr_item['info'].get('Name', list(curr_item["info"]["items"].keys())[i])}", text_alignment="center", font_size="1.75rem")

                    if views["Image"]:
                        if backEnd.CURR_COLL.split("_")[1] == "Custom":
                            if curr_item["info"].get("items"):
                                st.image(backEnd.get_cloud_storage_image(curr_item["info"]["items"][list(curr_item["info"]["items"].keys())[i]]["Image"]), width=200)
                            else:
                                #UPC Item
                                st.image((curr_item["info"]["Image"]), width=200)
                        else:
                            try:
                                st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)
                            except Exception:
                                st.image(curr_item["info"]["Image"], width=200)

                    if views["Quantity"]:
                        st_yled.text(f"x{curr_item.get("quantity")}", text_alignment="center", font_size="1rem")
                    
                    if views["Notes"]:
                        notes = curr_item.get("notes")
                        if notes != "Enter notes here" and notes != "Your notes here":
                            st_yled.text(f"{notes}", text_alignment="center", font_size="1rem")
                        else:
                            st_yled.text(_("Enter notes here"), text_alignment="center", font_size="1rem" , color=gfuncs.read_config_val("backgroundColor"))    

                    if st_yled.button(_("View More"), key=f"{curr_item['info'].get('Name', key)}_{key}_view"):
                        viewItem(key, i)
                    gfuncs.apply_collectionpage_icon_animation(f"{key.replace(' ', '-')}_container")
            else:
                
                with col.container(horizontal_alignment="center", key=f"{key}_container"):
                    if views["Name"]:
                        st_yled.text(f"{curr_item['info'].get('Name')}"[:15], text_alignment="center", font_size="1.75rem")

                    if views["Image"]:
                        if backEnd.CURR_COLL.split("_")[1] == "Custom":
                            if curr_item["info"].get("items"):
                                st.image(backEnd.get_cloud_storage_image(curr_item["info"]["items"][list(curr_item["info"]["items"].keys())[i]]["Image"]), width=200)
                            else:
                                #UPC Item
                                st.image((curr_item["info"]["Image"]), width=200)
                        else:
                            try:
                                st.image(gfuncs.get_image_from_URL(curr_item["info"]["Image"]), width=200)
                            except Exception:
                                st.image(curr_item["info"]["Image"], width=200)

                    if views["Quantity"]:
                        st_yled.text(f"x{curr_item.get("quantity")}", text_alignment="center", font_size="1rem")
                    
                    if views["Notes"]:
                        notes = curr_item.get("notes")
                        if notes != "Enter notes here" and notes != "Your notes here":
                            st_yled.text(f"{notes}", text_alignment="center", font_size="1rem")
                        else:
                            st_yled.text(_("Enter notes here"), text_alignment="center", font_size="1rem" , color=gfuncs.read_config_val("backgroundColor"))
                    

                    if st_yled.button(_("View More"), key=f"{curr_item["info"]["Name"]}_{key}_view"):
                        viewItem(key, i)
                    gfuncs.apply_collectionpage_icon_animation(f"{key}_container")
                    st.space("medium")
    
    st.space("large")
    wishlist = backEnd.get_collection_wishlisted(backEnd.CURR_COLL)
    if wishlist != {}:
        st.divider()
        st.subheader(_("Wishlisted Items"), text_alignment="center")
        st.space("small")
        with st.container(horizontal=True, horizontal_alignment="center", width="stretch"):
            st.space("small")
            wishCols = st.columns(3, width="stretch") 
            for i, key in enumerate(wishlist.keys()):
                if view_mode == _("grid"):
                    col = wishCols[i % 3]
                else: 
                    col = wishCols[1]
                with col.container(horizontal_alignment="center"):
                    st_yled.text(wishlist[key].get("Name"),text_alignment="center", font_size="1.75rem")
                    st.image(gfuncs.image_grayscale(wishlist[key].get("Image")))
                    st_yled.text(f"{key.replace("_", "-")}", text_alignment="center", font_size="1rem")
    

    # Container in bottom right for add button
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="bottom"):
        collection = {
            "name" : backEnd.CURR_COLL.split("_")[0],
            "type" : backEnd.CURR_COLL.split("_")[1]
        }

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
                st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)

        else:    
            st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)
        
        if st.button(_("Create Sub Collection")):
            backEnd.get_template_types.clear()
            subColl()
            
# Uncomment below code to test GCS/firestore image upload and retrieval, leaving here for others to mess with as needed
# RN you can search images by their actual document id on firestore rather than name, will change later 


#db = backEnd.get_firestore_client()
#user_id = st.session_state.user_info["localId"]
#
#test_doc_id = st.text_input("Image doc id")
#if test_doc_id and st.button("Test fetch URL"):
#    url = backEnd.get_user_image_url(user_id, db, test_doc_id)
#    st.write(url)
#    if url:
#        st.image(url)
#
#names = backEnd.get_user_image_names(user_id, db)
#st.write("User image names:")
#for name in names:
#    st.write(name)