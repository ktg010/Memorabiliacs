import internetarchive
import streamlit as st
import tmdbsimple as tmdb
import rebrick
import json
from fastapi import FastAPI, Query, Path
from requests_futures.sessions import FuturesSession
import requests
from concurrent.futures import as_completed
from BackendMethods.auth_functions import create_account, sign_in, reset_password
from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.models.search_params_object import SearchParamsObject
from google.cloud import firestore
import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyzbar import pyzbar
import json
from pathlib import Path as FilePath

BASE_API_URL = "https://apitcg.com/api"
APITCG_API_KEY = st.secrets["APITCG_API_KEY"]
REBRICK_API_KEY = st.secrets["REBRICK_API_KEY"]
tmdb.API_KEY = st.secrets["TMDB_API_KEY"]
tmdb.REQUESTS_TIMEOUT = (2, 5)  # seconds, for connect and read specifically 
CURR_COLL = ""

app = FastAPI()

@st.cache_resource
def get_firestore_client():
    """Cached Firestore client to avoid repeated authentication."""
    return firestore.Client.from_service_account_info(st.secrets["firebase"])

@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_user_data(user_id: str):
    """Fetch user data from Firestore, cached to reduce DB calls."""
    db = get_firestore_client()
    return db.collection("Users").document(user_id).get().to_dict()

@st.cache_resource
def get_user_collections(user_id: str):
    """Fetch user's collections, cached to reduce DB calls."""
    db = get_firestore_client()
    return [{"id": doc.id,**doc.to_dict()} for doc in db.collection('Users').document(user_id).collection('Collections').stream()]

@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_collection_types():
    """Fetch collection types, cached globally."""
    db = get_firestore_client()
    res = []
    types = db.collections()
    for doc in types:
        if doc.id != "Users":
            if doc.id == "Custom":
                res.insert(0, doc.id)
            else:
                res.append(doc.id)
    return res

@st.cache_data(ttl=3600)
def type_fields(coll_type: str):
    """Get fields for a collection type, cached per type."""
    db = get_firestore_client()
    res = {}
    typeRef = db.collection(coll_type)
    index = 0
    for doc in typeRef.stream():
        fields = doc.to_dict()
        index += 1
        for key in fields.keys():
            res[key] = True
        if index >= 2:
            return res
    return res

def set_collection(collection:str):
    """Sets the collection name for reference across pages
    
    collection: full name_type of the collection (doc.id)
    """
    global CURR_COLL
    CURR_COLL = collection


def coll_visability(collection_name: str, db):
    """Checks if the collection is visable for main page
    
    coll_name: full id name of collection
    db: Firestore database
    Returns bool of visabliy
    """
    user_id = st.session_state.user_info['localId']
    collection_ref = db.collection('Users').document(user_id).collection('Collections').document(collection_name)
    contents = collection_ref.get().to_dict()
    return not contents["settings"]["hidden"]


CURR_THEME = ".streamlit/st-styled.css"

# Faster version of get_cards using asynchronous gets and future responses
@app.get("/{game}/cards")
def get_cards2(
    game: str = Path(..., description="Game type: one-piece, pokemon, yugioh, etc."),
    id: list[str] = Query(..., description="Card name(s) to search")
):
    url = f"{BASE_API_URL}/{game}/cards"

    headers = {
        "x-api-key": APITCG_API_KEY
    }


    futureList = []

    responseList = []
    session = FuturesSession()
    # first request is started in background
    for i in range(len(id)-1):
        params = {
        "id": id[i]}
        futureList.append(session.get(url, headers=headers, params=params))
    for future in as_completed(futureList):
        #create the dictionary with the id, name, type, hp, and image url
        try:
            card_hp = future.result().json()["data"][0]["hp"]
        except (KeyError, TypeError):
            card_hp = 0
        try:
            card_text = future.result().json()["data"][0]["flavorText"]
        except (KeyError, TypeError):
            card_text = ""
        card_name = future.result().json()["data"][0]["name"]
        card_id = future.result().json()["data"][0]["id"]
        image_url = future.result().json()["data"][0]["images"]["small"]
        responseList.append({
            "id": card_id,
            "flavorText": card_text,
            "hp": card_hp,
            "name": card_name,
            "image": image_url
        })

    return(responseList)


