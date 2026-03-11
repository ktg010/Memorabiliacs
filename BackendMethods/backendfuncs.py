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

BASE_API_URL = "https://apitcg.com/api"
APITCG_API_KEY = st.secrets["APITCG_API_KEY"]

app = FastAPI()

CURR_COLL = ""

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

tmdb.API_KEY = st.secrets["TMDB_API_KEY"]
tmdb.REQUESTS_TIMEOUT = (2, 5)  # seconds, for connect and read specifically 

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

# make a method to generate a specific collection (list of dictionaries) based on
# the input that will be the name of the collection. 
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
        return items_refs
    else:
        return []

# created new document in db
def create_collection(collection_name: str, collection_type: str, db):
    """Create a collection of items in the database with the specified name and type.

    collection_name: Name of the collection to create
    collection_type: Type of the collection (e.g., "Pokemon", "Movies", etc.)
    db: Firestore database instance
    """
    user_id = st.session_state.user_info['localId']

    # generates db collection name
    fullName = collection_name.title() + f"_{collection_type}"

    # check if name already exists in the database
    if checkForCollName(collection_name.title(), db):
        return True
    
    # created new collection
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set({"Info":[]})

# renames a collection
def rename_collection(collection_name:str, new_collection:str, db):
    """Renames a collection, by use of creating a new collection and moving the data
    
    collection_name: name of original collection
    new_collection: new name for collection
    db: database
    """
    user_id = st.session_state.user_info['localId']
    
    # gets reference and type of collection
    collection_ref_OLD = db.collection('Users').document(user_id).collection('Collections').document(collection_name.id)
    coll_Info = collection_ref_OLD.get().id.split("_")
    data = generate_collection(collection_name.id, db)
    # print(data)

    # checks if new name already exists in the database
    if checkForCollName(new_collection.title(), db):
        return True

    # created new collection to move data to
    fullName = f"{new_collection.title()}_{coll_Info[1]}"
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(data, merge=True)
    items = {"Info":[]}
    
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(items, merge=True)

    collection_ref_OLD.delete()

def add_reference_collectionView(db, user_id, item_doc_id, actual_item_id):
    pokemon_ref = db.collection("Pokemon").document(actual_item_id)
    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).set({item_doc_id: pokemon_ref}, merge=True)
    st.rerun()
    
def add_reference_search(db, user_id, item_doc_id, actual_item_id):
    pokemon_ref = db.collection("Pokemon").document(actual_item_id)
    db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL).set({item_doc_id: pokemon_ref}, merge=True)

def delete_reference(db, user_id, item_doc_id):
    delete = db.collection('Users').document(user_id).collection('Collections').document(CURR_COLL)
    delete.update({item_doc_id: firestore.DELETE_FIELD})
    st.rerun()

def checkForCollName(collection_name:str, db) -> bool:
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
    
def setCollection(collection:str):
    global CURR_COLL
    CURR_COLL = collection

REBRICK_API_KEY = st.secrets["REBRICK_API_KEY"]

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
                    "id": getattr(hit, 'id', getattr(hit, 'id', None)),
                    "name": getattr(hit, 'name', None),
                    "image": getattr(hit, 'image', None),
                    "flavorText": getattr(hit, 'flavorText', None),
                    "HP": getattr(hit, 'HP', getattr(hit, 'hp', None))
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
            'title': item['title'],
            'description': item['description'],
            'publisher': item.get('publisher', None),
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
