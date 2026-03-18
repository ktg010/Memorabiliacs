import streamlit as st
from google.cloud import firestore
import BackendMethods.global_functions as gfuncs
import BackendMethods.auth_functions as authFuncs
import BackendMethods.backendfuncs as backEnd

st.session_state["last_code"] = ""

# user sign-in check
if 'user_info' not in st.session_state:
    st.switch_page("pages/login.py")

try:
    db = firestore.Client.from_service_account_info(st.secrets["firebase"])
    user_id = st.session_state.user_info["localId"]
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()    

## -------------------------------------------------------------------------------------------------
## Logged in ---------------------------------------------------------------------------------------
## -------------------------------------------------------------------------------------------------
else:
    gfuncs.page_initialization()
# This is straight from kieran's ui in apitesting, placeholder
    st.subheader("Search for Collectables!", text_alignment="center")
    # DEGUB:{st.session_state.user_info}
    st.space("large")
    col_left, col_right = st.columns([3, 2])

    # Search type selector (left column)
    search_type = col_left.selectbox(
        "What would you like to search for?",
        options=("Vinyl & CDs", "Movies", "Pokemon Cards", "UPC", "Lego Sets", "Lego Minifigs"),
    )

    # Collection selector (right column) - list user's collections except DefaultCollection
    try:
        collections_docs = list(db.collection('Users').document(user_id).collection('Collections').stream())
        collections = [doc.id for doc in collections_docs if not doc.id.startswith("DefaultCollection")]
        display_collections = [name.split("_")[0] for name in collections]
    except Exception:
        collections = []

    if not collections:
        collections = ["(No collections)"]

    # Persist selection in session state
    default_index = 0
    if hasattr(backEnd, 'CURR_COLL') and backEnd.CURR_COLL:
        try:
            default_index = collections.index(backEnd.CURR_COLL)
        except Exception:
            default_index = 0

    selected_collection = col_right.selectbox("Add items to collection:", options=display_collections, index=default_index, key="selected_collection")

    # Set backend current collection for add actions
    if selected_collection and selected_collection != "(No collections)":
        try:
            backEnd.setCollection(collections[display_collections.index(selected_collection)])
        except Exception:
            backEnd.CURR_COLL = collections[display_collections.index(selected_collection)]
    else:
        try:
            backEnd.setCollection("")
        except Exception:
            backEnd.CURR_COLL = ""

    if search_type == "UPC":
        input_mode = st.radio("Input source", options=["Upload", "Camera"], horizontal=True)
        enhanced = st.toggle("Enhanced decode (slower)", value=False)
        uploaded = None

        if input_mode == "Camera":
            uploaded = st.camera_input("Scan barcode")
        else:
            uploaded = st.file_uploader("Upload barcode image", type=["png", "jpg", "jpeg"])

        if not backEnd.PYZBAR_AVAILABLE:
            st.error("Barcode decoding is unavailable. Install 'pyzbar' and the system 'zbar' library.")
            st.stop()

        decoded: list[dict[str, str]] = []
        if uploaded is not None:
            try:
                image = backEnd._load_image(uploaded)
                decoded = backEnd._decode_barcodes(image)
                if enhanced and not decoded:
                    decoded = backEnd._decode_with_enhancements(image)
            except Exception as exc:
                st.error(f"Failed to read image: {exc}")

        if decoded:
            supported_codes = backEnd._extract_supported_codes(decoded)
            if supported_codes:
                st.success("Supported code(s) detected")
                options = [f"{item['code']} ({item['label']})" for item in supported_codes]
                selected = st.selectbox("Detected codes", options=options)
                st.session_state["last_code"] = selected.split(" ")[0]
            else:
                st.warning("Barcode detected, but no UPC/EAN/ISBN code found.")
        elif uploaded is not None:
            st.warning("No barcode detected. Try a clearer image with the code centered.")

        st.divider()
        upc_query = st.text_input("Enter UPC code", value=st.session_state.get("last_code", ""))
        if upc_query:
            normalized = backEnd._normalize_payload(upc_query)
            if len(normalized) == 10 and normalized[:-1].isdigit() and normalized[-1] in "Xx":
                code = normalized[:-1] + "X"
                label = backEnd._classify_code(code, "ISBN10")
                st.success(f"{label} ready for use: {code}")
            elif normalized.isdigit() and len(normalized) in {8, 12, 13}:
                label = backEnd._classify_code(normalized, "")
                st.success(f"{label} ready for use: {normalized}")
            else:
                st.info("Enter a valid UPC (8/12), EAN (8/13), or ISBN (10/13).")
            if st.button("Search UPC"):
                with st.spinner("Searching UPC..."):
                    try:
                        st.markdown("UPC search results:")
                        cols = st.columns(2)
                        upc_result = backEnd.test_upc_api(upc_query)
                        # for idx, result in enumerate(upc_result):
                        with cols[0]:
                            if upc_result["image"]:
                                st.image(upc_result["image"], width=200)
                            st.write(f"**{upc_result.get('title', 'No title')}**")
                            if upc_result["description"]:
                                st.write(f"Description: {upc_result['description']}")
                            if upc_result["publisher"]:
                                st.write(f"Publisher: {upc_result['publisher']}")
                            st.write(f"Item ean: {upc_result['ean']}")

                    except Exception as e:
                        st.error(f"UPC search failed: {e}")
    elif search_type == "Pokemon Cards":
        with st.form(key="algolia_search_form", clear_on_submit=False):
            pokemon_query = st.text_input("Search for a Pokemon card")
            pokemon_search_submitted = st.form_submit_button("Search Pokemon")

        if pokemon_search_submitted:
            with st.spinner("Searching Pokemon (Algolia)..."):
                try:
                    algolia_conf = st.secrets.get("algolia", {})
                    app_id = algolia_conf.get("app_id")
                    search_key = algolia_conf.get("search_key")

                    if not (app_id and search_key):
                        raise ValueError("Algolia credentials (app_id, search_key, index_name) missing in Streamlit secrets")

                    hits = backEnd.search_algolia(pokemon_query, index_name="PokemonSearchResults", max_results=10)
                except Exception as e:
                    st.error(f"Algolia search failed: {e}")
                    hits = []

            st.session_state["pokemon_results"] = hits


            pokemon_results = st.session_state.get("pokemon_results", [])
            if pokemon_results:
                st.markdown("### Top Pokemon results")
                cols = st.columns(2)
                for idx, item in enumerate(pokemon_results):
                    with cols[idx % 2]:
                        
                        def add_pokemon_button(item_id, Cardname):
                            proper_id = str(item_id).replace("-", "_")
                            backEnd.add_reference_search(db, user_id, proper_id, item_id)
                            st.success(f"Added '{Cardname}' to your {backEnd.CURR_COLL.split('_')[0]} collection!")
                        print(f"pokemon restults = {pokemon_results}")
                        if item.get("images"):
                            st.image(item["images"]['small'], width=200)
                        name = item.get('name', item.get('title', 'No name'))
                        st.write(f"**{name}**")
                        if item.get('set'):
                            st.write(item['set'])
                        if item.get('HP'):
                            st.write(f"HP: {item['HP']}")
                        if item.get('flavorText'):
                            st.write(f"*{item['flavorText']}*")
                        item_id = item["id"]
                        item_name = item['name'] if 'name' in item else item['title'] if 'title' in item else "No name"
                        st.button(f"Add to {backEnd.CURR_COLL.split('_')[0]} Collection", key=f"add_{item_id}", on_click=add_pokemon_button, kwargs={"item_id": item_id, "Cardname": item_name})



    elif search_type == "Lego Sets":
        with st.form(key="lego_search_form", clear_on_submit=False):
            lego_query = st.text_input("Search for a Lego set")
            lego_search_submitted = st.form_submit_button("Search Lego")

        if lego_search_submitted:
            with st.spinner("Searching for Lego sets..."):
                try:
                    results = backEnd.search_sets_rebrickable(lego_query, max_results=10)
                except Exception as e:
                    st.error(f"Lego search failed: {e}")
                    results = []
            st.session_state["lego_results"] = results

            lego_results = st.session_state.get("lego_results", [])
            if lego_results:
                st.markdown("### Top Lego set results")
                cols = st.columns(2)
                for idx, item in enumerate(lego_results):
                    with cols[idx % 2]:
                        if item.get("image_url"):
                            st.image(item["image_url"], width=200)
                        st.write(f"{item.get('name', 'No name')}")
                        if item.get('year'):
                            st.write(f"Year: {item['year']}")
                        if item.get('theme'):
                            st.write(f"Theme: {item['theme']}")
                        if item.get('set_id'):
                            st.write(f"Set ID: {item['set_id']}")
                        if item.get('num_parts'):
                            st.write(f"Part Count: {item['num_parts']}")
                            
    elif search_type == "Lego Minifigs":
        with st.form(key="lego_minifig_search_form", clear_on_submit=False):
            minifig_query = st.text_input("Search for a Lego minifigure")
            minifig_search_submitted = st.form_submit_button("Search Lego Minifigs")

        if minifig_search_submitted:
            with st.spinner("Searching for Lego minifigs..."):
                try:
                    results = backEnd.search_minifigs_rebrickable(minifig_query, max_results=10)
                except Exception as e:
                    st.error(f"Lego minifig search failed: {e}")
                    results = []
            st.session_state["lego_minifig_results"] = results

            lego_minifig_results = st.session_state.get("lego_minifig_results", [])
            if lego_minifig_results:
                st.markdown("### Top Lego minifigure results")
                cols = st.columns(2)
                for idx, item in enumerate(lego_minifig_results):
                    with cols[idx % 2]:
                        if item.get("image_url"):
                            st.image(item["image_url"], width=200)
                        st.write(f"{item.get('name', 'No name')}")
                        if item.get('minifig_id'):
                            st.write(f"Minifig ID: {item['minifig_id']}")

                            

                            
    else:
        st.info("Search functionality for this category is coming soon!")