def search_movies(query, max_results=10):
    search = tmdb.Search()
    response = search.movie(query=query)
    results = []
    for movie in response['results'][:max_results]:
        results.append({
            'title': movie.get('title'),
            'release_date': movie.get('release_date'),
            'overview': movie.get('overview'),
            'image': f"https://image.tmdb.org/t/p/w500{movie['poster_path']}" if movie.get('poster_path') else None,
            'id': movie.get('id')
        })
    return results


def search_internetarchive(creators: str = "", title: str = "", max_results: int = 10):
    """Search Internet Archive for audio items filtered to Vinyl or CD formats.

    creators: comma-separated list of creators to search (OR'd together)
    title: title or comma-separated titles to search (OR'd together)
    max_results: maximum number of results to return (default 10)
    Returns a list of dicts with keys: identifier, title, creator, thumbnail, format
    """
    query_parts = []
    if creators:
        parts = []
        for c in creators.split(","):
            s = c.strip()
            if s:
                parts.append(f'"{s}"')
        creators_escaped = " OR ".join(parts)
        query_parts.append(f'creator:({creators_escaped})')
    if title:
        parts = []
        for t in title.split(","):
            s = t.strip()
            if s:
                parts.append(f'"{s}"')
        title_escaped = " OR ".join(parts)
        query_parts.append(f'title:({title_escaped})')

    # Always limit to audio mediatype
    query_parts.append('mediatype:(audio)')

    query = " AND ".join(query_parts)

    search_results = internetarchive.search_items(
        query,
        fields=['identifier', 'title', 'creator', 'format'],
    )

    results = []
    for result in search_results:
        identifier = result.get('identifier')
        name = result.get('title', '')
        creator = result.get('creator', '')
        fmt = result.get('format', '')
        thumb_url = f"https://archive.org/download/{identifier}/__ia_thumb.jpg" if identifier else None
        results.append({
            'id': identifier,
            'title': name,
            'creator': creator,
            'image': thumb_url,
            'format': fmt,
        })

    return results


def generate_collection(collection_name: str, db):
    """Generate a collection of items from the database based on the collection name.

    collection_name: Name of the collection to retrieve
    db: Firestore database instance
    Returns a list of items (data dictionaries) referenced in the specified collection
    """
    user_id = st.session_state.user_info['localId']
    collection_ref = db.collection('Users').document(user_id).collection('Collections').document(collection_name)
    collection_doc = collection_ref.get()
    if collection_doc.exists:
        items_refs = collection_doc.to_dict()
        return items_refs["items"]
    else:
        return []
    

@st.cache_data(ttl=3600)
def get_collection_items(collection_name: str):
    """Fetch and process all items in a collection - cached to avoid repeated DB reads"""
    db = get_firestore_client()  # Use cached client
    collectionData = generate_collection(collection_name, db)
    items = {}
    for id in collectionData:
        items[id] = {'info' : (collectionData[id].get('ref')).get().to_dict(), 'notes' : collectionData[id].get('notes')}
    return items


def update_notes(db, user_id, item_id, new_notes):
    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).update({f"items.{item_id}.notes": new_notes})

def create_collection(collection_name: str, collection_type: str, db):
    """Create a collection of items in the database with the specified name and type.

    collection_name: Name of the collection to create
    collection_type: Type of the collection (e.g., "Pokemon", "Movies", etc.)
    db: Firestore database instance
    Returns true if collection already exits, else sets collection
    """
    user_id = st.session_state.user_info['localId']

    # generates db collection name
    fullName = collection_name.title() + f"_{collection_type}"

    # check if name already exists in the database
    if check_for_coll_name(collection_name.title(), db):
        return True
    
    # created new collection
    baseInfo = {
        # list of items per collection
        "items": {},

        # collection settings
        "settings": {
            # sets what fields are viewed via item type
            "views" : type_fields(collection_type),
            # sets preview image 
            "image" : "url to display image",
            # sets a background image when viewing collection
            "background" : "url to background image",
            # ? way to re-order collections on main page ?
            "order" : "figure out later, way to sort/filter/order on main page",
            # hidden on main page
            "hidden" : False
        }
    }
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(baseInfo)
    get_user_collections.clear(user_id)


