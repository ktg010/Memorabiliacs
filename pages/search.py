import streamlit as st
import BackendMethods.global_functions as gfuncs
import BackendMethods.backendfuncs as backEnd
from BackendMethods.translations import _
from time import sleep
import st_yled
import os

st.session_state["last_code"] = ""

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
try:
    db = backEnd.get_firestore_client()
    user_id = st.session_state.user_info["localId"]
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()    

## -------------------------------------------------------------------------------------------------
## Logged in ---------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    #st_yled.init(CURR_THEME)
    st_yled.init()
    user_data_dict = backEnd.get_user_data(user_id)
    gfuncs.page_initialization(user_data_dict)
    collection = st.query_params

    if st.button("Back"):
        if collection == {}:
            backEnd.set_collection("")
            backEnd.set_sub_collection("")
            st.switch_page(gfuncs.home_page)
        else:
            st.switch_page(gfuncs.collection_page)
    
    @st.dialog("Add to Collection")
    def add_item_to_coll(item_id, name):
        st.write(name)
        notes = st.text_input("Add notes", value="Enter notes here")
        quantity = st.text_input("How many", value="1")
        if st.button("Save"):
            if quantity.isdigit():
                backEnd.add_item(item_id, notes, quantity, db)
                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=name, collection=backEnd.CURR_COLL.split('_')[0]))
                sleep(.5)
                st.rerun()
            else:
                st.error("Quantity must be a whole number")

    st_yled.subheader(_("Search for Collectables!"), text_alignment="center")
    st.space("small")
    outer_cols = st.columns([1, 3, 1])
    with outer_cols[1]:
        col_left, col_right = st.columns([3, 2], width=1000, border=True, )


        all_types = backEnd.get_collection_types()
        collSearch = None if (collection == {}) else all_types.index(collection["type"])

        # Search type selector (left column)
        search_type = col_left.selectbox(
            _("What would you like to search for?"),
            options=all_types,
            index=collSearch
        )

        # Collection selector (right column) - list user's collections except DefaultCollection
        try:
            collections_docs = backEnd.get_user_collections(user_id)
            collections = [doc['id'] for doc in collections_docs if not doc['id'].startswith("DefaultCollection")]
            display_collections = [name.split("_")[0] for name in collections if name.split("_")[1]==search_type]
        except Exception:
            collections = []

        if not collections:
            collections = [_("(No collections)")]

        # Persist selection in session state
        default_index = None if (collection == {}) else display_collections.index(collection["name"]) if collection["name"] in display_collections else None
        selected_collection = col_right.selectbox(_("Add items to collection:"), options=display_collections, index=default_index, key="selected_collection")

        

        # Set backend current collection for add actions
        if selected_collection and selected_collection != _("(No collections)"):
            try:
                collections_docs = backEnd.get_user_collections(user_id)
                collections = [doc['id'] for doc in collections_docs if not doc['id'].startswith("DefaultCollection")]
                display_collections = [name.split("_")[0] for name in collections if name.split("_")[1]==search_type]
            except Exception:
                collections = []

            if not collections:
                collections = [_("(No collections)")]

            # Set backend current collection for add actions
            if selected_collection and selected_collection != _("(No collections)"):
                try:
                    backEnd.set_collection(collections[collections.index(selected_collection+"_"+search_type)])
                except Exception:
                    backEnd.CURR_COLL = collections[collections.index(selected_collection+"_"+search_type)]
            else:
                try:
                    backEnd.set_collection("")
                except Exception:
                    backEnd.CURR_COLL = ""
            if search_type == "Custom":
                input_mode = st_yled.radio(_("Input source"), options=[_("Upload"), _("Camera")], horizontal=True)
                enhanced = st_yled.toggle(_("Enhanced decode (slower)"), value=False)
                uploaded = None

                if input_mode == _("Camera"):
                    uploaded = st.camera_input(_("Scan barcode"))
                else:
                    uploaded = st.file_uploader(_("Upload barcode image"), type=["png", "jpg", "jpeg"])

                st.divider()
                upc_query = st_yled.text_input(_("Enter UPC code"), value=st.session_state.get("last_code", ""))
                if upc_query:
                    normalized = backEnd._normalize_payload(upc_query)
                    if len(normalized) == 10 and normalized[:-1].isdigit() and normalized[-1] in "Xx":
                        code = normalized[:-1] + "X"
                        label = backEnd._classify_code(code, "ISBN10")
                        st_yled.success(f"{label} {_('ready for use')}: {code}")
                    elif normalized.isdigit() and len(normalized) in {8, 12, 13}:
                        label = backEnd._classify_code(normalized, "")
                        st_yled.success(f"{label} {_('ready for use')}: {normalized}")
                    else:
                        st.info(_("Enter a valid UPC (8/12), EAN (8/13), or ISBN (10/13)."))
                    if st_yled.button(_("Search UPC")):
                        with st.spinner(_("Searching UPC...")):
                            try:
                                st.markdown(_("UPC search results:"))
                                cols = st.columns(2)
                                upc_result = backEnd.test_upc_api(upc_query)
                                
                                def add_upc_button(upc_result):
                                    item_id = upc_result.get("ean", upc_query)
                                    proper_id = str(item_id).replace("-", "_")
                                    #add UPC object to Custom collection in firestore
                                    db.collection("Custom").document(proper_id).set(upc_result, merge=True)
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                    st_yled.success(
                                        _("Added '{item}' to your {collection} collection!").format(
                                            item=upc_result.get("name", _("UPC Item")),
                                            collection=backEnd.CURR_COLL.split("_")[0],
                                        )
                                    )

                                with cols[0]:
                                    if upc_result["image"]:
                                        st.image(upc_result["image"], width="content")
                                    else:
                                        st.info(_("No image available for this item."))
                                    with st_yled.badge_card_one(title=upc_result.get('name', _('No title')), text=f"\n**UPC: {upc_result.get('ean', '')}**", badge_text=_("UPC Result"), badge_color="primary",
                                                        background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, height="content", width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", 
                                                        border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                        if upc_result["description"]:
                                            st.write(f"{_('Description')}: {upc_result['description']}")
                                        # if upc_result["publisher"]:
                                        #     st.write(f"{_('Publisher')}: {upc_result['publisher']}")
                                        st.write(f"{_('Item ean')}: {upc_result['ean']}")
                                        if backEnd.CURR_COLL:
                                            st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_upc_{upc_result['ean']}", on_click=add_upc_button, kwargs={"upc_result": upc_result})                           

                            except Exception as e:
                                st_yled.error(f"{_('UPC search failed')}: {e}")
        
            elif search_type == "Pokemon":
                with st_yled.form(key="algolia_search_form", clear_on_submit=False):
                    pokemon_query = st_yled.text_input(_("Search for a Pokemon card"))
                    pokemon_search_submitted = st_yled.form_submit_button(_("Search Pokemon"))

                pokemon_results = st.session_state.get("pokemon_results", [])
                if pokemon_results:
                    st.markdown(_("### Top Pokemon results"))
                    cols = st.columns(3)
                    for idx, item in enumerate(pokemon_results):
                        with cols[idx % 3]:
                            innercols = st.columns([0.5,4,0.5])
                            def add_pokemon_button(item_id, Cardname):
                                proper_id = str(item_id).replace("-", "_")
                                backEnd.add_reference_search(proper_id, item_id, db)
                                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))
                            if item.get("image"):
                                with innercols[1]:
                                    st.image(item["image"], width="stretch")
                            with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                card_shadow=True, badge_text=_("Pokemon Card"), badge_color="primary", text=f"\r\n**ID: {item.get('id', '')}**",
                                                height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", 
                                                border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                st_yled.write(f"**{_('HP')}: {item.get('hp', 'N/A')}**")
                                st_yled.write(f"**{_('Flavortext')}: {item.get('flavorText', 'N/A')}**")
                                if backEnd.CURR_COLL:
                                    st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_item_to_coll, kwargs={"item_id": item['id'], "name": item['name']})
                            st.space("small")

        elif search_type == "Movies":
            with st_yled.form(key="algolia_search_form", clear_on_submit=False):
                movies_query = st_yled.text_input(_("Search for a movie"))
                movies_search_submitted = st_yled.form_submit_button(_("Search Movies"))

            if movies_search_submitted:
                with st.spinner(_("Searching Movies (Algolia)...")):
                        try:
                            algolia_conf = st.secrets.get("algolia", {})
                            app_id = algolia_conf.get("app_id")
                            search_key = algolia_conf.get("search_key")

                            if not (app_id and search_key):
                                raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                        except Exception as e:
                            st.error(f"{_('Algolia search failed')}: {e}")
                            hits = []

                movie_results = st.session_state.get("movies_results", [])
                if movie_results:
                    st.markdown(_("### Top Movie results"))
                    cols = st.columns(3)
                    def add_movie_button(item_id, Moviename):
                                proper_id = str(item_id).replace("-", "_")
                                backEnd.add_reference_search(proper_id, item_id, db)
                                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Moviename, collection=backEnd.CURR_COLL.split('_')[0]))
                    for idx, item in enumerate(movie_results):
                        with cols[idx % 3]:
                            innercols = st.columns([0.5,4,0.5])
                            if item.get("image"):
                                with innercols[1]:
                                    st.image(item["image"], width="stretch")
                            with st_yled.badge_card_one(title=item.get('name', _('No title')), text=f"\n**ID: {item.get('id', '')}**", badge_text=_("Movie"), badge_color="primary",
                                                background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", 
                                                border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                if item.get('overview'):
                                    st_yled.write(f"{_('Description')}: {item['overview']}")
                                if item.get('director'):
                                    st_yled.write(f"{_('Director')}: {item['director']}")
                                if item.get('release_date'):
                                    st_yled.write(f"{_('Release Year')}: {item['release_date'][:4]}")
                                if backEnd.CURR_COLL:
                                    st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_movie_button, kwargs={"item_id": item['id'], "Moviename": item['name']})
                            st.space("small")

    #TODO: Fix the rebrickable items within the db so image tags are correct, then add to algolia
        elif search_type == "LegoSets":
            with st_yled.form(key="lego_search_form", clear_on_submit=False):
                lego_query = st_yled.text_input(_("Search for a Lego set"))
                lego_search_submitted = st_yled.form_submit_button(_("Search Lego"))

            if lego_search_submitted:
                with st.spinner(_("Searching for Lego sets (Algolia)...")):
                    try:
                        results = backEnd.search_algolia(lego_query, index_name="LegoSetSearchResults", max_results=10)
                    except Exception as e:
                        st.error(f"{_('Lego search failed')}: {e}")
                        results = []
                st.session_state["lego_results"] = results

                lego_results = st.session_state.get("lego_results", [])
                if lego_results:
                    st.markdown(_("### Top Lego set results"))
                    cols = st.columns(3)
                    for idx, item in enumerate(lego_results):
                        with cols[idx % 3]:
                            innercols = st.columns([0.5,4,0.5])
                            if item.get("image"):
                                with innercols[1]:
                                    st.image(item["image"], width="stretch")
                            with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"),
                                                card_shadow=True, badge_text=_("Lego Set"), badge_color="primary", text=f"\n**ID: {item.get('id', '')}**",
                                                height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                if item.get('num_parts'):
                                    st.write(f"{_('Part Count')}: {item['num_parts']}")
                                if item.get('year'):
                                    st.write(f"{_('Release Year')}: {item['year']}")
                            st.space("small")

        elif search_type == "LegoMinifigs":
            with st_yled.form(key="lego_minifig_search_form", clear_on_submit=False):
                minifig_query = st_yled.text_input(_("Search for a Lego minifigure"))
                minifig_search_submitted = st_yled.form_submit_button(_("Search Lego Minifigs"))

            if minifig_search_submitted:
                with st.spinner(_("Searching for Lego minifigs (Algolia)...")):
                    try:
                        results = backEnd.search_algolia(minifig_query, index_name="LegoMinifigSearchResults", max_results=10)
                    except Exception as e:
                        st.error(f"{_('Lego minifig search failed')}: {e}")
                        results = []
                st.session_state["lego_minifig_results"] = results

                lego_minifig_results = st.session_state.get("lego_minifig_results", [])
                if lego_minifig_results:
                    st.markdown(_("### Top Lego minifigure results"))
                    cols = st.columns(3)
                    for idx, item in enumerate(lego_minifig_results):
                        with cols[idx % 3]:
                            innercols = st.columns([0.5,4,0.5])
                            if item.get("image"):
                                with innercols[1]:
                                    st.image(item["image"], width="stretch")
                            with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"),
                                                card_shadow=True, badge_text=_("Lego Minifig"), badge_color="primary", text=f"\n**ID: {item.get('id', '')}**",
                                                height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                if item.get('minifig_number'):
                                    st.write(f"{_('Minifig ID')}: {item['minifig_number']}")
                            st.space("small")

        elif search_type == "Dragonball":
            with st_yled.form(key="dbz_search_form", clear_on_submit=False):
                dbz_query = st_yled.text_input(_("Search for a Dragonball Z card"))
                dbz_search_submitted = st_yled.form_submit_button(_("Search DBZ Cards"))

            if dbz_search_submitted:
                with st.spinner(_("Searching Dragonball Z cards (Algolia)...")):
                    try:
                        algolia_conf = st.secrets.get("algolia", {})
                        app_id = algolia_conf.get("app_id")
                        search_key = algolia_conf.get("search_key")

                        if not (app_id and search_key):
                            raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                        hits = backEnd.search_algolia(dbz_query, index_name="DragonballSearchResults", max_results=10)
                    except Exception as e:
                        st.error(f"{_('Algolia search failed')}: {e}")
                        hits = []

                st.session_state["dbz_results"] = hits
                dbz_results = st.session_state.get("dbz_results", [])
                if dbz_results:
                    st.markdown(_("### Top Dragonball Z card results"))
                    cols = st.columns(3)
                    def add_dbz_button(item_id, Cardname):
                                proper_id = str(item_id).replace("-", "_")
                                backEnd.add_reference_search(proper_id, item_id, db)
                                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                    for idx, item in enumerate(dbz_results):
                        with cols[idx % 3]:
                            innercols = st.columns([0.5,4,0.5])
                            if item["image"]:
                                with innercols[1]:
                                    st.image(item["image"], width="stretch")
                            with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                card_shadow=True, badge_text=_("DBZ Card"), badge_color="primary", text=f"\n**{_('ID')}: {item.get('id', '')}**",
                                                height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                st_yled.write(f"**{_('Power')}: {item.get('power', 'N/A')}**")
                                if backEnd.CURR_COLL:
                                    st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_dbz_button, kwargs={"item_id": item['id'], "Cardname": item['name']})
                            st.space("small")

        elif search_type == "Digimon":
            with st_yled.form(key="digimon_search_form", clear_on_submit=False):
                digimon_query = st_yled.text_input(_("Search for a Digimon card"))
                digimon_search_submitted = st_yled.form_submit_button(_("Search Digimon Cards"))

            if digimon_search_submitted:
                with st.spinner(_("Searching Digimon cards (Algolia)...")):
                    try:
                        algolia_conf = st.secrets.get("algolia", {})
                        app_id = algolia_conf.get("app_id")
                        search_key = algolia_conf.get("search_key")

                        if not (app_id and search_key):
                            raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                        hits = backEnd.search_algolia(digimon_query, index_name="DigimonSearchResults", max_results=10)
                    except Exception as e:
                        st.error(f"{_('Algolia search failed')}: {e}")
                        hits = []

                st.session_state["digimon_results"] = hits
                digimon_results = st.session_state.get("digimon_results", [])
                if digimon_results:
                    st.markdown(_("### Top Digimon card results"))
                    cols = st.columns(3)
                    def add_digimon_button(item_id, Cardname):
                                proper_id = str(item_id).replace("-", "_")
                                backEnd.add_reference_search(proper_id, item_id, db)
                                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                    for idx, item in enumerate(digimon_results):
                        with cols[idx % 3]:
                            if item["image"]:
                                innercols = st.columns([0.5,4,0.5])
                                def add_pokemon_button(item_id, Cardname):
                                    proper_id = str(item_id).replace("-", "_")
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))
                                if item.get("image"):
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                    card_shadow=True, badge_text=_("Pokemon Card"), badge_color="primary", text=f"\r\n**ID: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", 
                                                    border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    st_yled.write(f"**{_('HP')}: {item.get('hp', 'N/A')}**")
                                    st_yled.write(f"**{_('Flavortext')}: {item.get('flavorText', 'N/A')}**")
                                    if backEnd.CURR_COLL:
                                        st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_item_to_coll, kwargs={"item_id": item['id'], "name": item['name']})
                                st.space("small")

            elif search_type == "Movies":
                with st_yled.form(key="algolia_search_form", clear_on_submit=False):
                    movies_query = st_yled.text_input(_("Search for a movie"))
                    movies_search_submitted = st_yled.form_submit_button(_("Search Movies"))

                if movies_search_submitted:
                    with st.spinner(_("Searching Movies (Algolia)...")):
                            try:
                                algolia_conf = st.secrets.get("algolia", {})
                                app_id = algolia_conf.get("app_id")
                                search_key = algolia_conf.get("search_key")

                                if not (app_id and search_key):
                                    raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                                hits = backEnd.search_algolia(movies_query, index_name="MovieSearchResults", max_results=10)
                            except Exception as e:
                                st.error(f"{_('Algolia search failed')}: {e}")
                                hits = []

                st.session_state["onepiece_results"] = hits
                onepiece_results = st.session_state.get("onepiece_results", [])
                if onepiece_results:
                    st.markdown(_("### Top One Piece card results"))
                    cols = st.columns(3)
                    def add_onepiece_button(item_id, Cardname):
                                proper_id = str(item_id).replace("-", "_")
                                backEnd.add_reference_search(proper_id, item_id, db)
                                st.audio(gfuncs.DEFAULT_SOUNDS["add"], autoplay=True, width=1, start_time=0)
                                st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                    movie_results = st.session_state.get("movies_results", [])
                    if movie_results:
                        st.markdown(_("### Top Movie results"))
                        cols = st.columns(3)
                        def add_movie_button(item_id, Moviename):
                                    proper_id = str(item_id).replace("-", "_")
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Moviename, collection=backEnd.CURR_COLL.split('_')[0]))
                        for idx, item in enumerate(movie_results):
                            with cols[idx % 3]:
                                innercols = st.columns([0.5,4,0.5])
                                if item.get("image"):
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No title')), text=f"\n**ID: {item.get('id', '')}**", badge_text=_("Movie"), badge_color="primary",
                                                    background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), card_shadow=True, height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", 
                                                    border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    if item.get('overview'):
                                        st_yled.write(f"{_('Description')}: {item['overview']}")
                                    if item.get('director'):
                                        st_yled.write(f"{_('Director')}: {item['director']}")
                                    if item.get('release_date'):
                                        st_yled.write(f"{_('Release Year')}: {item['release_date'][:4]}")
                                    if backEnd.CURR_COLL:
                                        st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_movie_button, kwargs={"item_id": item['id'], "Moviename": item['name']})
                                st.space("small")

        #TODO: Fix the rebrickable items within the db so image tags are correct, then add to algolia
            elif search_type == "LegoSets":
                with st_yled.form(key="lego_search_form", clear_on_submit=False):
                    lego_query = st_yled.text_input(_("Search for a Lego set"))
                    lego_search_submitted = st_yled.form_submit_button(_("Search Lego"))

                if lego_search_submitted:
                    with st.spinner(_("Searching for Lego sets (Algolia)...")):
                        try:
                            results = backEnd.search_algolia(lego_query, index_name="LegoSetSearchResults", max_results=10)
                        except Exception as e:
                            st.error(f"{_('Lego search failed')}: {e}")
                            results = []
                    st.session_state["lego_results"] = results

                    lego_results = st.session_state.get("lego_results", [])
                    if lego_results:
                        st.markdown(_("### Top Lego set results"))
                        cols = st.columns(3)
                        for idx, item in enumerate(lego_results):
                            with cols[idx % 3]:
                                innercols = st.columns([0.5,4,0.5])
                                if item.get("image"):
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"),
                                                    card_shadow=True, badge_text=_("Lego Set"), badge_color="primary", text=f"\n**ID: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    if item.get('num_parts'):
                                        st.write(f"{_('Part Count')}: {item['num_parts']}")
                                    if item.get('year'):
                                        st.write(f"{_('Release Year')}: {item['year']}")
                                st.space("small")

            elif search_type == "LegoMinifigs":
                with st_yled.form(key="lego_minifig_search_form", clear_on_submit=False):
                    minifig_query = st_yled.text_input(_("Search for a Lego minifigure"))
                    minifig_search_submitted = st_yled.form_submit_button(_("Search Lego Minifigs"))

                if minifig_search_submitted:
                    with st.spinner(_("Searching for Lego minifigs (Algolia)...")):
                        try:
                            results = backEnd.search_algolia(minifig_query, index_name="LegoMinifigSearchResults", max_results=10)
                        except Exception as e:
                            st.error(f"{_('Lego minifig search failed')}: {e}")
                            results = []
                    st.session_state["lego_minifig_results"] = results

                    lego_minifig_results = st.session_state.get("lego_minifig_results", [])
                    if lego_minifig_results:
                        st.markdown(_("### Top Lego minifigure results"))
                        cols = st.columns(3)
                        for idx, item in enumerate(lego_minifig_results):
                            with cols[idx % 3]:
                                innercols = st.columns([0.5,4,0.5])
                                if item.get("image"):
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"),
                                                    card_shadow=True, badge_text=_("Lego Minifig"), badge_color="primary", text=f"\n**ID: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    if item.get('minifig_number'):
                                        st.write(f"{_('Minifig ID')}: {item['minifig_number']}")
                                st.space("small")

            elif search_type == "Dragonball":
                with st_yled.form(key="dbz_search_form", clear_on_submit=False):
                    dbz_query = st_yled.text_input(_("Search for a Dragonball Z card"))
                    dbz_search_submitted = st_yled.form_submit_button(_("Search DBZ Cards"))

                if dbz_search_submitted:
                    with st.spinner(_("Searching Dragonball Z cards (Algolia)...")):
                        try:
                            algolia_conf = st.secrets.get("algolia", {})
                            app_id = algolia_conf.get("app_id")
                            search_key = algolia_conf.get("search_key")

                            if not (app_id and search_key):
                                raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                            hits = backEnd.search_algolia(dbz_query, index_name="DragonballSearchResults", max_results=10)
                        except Exception as e:
                            st.error(f"{_('Algolia search failed')}: {e}")
                            hits = []

                    st.session_state["dbz_results"] = hits
                    dbz_results = st.session_state.get("dbz_results", [])
                    if dbz_results:
                        st.markdown(_("### Top Dragonball Z card results"))
                        cols = st.columns(3)
                        def add_dbz_button(item_id, Cardname):
                                    proper_id = str(item_id).replace("-", "_")
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                        for idx, item in enumerate(dbz_results):
                            with cols[idx % 3]:
                                innercols = st.columns([0.5,4,0.5])
                                if item["image"]:
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                    card_shadow=True, badge_text=_("DBZ Card"), badge_color="primary", text=f"\n**{_('ID')}: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    st_yled.write(f"**{_('Power')}: {item.get('power', 'N/A')}**")
                                    if backEnd.CURR_COLL:
                                        st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_dbz_button, kwargs={"item_id": item['id'], "Cardname": item['name']})
                                st.space("small")

            elif search_type == "Digimon":
                with st_yled.form(key="digimon_search_form", clear_on_submit=False):
                    digimon_query = st_yled.text_input(_("Search for a Digimon card"))
                    digimon_search_submitted = st_yled.form_submit_button(_("Search Digimon Cards"))

                if digimon_search_submitted:
                    with st.spinner(_("Searching Digimon cards (Algolia)...")):
                        try:
                            algolia_conf = st.secrets.get("algolia", {})
                            app_id = algolia_conf.get("app_id")
                            search_key = algolia_conf.get("search_key")

                            if not (app_id and search_key):
                                raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                            hits = backEnd.search_algolia(digimon_query, index_name="DigimonSearchResults", max_results=10)
                        except Exception as e:
                            st.error(f"{_('Algolia search failed')}: {e}")
                            hits = []

                    st.session_state["digimon_results"] = hits
                    digimon_results = st.session_state.get("digimon_results", [])
                    if digimon_results:
                        st.markdown(_("### Top Digimon card results"))
                        cols = st.columns(3)
                        def add_digimon_button(item_id, Cardname):
                                    proper_id = str(item_id).replace("-", "_")
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                        for idx, item in enumerate(digimon_results):
                            with cols[idx % 3]:
                                if item["image"]:
                                    innercols = st.columns([0.5,4,0.5])
                                    with innercols[1]:
                                        st.image(item["image"], width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                    card_shadow=True, badge_text=_("Digimon Card"), badge_color="primary", text=f"\n**{_('ID')}: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    st_yled.write(f"**{_('Card Type')}: {item.get('cardType', 'N/A')}**")
                                    if backEnd.CURR_COLL:
                                        st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_digimon_button, kwargs={"item_id": item['id'], "Cardname": item['name']})
                                st.space("small")

            elif search_type == "OnePiece":
                with st_yled.form(key="onepiece_search_form", clear_on_submit=False):
                    onepiece_query = st_yled.text_input(_("Search for a One Piece card"))
                    onepiece_search_submitted = st_yled.form_submit_button(_("Search One Piece Cards"))

                if onepiece_search_submitted:
                    with st.spinner(_("Searching One Piece cards (Algolia)...")):
                        try:
                            algolia_conf = st.secrets.get("algolia", {})
                            app_id = algolia_conf.get("app_id")
                            search_key = algolia_conf.get("search_key")

                            if not (app_id and search_key):
                                raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                            hits = backEnd.search_algolia(onepiece_query, index_name="OnepieceSearchResults", max_results=10)
                        except Exception as e:
                            st.error(f"{_('Algolia search failed')}: {e}")
                            hits = []

                    st.session_state["onepiece_results"] = hits
                    onepiece_results = st.session_state.get("onepiece_results", [])
                    if onepiece_results:
                        st.markdown(_("### Top One Piece card results"))
                        cols = st.columns(3)
                        def add_onepiece_button(item_id, Cardname):
                                    proper_id = str(item_id).replace("-", "_")
                                    backEnd.add_reference_search(proper_id, item_id, db)
                                    st_yled.success(_("Added '{item}' to your {collection} collection!").format(item=Cardname, collection=backEnd.CURR_COLL.split('_')[0]))

                        for idx, item in enumerate(onepiece_results):
                            with cols[idx % 3]:
                                if item["image"]:
                                    innercols = st.columns([0.5,4,0.5])
                                    with innercols[1]:
                                        st.image(gfuncs.get_image_from_URL(item["image"]), width="stretch")
                                with st_yled.badge_card_one(title=item.get('name', _('No name')), background_color=gfuncs.read_config_val(gfuncs.conf_file, "backgroundColor"), 
                                                    card_shadow=True, badge_text=_("One Piece Card"), badge_color="primary", text=f"\n**ID: {item.get('id', '')}**",
                                                    height=300, width=400, text_font_size=17, title_font_size=30, title_font_weight="bold", border_style="solid", border_color=gfuncs.read_config_val(gfuncs.conf_file, "textColor"), border_width=1):
                                    st_yled.write(f"**{_('Type')}: {item.get('type', 'N/A')}**")
                                    st_yled.write(f"**{_('Rarity')}: {item.get('rarity', 'N/A')}**")
                                    if backEnd.CURR_COLL:
                                        st_yled.button(_("Add to {collection} Collection").format(collection=backEnd.CURR_COLL.split('_')[0]), key=f"add_{item['id']}", on_click=add_onepiece_button, kwargs={"item_id": item['id'], "Cardname": item['name']})
                                st.space("small")

            else:
                st.info(_("Search functionality for this category is coming soon!"), width=1000)