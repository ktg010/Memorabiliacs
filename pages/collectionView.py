import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
import st_yled
import os

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


    # cloud_image_url = backEnd.get_cloud_storage_image("pikachu.jpeg")  # Example usage of cached image retrieval

    # st.image(cloud_image_url, width=200)  # Display the image from Cloud Storage
    
    coll_type = backEnd.CURR_COLL.split("_")[1]
    
    items = backEnd.get_collection_items(backEnd.CURR_COLL)  # Use cached function
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
                if key not in ("Name", "Image", "Rarity", "ID"):
                    if views[key]:
                        st.write(f"**{key}**: **{items[item]['info'][key]}**")
            if st.button(_("Remove From Collection")):
                backEnd.delete_reference(item, db)
      
    @st.dialog("Template Info")
    def createCustomTemplate():
        template = []
        with st_yled.badge_card_one(title='Create Custom Template', text='', badge_text="Attributes", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
            tempName = st.text_input("Enter template name: ", value="here")
            for index in range(0,10):
                value = (st.text_input("Enter attribute name: ", value="here", key=index))
                if value != "here":
                    template.append(value)
        if st_yled.button(_("Create Template"), key='CT'):
            # Make Template arrays in both locations
            db.collection('Custom').document(backEnd.CURR_COLL).update({"templates": {tempName: template}})
            db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).update({f"templates.{tempName}": template})
            backEnd.get_collection_items.clear(backEnd.CURR_COLL)
    
    if "createCustomItemPopup" not in st.session_state:
        st.session_state.createCustomItemPopup = False
    # Make function give popup based on selected template with text inputs
    
    @st.dialog("Item Info")
    def createCustomItem(template):
        attributes = {}
        template = db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).get().to_dict()['templates'][template]
        with st_yled.badge_card_one(title="Enter values", text="", badge_text="New item", width="stretch", badge_color="primary", background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
            if ("name" in template) == False and ("Name" in template) == False:
                name = st.text_input("Name", value="", key="force_name")
            for i in range(len(template)):
                attribute = st.text_input(_(template[i]), value="", key=i)
                if template[i] == "name" or template[i] == "Name":
                    name = attribute
                if attribute != "":
                    attributes[template[i]] = attribute
            if st_yled.button(_("Create"), key="CreateKey"):
                new_item_id = db.collection('Custom').document(backEnd.CURR_COLL)
                db.collection('Custom').document(backEnd.CURR_COLL).update({
                    "items": {name: attributes}
                })
                db.collection('Users').document(user_id).collection('Collections').document(backEnd.CURR_COLL).update({
                    f"items.{name}": {
                        "notes": "Your notes here",
                        "ref": new_item_id   
                        }
                    })
                st.session_state.createCustomItemPopup = False
                backEnd.get_collection_items.clear(backEnd.CURR_COLL)
                st.rerun()

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
                if coll_type == "Custom" and items == None:
                    pass
                else:
                    if coll_type == "Custom":
                        # Make custom item list match format of normal item list
                        item_list = db.collection('Custom').document(backEnd.CURR_COLL).get().to_dict()['items']
                    for i, key in enumerate(items.keys()):
                        col = cols[i % 3]
                        print(f'items = {items}')
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
        collection = {
            "name" : backEnd.CURR_COLL.split("_")[0],
            "type" : backEnd.CURR_COLL.split("_")[1]
        }

        # TODO
        #  Translate string 
        # Change create custom to load a value into the templates map called "no custom template" which will be removed/ovewritten
        #  after the creation of the user's first template.

        if coll_type == "Custom":
            types = backEnd.get_template_types()
            print(f"Types = {types}")     
            template = st.selectbox(_("Type"), types) 
              
            st.page_link(page="pages/search.py", label=_("Add Existing Item"), query_params=collection)
            if st_yled.button(_("New Custom Template"), key="NCT"):
                createCustomTemplate()
            # Make function to display list of templates
            if st_yled.button(_("New Custom Item"), key="NCI"):
                st.session_state.createCustomItemPopup = True
            if st.session_state.createCustomItemPopup == True:
                createCustomItem(template)
        else:    
            st.page_link(page="pages/search.py", label=_("Add to Collection"), query_params=collection)  
            