def rename_collection(collection_name:str, new_collection:str, db):
    """Renames a collection, by use of creating a new collection and moving the data
    
    collection_name: name of original collection
    new_collection: new name for collection
    db: database
    """
    user_id = st.session_state.user_info['localId']
    
    # gets reference and type of collection
    collection_ref_OLD = db.collection('Users').document(user_id).collection('Collections').document(collection_name)
    coll_Info = collection_ref_OLD.get().id.split("_")

    # checks if new name already exists in the database
    if check_for_coll_name(new_collection.title(), db):
        return True

    # created new collection to move data to
    fullName = f"{new_collection.title()}_{coll_Info[1]}"
    
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(collection_ref_OLD.get().to_dict())
    collection_ref_OLD.delete()
    get_user_collections.clear(user_id)


def add_reference_collectionView(item_doc_id, actual_id, db):
    """Adds an Item to a user's collection

    item_doc_id: the fixed name (removed '-') of the item
    actual_id: the document reference name of the item
    db: Firebase database
    """
    user_id = st.session_state.user_info['localId']
    coll_type = CURR_COLL.split("_")[1]
    item_ref = db.collection(coll_type).document(actual_id)

    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).update({
    f"items.{item_doc_id}": {
        "notes": "Your notes here",
        "ref": item_ref   
        }
    })
    get_collection_items.clear(CURR_COLL)
    st.rerun()
    

def add_reference_search(item_doc_id, actual_id, db):
    """Adds an Item to a users collection, does not rerun

    item_doc_id: the fixed name (removed '-') of the item
    actual_id: the document reference name of the item
    db: Firebase database
    """
    user_id = st.session_state.user_info['localId']
    coll_type = CURR_COLL.split("_")[1]
    item_ref = db.collection(coll_type).document(actual_id)

    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).update({
    f"items.{item_doc_id}": {
        "notes": "Your notes here",
        "ref": item_ref   
        }
    })
    get_collection_items.clear(CURR_COLL)


def delete_reference(item_doc_id, db):
    """Deleted an item from the user's collection

    item_doc_id: the fixed name (removed '-') of the item, version stored in user's collection
    db: Firebase database
    """
    user_id = st.session_state.user_info['localId']
    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).update({
          f"items.{item_doc_id}": firestore.DELETE_FIELD
    })
    get_collection_items.clear(CURR_COLL)
    st.rerun()


def check_for_coll_name(collection_name:str, db) -> bool:
    """Checks if the provided name is in the database
    
    collection_name: name checking for
    db: database
    """
    user_id = st.session_state.user_info['localId']

    collections = list(db.collection("Users").document(user_id).collections())

    for coll in collections:
        for doc in list(coll.stream()):
            collName = doc.id.split("_")
            if collName[0] == collection_name:
                return True
    return False

def setTheme(theme:str):
    global CURR_THEME
    CURR_THEME = theme

REBRICK_API_KEY = st.secrets["REBRICK_API_KEY"]

def collection_views(collection_name:str, db):
    """Gets the collection type views

    collection_name: name of the collection
    db: Firebase database
    Returns list map(dict) of views
    """
    user_id = st.session_state.user_info['localId']

    collection_ref = db.collection("Users").document(user_id).collection("Collections").document(collection_name)

    return collection_ref.get().to_dict()["settings"]["views"]


def update_collection_views(collection_name:str, views, db):
    """Updates the type views for the collection

    collection_name: name of collection
    views: dictonary of fields and booleans per item type
    db: Firebase database 
    """
    user_id = st.session_state.user_info['localId']

    collection_ref = db.collection("Users").document(user_id).collection("Collections").document(collection_name)
    collection_ref.update({"settings.views": views})


def search_minifigs_rebrickable(query, max_results: int = 10):
    """Search Rebrickable for minifigs matching `query` (query can be part of any attribute present in the json, such as name or minifig_id).

    Returns a list of dicts with keys: name, minifig_id,  image_url

    """
    rebrick.init(REBRICK_API_KEY)
    try:
        resp = rebrick.lego.get_minifigs(query)
        data = json.loads(resp.read())
    except Exception:
        return []

    items = []
    if isinstance(data, dict):
        items = data.get('results')
  

    results = []
    for item in items[:max_results]:
        results.append({
            'name': item.get('name'),
            'minifig_id': item.get('set_num'),
            'image_url': item.get('set_img_url'),
        })

    return results


def search_sets_rebrickable(query, max_results: int = 10):
    """Search Rebrickable for sets matching `query`.

    Returns a list of dicts with keys: name, set_id, image_url, num_parts, year
    """
    rebrick.init(REBRICK_API_KEY)
    try:
        resp = rebrick.lego.get_sets(query)
        data = json.loads(resp.read())
    except Exception:
        return []

    items = []
    
    if isinstance(data, dict):
        items = data.get('results') 

    results = []
    for item in items[:max_results]:
        results.append({
            'name': item.get('name'),
            'set_id': item.get('set_num'),
            'image_url': item.get('set_img_url'),
            'num_parts': item.get('num_parts'),
            'year': item.get('year'),
        })

    return results


def search_algolia(query: str, index_name: str, max_results: int = 10):
    """Search an Algolia index for items matching `query`.
    
    query(str): the search query
    index_name(str): the Algolia index name to search
    max_results(int): maximum number of results to return (default 10)
    
    Returns a list of dicts with filtered attributes. For "PokemonSearchResults" index,
    returns: id, name, image, flavorText, and HP
    """
    try:
        algolia_conf = st.secrets.get("algolia", {})
        app_id = algolia_conf.get("app_id")
        search_key = algolia_conf.get("search_key")
        
        if not (app_id and search_key):
            raise ValueError("Algolia credentials (app_id, search_key) missing in Streamlit secrets")
        
        
        client = SearchClientSync(app_id, search_key)
        response = client.search_single_index(
                        index_name=index_name,
                        search_params=SearchParamsObject(
                        query=query,
                        hits_per_page=max_results
                        )
                    )
        hits = response.hits
        
        # Check if this is the PokemonSearchResults index
        if index_name == "PokemonSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', getattr(hit, 'object_id', None)),
                    "name": getattr(hit, 'name', None),
                    "images": getattr(hit, 'images', None),
                    "flavorText": getattr(hit, 'flavorText', None),
                    "hp": getattr(hit, 'hp', getattr(hit, 'hp', None))
                })
            return results
        
        elif index_name == "MovieSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'name', None),
                    "release_date": getattr(hit, 'release_date', None),
                    "overview": getattr(hit, 'overview', None),
                    "image": getattr(hit, 'image', None)
                })
            return results
        
        elif index_name == "DragonballSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'name', None),
                    "power": getattr(hit, 'power', None),
                    "image": getattr(hit, 'image', None)
                })
            return results
        
        elif index_name == "DigimonSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'name', None),
                    "cardType": getattr(hit, 'cardType', None),
                    "image": getattr(hit, 'image', None)
                })
            return results
        
        elif index_name == "OnepieceSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'name', None),
                    "type": getattr(hit, 'type', None),
                    "image": getattr(hit, 'image', None),
                    "rarity": getattr(hit, 'rarity', None)
                })
            return results


        else:
            return hits
            
    except Exception as e:
        st.error(f"Algolia search failed: {e}")
        return []


def test_upc_api(upc_code: str):
    headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Accept-Encoding': 'gzip,deflate'
    }
    resp = requests.get(f'https://api.upcitemdb.com/prod/trial/lookup?upc={upc_code}', headers=headers)
    data = json.loads(resp.text)
    if 'items' in data and len(data['items']) > 0:
        item = data['items'][0]
        results = {
            'name': item['title'],
            'description': item['description'],
            'publisher': item.get('publisher', None) if item['publisher'] else None,
            'ean': item['ean'],
            'image': item['images'][0]  # Get the first image if available
        }
    else:
        raise ValueError("No items found for the provided UPC code.")
    return results


def _decode_barcodes(image: Image.Image) -> list[dict[str, str]]:


	decoded = pyzbar.decode(image)
	results: list[dict[str, str]] = []
	for barcode in decoded:
		data = barcode.data.decode("utf-8", errors="ignore").strip()
		if data:
			results.append({"type": barcode.type, "data": data})
	return results


def _enhance_variants(image: Image.Image) -> list[Image.Image]:
	variants: list[Image.Image] = []

	gray = ImageOps.grayscale(image)
	variants.append(gray)
	variants.append(ImageOps.autocontrast(gray))
	variants.append(ImageOps.autocontrast(gray, cutoff=2))

	contrast = ImageEnhance.Contrast(gray).enhance(2.0)
	variants.append(contrast)

	sharp = contrast.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=3))
	variants.append(sharp)
	variants.append(sharp.filter(ImageFilter.SHARPEN))

	for scale in (0.75, 1.25, 1.5, 2.0):
		w, h = gray.size
		scaled = gray.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
		variants.append(scaled)

	rotated: list[Image.Image] = []
	for img in variants:
		rotated.append(img)
		rotated.append(img.rotate(90, expand=True))
		rotated.append(img.rotate(180, expand=True))
		rotated.append(img.rotate(270, expand=True))

	return rotated


def _decode_with_enhancements(image: Image.Image) -> list[dict[str, str]]:
	for variant in _enhance_variants(image):
		decoded = _decode_barcodes(variant)
		if decoded:
			return decoded
	return []


def _normalize_payload(payload: str) -> str:
	return payload.replace("-", "").replace(" ", "").strip()


def _classify_code(code: str, barcode_type: str) -> str:
	barcode_type = (barcode_type or "").upper()
	known = {
		"UPCA": "UPC-A",
		"UPCE": "UPC-E",
		"EAN13": "EAN-13",
		"EAN8": "EAN-8",
		"ISBN10": "ISBN-10",
		"ISBN13": "ISBN-13",
	}
	if barcode_type in known:
		return known[barcode_type]

	if len(code) == 8:
		return "UPC-E / EAN-8"
	if len(code) == 10:
		return "ISBN-10"
	if len(code) == 12:
		return "UPC-A"
	if len(code) == 13:
		return "ISBN-13" if code.startswith(("978", "979")) else "EAN-13"
	return "Unknown"


def _extract_supported_codes(decoded: list[dict[str, str]]) -> list[dict[str, str]]:
	seen: set[str] = set()
	matches: list[dict[str, str]] = []
	for item in decoded:
		raw = _normalize_payload(item["data"])
		if not raw:
			continue

		code = raw
		if len(raw) == 10 and raw[:-1].isdigit() and raw[-1] in "Xx":
			code = raw[:-1] + "X"
		elif not raw.isdigit():
			continue

		if len(code) not in {8, 10, 12, 13}:
			continue
		if code in seen:
			continue

		seen.add(code)
		matches.append({
			"code": code,
			"label": _classify_code(code, item.get("type", "")),
		})
	return matches


def _load_image(uploaded_file: st.runtime.uploaded_file_manager.UploadedFile) -> Image.Image:
	data = uploaded_file.getvalue()
	return Image.open(io.BytesIO(data)).convert("RGB")


# Function to upload all pokemon cards to database
# I have this placed into the homepage 'add_collection' button for the sole purpose of running the code
# In order to use this for other items, create a template (you can use professor gpt), download
# # the files from the github or wherever the information is and specify it, and run the code.
# def upload_pokemon_data(db):
#     # Specify the location of the data to upload
#     data_dir = Path(r"C:\Users\andre\Desktop\Memorabiliacs\BackendMethods\Pokemon_Cards")

#     # Create a template so that all cards contain all fields and fill the blanks with N/A
#     CARD_TEMPLATE = {
#         "name": "N/A",
#         "supertype": "N/A",
#         "subtypes": "N/A",
#         "level": "N/A",
#         "hp": "N/A",
#         "types": "N/A",
#         "evolvesFrom": "N/A",
#         "abilities": "N/A",
#         "attacks": "N/A",
#         "weaknesses": "N/A",
#         "retreatCost": "N/A",
#         "convertedRetreatCost": "N/A",
#         "number": "N/A",
#         "artist": "N/A",
#         "rarity": "N/A",
#         "flavorText": "N/A",
#         "nationalPokedexNumbers": "N/A",
#         "legalities": "N/A",
#         "images": "N/A"
#     }

#     # Runs through the json file of data to analyze all cards ad fill out the template
#     for json_file in data_dir.rglob("*.json"):
#         print(f"Reading {json_file.name}")

#         with open(json_file, "r", encoding="utf-8") as f:
#             cards = json.load(f)

#         for card in cards:

#             card_id = card.get("id")
#             if not card_id:
#                 continue

#             # Fill missing fields
#             card_map = {k: card.get(k, "N/A") for k in CARD_TEMPLATE}

#             doc_ref = db.collection("Pokemon").document(card_id)

#             doc_ref.set(card_map)
