import internetarchive
import streamlit as st
import tmdbsimple as tmdb
import rebrick
import json
from fastapi import FastAPI, Query, Path
from requests_futures.sessions import FuturesSession
import requests
from concurrent.futures import as_completed
from algoliasearch.search.client import SearchClientSync
from algoliasearch.search.models.search_params_object import SearchParamsObject
from google.cloud import firestore
import io
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from pyzbar import pyzbar
import firebase_admin
from firebase_admin import credentials, storage
from BackendMethods.auth_functions import access_secret_version
st.secrets = access_secret_version()

BASE_API_URL = "https://apitcg.com/api"
APITCG_API_KEY = st.secrets["APITCG_API_KEY"]
REBRICK_API_KEY = st.secrets["REBRICK_API_KEY"]
tmdb.API_KEY = st.secrets["TMDB_API_KEY"]
tmdb.REQUESTS_TIMEOUT = (2, 5)  # seconds, for connect and read specifically 
CURR_COLL = ""
SUB_COLL = ""
CURR_THEME = ".streamlit/st-styled.css"

app = FastAPI()

###################################################################################################
####################################### [General Data] ############################################
def set_collection(collection:str):
    """Sets the collection name for reference across pages
    
    collection: full name_type of the collection (doc.id)
    """
    global CURR_COLL
    global SUB_COLL
    CURR_COLL = collection
    SUB_COLL = ""

def set_sub_collection(sub_coll:str):
    """Sets the sub collection name for reference across pages
    
    subCollection: name of the sub collection
    """
    global SUB_COLL
    SUB_COLL = sub_coll

def setTheme(theme:str):
    global CURR_THEME
    CURR_THEME = theme


@st.cache_resource
def get_firestore_client():
    """Cached Firestore client to avoid repeated authentication."""
    return firestore.Client.from_service_account_info(st.secrets["firebase"])

@st.cache_resource
def get_cloud_storage():
    """Cached Cloud Storage client to avoid repeated authentication."""
    firebase_admin.initialize_app(credentials.Certificate(dict(st.secrets["firebase"])), {'storageBucket': "memorabiliacs-ec1bd.firebasestorage.app"})
    return storage.bucket()


@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_collection_types():
    """Fetch collection types."""
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
    """Get fields for a collection type."""
    db = get_firestore_client()
    typeRef = db.collection(coll_type)
    fields = typeRef.document("#TEMPLATE").get().to_dict()
    fields["Notes"] = True
    fields["Quantity"] = True
    return fields


def coll_visability(collection: str) -> bool:
    """Checks if the collection is visable for main page
    
    collection: name of collection
    Returns bool of visabliy
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    collection_ref = db.collection('Users').document(user_id).collection('Collections').document(collection)
    contents = collection_ref.get().to_dict()
    return not contents["settings"]["hidden"]

def check_for_coll_name(collection:str) -> bool:
    """Checks if the provided name is in the database
    
    collection: name checking for
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    collections = db.collection("Users").document(user_id).collection("Collections")
    for doc in collections.stream():
        collName = doc.id.split("_")
        if collName[0] == collection:
            return True
    return False

def check_for_sub_name(collection:str, sub_coll:str):
    """Checks if name for subcollection exists
    
    collection: source collection
    sub_coll: name checking for 
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    collections = db.collection("Users").document(user_id).collection("Collections").document(collection).collection("Sub Collections")
    for doc in collections.stream():
        if doc.id == sub_coll:
            return True
    return False

###################################################################################################
######################################### [Getting Data] ##########################################
@st.cache_data(ttl=3600)  # Cache for 1 hour
def get_cloud_storage_image(blob_name: str):
    """Fetch a signed URL for a blob in Cloud Storage
    
    blob_name: name to retreave data
    """
    bucket = get_cloud_storage()
    blob = bucket.blob(blob_name)
    return blob.generate_signed_url(version="v4", expiration=3600)


@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_user_data(user_id: str):
    """Fetch user data from Firestore, cached to reduce DB calls."""
    db = get_firestore_client()
    return db.collection("Users").document(user_id).get().to_dict()

## Main Coll ##
@st.cache_resource
def get_user_collections(user_id: str):
    """Fetch user's collections, cached to reduce DB calls."""
    db = get_firestore_client()
    return [{"id": doc.id,**doc.to_dict()} for doc in db.collection('Users').document(user_id).collection('Collections').stream()]

@st.cache_data(ttl=3600)
def get_collection_items(collection: str):
    """Fetch and process all items in a collection - cached to avoid repeated DB reads"""
    db = get_firestore_client()
    user_id = st.session_state.user_info['localId']

    collection_ref = db.collection('Users').document(user_id).collection('Collections').document(collection)
    data = collection_ref.get().to_dict()["items"]
    items = {}
    for item in data:
        items[item] = {'info' : (data[item].get('ref')).get().to_dict(),
                       'notes' : data[item].get('notes'),
                       'quantity' : data[item].get('quantity', 1)  # Default to 1 if quantity is not set
                    }
    return items

def collection_views(collection:str):
    """Gets the collection type views

    collection: name of the collection
    Returns list map(dict) of views
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    collection_ref = db.collection("Users").document(user_id).collection("Collections").document(collection)
    return collection_ref.get().to_dict()["settings"]["views"]

def get_collection_wishlisted(collection:str):
    """Gets all wishlisted items
    
    collection: full name of collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    coll_ref = db.collection("Users").document(user_id).collection("Collections").document(collection)
    data = coll_ref.get().to_dict().get("Wishlist", None)

    items = {}
    if data is not None:
        for item in data:
            items[item] = data[item].get("ref").get().to_dict()
    return items

## Sub Coll ##
@st.cache_data(ttl=3600)
def get_sub_collections(collection:str):
    """Cached function for getting all subcollections in a given collection
    
    collection: name of collection getting from
    returns a list of all subcollections
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    res = []
    for subColl in db.collection("Users").document(user_id).collection("Collections").document(collection).collection("Sub Collections").stream():
        res.append(subColl.id)
    return res

@st.cache_data(ttl=3600)
def get_sub_collection_items(collection:str, sub_collection: str):
    """Gets all items in a sub collection from the database.

    collection: Name of the collection sub collection is in
    sub_collection: Name of the sub collection to retrieve
    Returns a list of items (data dictionaries) referenced in the specified sub collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client() 

    collection = db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_collection).get()
    data = collection.to_dict()["items"]
    items = {}
    for item in data:
        items[item] = {'info' : (data[item].get('ref')).get().to_dict(),
                       'notes' : data[item].get('notes'),
                       'quantity' : data[item].get('quantity', 1)
                    }
    return items

def get_sub_coll_size(sub_coll:str, collection:str) -> int:
    """Gets the size of the given sub collection
    
    sub_coll: name of sub collection
    collection: parent collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client() 

    sub_collection = db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_coll)
    return int(sub_collection.get().to_dict()["settings"]["size"])


###################################################################################################
######################################### [Setting Data] ##########################################
## Main Coll ##
def create_collection(collection: str, collection_type: str):
    """Create a collection of items in the database with the specified name and type.

    collection: Name of the collection to create
    collection_type: Type of the collection (e.g., "Pokemon", "Movies", etc.)
    Returns true if collection already exits, else sets collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    # generates db collection name
    fullName = collection.title() + f"_{collection_type}"

    # check if name already exists in the database
    if check_for_coll_name(collection.title()):
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
            "background" : "",
            # ? way to re-order collections on main page ?
            "order" : "figure out later, way to sort/filter/order on main page",
            # hidden on main page
            "hidden" : False,
            # gid / colomn view
            "collection view" : "grid"
        }
    }
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(baseInfo)
    get_user_collections.clear(user_id)
    
def create_custom_collection(collection: str, collection_type: str):
    """Create a custom collection of items in the database with the specified name and type.

    collection_name: Name of the collection to create
    collection_type: Type of the collection (e.g., "Pokemon", "Movies", etc.)
    Returns true if collection already exits, else sets collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    # generates db collection name
    fullName = collection.title() + f"_{collection_type}"

    # check if name already exists in the database
    if check_for_coll_name(collection.title()):
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
            "hidden" : False,
            # gid / colomn view
            "collection view" : "grid"
        },
        
        # list of item templates
        "templates": {}
    }
    db.collection('Custom').document(fullName).set(baseInfo)
    db.collection('Users').document(user_id).collection('Collections').document(fullName).set(baseInfo)
    get_user_collections.clear(user_id)

@st.cache_data(ttl=3600)
def get_template_types():
    """Fetch collection types, cached globally."""
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    types = db.collection("Users").document(user_id).collection("Collections").document(CURR_COLL).get().to_dict()['templates']
    tlist = []
    for key in types.keys():
        if key != "No Custom Template":
            tlist.append(key)
    if not tlist:
        info = db.collection("Users").document(user_id).collection("Collections").document(CURR_COLL).get().to_dict().get("items", None)
        if info != {} and info is not None:
             return ["UPC ITEMS"]
        else:
            return ["No Custom Template"]
    else:
        return tlist

def rename_collection(collection:str, new_name:str):
    """Renames a collection, by use of creating a new collection and moving the data
    
    collection_: name of original collection
    new_name: new name for collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    
    # gets reference and type of collection
    collection_ref_OLD = db.collection('Users').document(user_id).collection('Collections').document(collection)
    coll_Info = collection_ref_OLD.get().id.split("_")

    # checks if new name already exists in the database
    if check_for_coll_name(new_name.title(), db):
        return True

    # created new collection to move data to
    fullName = f"{new_name.title()}_{coll_Info[1]}"
    
    new_coll = db.collection('Users').document(user_id).collection('Collections').document(fullName)
    new_coll.set(collection_ref_OLD.get().to_dict())
    for sub in get_sub_collections(collection):
        data = get_sub_collection_items(collection, sub)
        new_coll.collection("Sub Collections").document(sub).set(data)
    collection_ref_OLD.delete()
    get_user_collections.clear(user_id)

def delete_collection(collection:str):
    """Deletes collection
    
    collection: full name of collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    ref = db.collection("Users").document(user_id).collection("Collections").document(collection)
    db.recursive_delete(ref)

def update_notes(item:str, new_notes:str, collection:str):
    """Sets the user's specific note per item
    
    item: name of the item
    new_notes: note for item
    collection: name of collection item is in
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    db.collection('Users').document(user_id).collection('Collections').document(collection).update(
            {f"items.{item}.notes": new_notes}
        )
    get_collection_items.clear(collection)  # Clear cache for this collection to reflect updated notes

def add_item(item:str, notes:str, quantity:int, collection:str):
    """Adds an Item to a users collection, does not rerun

    item: the id/name of the item
    notes: specific per user note for item
    quantitiy: how many to add
    collection: collection to add item to
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    coll_type = collection.split("_")[1]

    item_ref = db.collection(coll_type).document(item)
    fixed_name = item_ref.get().id.replace("-", "_")
    ref = db.collection('Users').document(user_id).collection('Collections').document(collection)
    items = get_collection_items(collection)
    if fixed_name in items:
        ammount = int(ref.get().to_dict()["items"][fixed_name]["quantity"])
        ammount += quantity
        ref.update({f"items.{fixed_name}.quantity" : ammount})
        ref.update({f"items.{fixed_name}.notes" : notes})
    else: 
        ref.update({
        f"items.{fixed_name}": {
            "notes": notes,
            "ref": item_ref,
            "quantity" : quantity
            }
        })
    wishlist = get_collection_wishlisted(collection)
    if fixed_name in wishlist:
        delete_wishilst_item(fixed_name, collection)
    get_collection_items.clear(collection)

def wishlist_item(item:str, collection:str) -> bool:
    """Adds item to collection as wishlisted item
    
    item: item id
    collection: full collection name
    Return false if error, true if success"""
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    coll_type = collection.split("_")[1]

    fixed_name = item.replace("-", "_")
    item_ref = db.collection(coll_type).document(item)
    coll_ref = db.collection("Users").document(user_id).collection("Collections").document(collection)

    coll_items = get_collection_items(collection)
    if fixed_name in coll_items:
        return False

    coll_ref.update({f"Wishlist.{fixed_name}" : {
        "ref" : item_ref
    }})
    return True

def delete_reference(item:str, collection:str):
    """Deleted an item from the user's collection

    item: the name of item in user's collection
    collection: collection item in
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    ref = db.collection('Users').document(user_id).collection('Collections').document(collection)
    ammount = int(ref.get().to_dict()["items"][item]["quantity"])
    if ammount == 1:
        ref.update({
            f"items.{item}": firestore.DELETE_FIELD
        })
    else:
        ammount -= 1
        ref.update({f"items.{item}.quantity": ammount })
    get_collection_items.clear(collection)

def delete_wishilst_item(item:str, collection:str):
    """Removes given item from wishlist in given collection
    
    item: item id
    collection: full collection name
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    ref = db.collection("Users").document(user_id).collection("Collections").document(collection)
    ref.update({f"Wishlist.{item}": firestore.DELETE_FIELD})

def update_collection_views(collection:str, views:dict):
    """Updates the type views for the collection

    collection_name: name of collection
    views: dictonary of fields and booleans per item type
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    collection_ref = db.collection("Users").document(user_id).collection("Collections").document(collection)
    collection_ref.update({"settings.views": views})

def upload_user_image(uploaded_file, firestore_field: str = "profile_image_blob") -> str:
    """Uploads Streamlit UploadedFile to GCS, stores blob path in Firestore.

    uploaded_file: file of image
    Returns blob_name.
    """
    bucket = get_cloud_storage()
    user_id = st.session_state.user_info['localId']

    blob_name = f"user_uploads/{user_id}/{uploaded_file.name}"
    blob = bucket.blob(blob_name)

    blob.upload_from_string(
        uploaded_file.getvalue(),
        content_type=(uploaded_file.type or "application/octet-stream")
    )

    return blob_name

## Sub Coll ##
def create_sub_collection(sub_coll:str, collection:str, size:int):
    """Creates a subcollection in a given collection
    
    sub_coll: name of sub colleciton
    collection: name of parent collection
    size: size of sub collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    baseInfo = {
        # list of items per collection
        "items": {},

        # collection settings
        "settings": {
            # sets what fields are viewed via item type
            "views" : collection_views(collection),
            # sets preview image 
            "image" : "url to display image",
            # sets a background image when viewing collection
            "background" : "",
            # ? way to re-order collections on main page ?
            "order" : "figure out later, way to sort/filter/order on main page",
            # hidden on main page
            "hidden" : False,
            # number of items avalible for sub collection
            "size" : size
        }
    }
    db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_coll.title()).set(baseInfo)
    get_sub_collections.clear(collection)

def rename_sub_collection(collection:str, sub_coll:str, new_name:str):
    """Renames a sub collection, by use of creating a new collection and moving the data
    
    collection_name: name of source collection
    sub_coll: name for sub collection
    new_name: new name for sub collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    
    # gets reference and type of collection
    collection_ref = db.collection('Users').document(user_id).collection('Collections').document(collection)
    old_sub = collection_ref.collection("Sub Collections").document(sub_coll)

    # checks if new name already exists in the database
    new_name = new_name.title()
    if check_for_sub_name(collection, new_name, db):
        return True

    # created new collection to move data to
    collection_ref.collection("Sub Collections").document(new_name).set(old_sub.get().to_dict())
    old_sub.delete()
    get_sub_collection_items.clear(collection, new_name)

def delete_sub_collection(sub_coll:str, collection:str):
    """Removes subcollection from collection
    
    name: name of subcollection
    collection: parent collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    sub_ref = db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_coll)
    sub_ref.delete()
    get_sub_collections.clear(collection)

def add_item_sub_coll(item:str, notes:str, quantity:int, sub_coll:str, collection:str):
    """Adds an item to a users sub collection

    item: the id/name of the item
    notes: specific per user note for item
    quantitiy: how many to add
    sub_coll: name of sub collection
    collection: name of parent collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()

    coll_type = collection.split("_")[1]
    fixed_name = item.replace("_", "-")
    item_ref = db.collection(coll_type).document(fixed_name)

    sub_ref = db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_coll)
    sub_ref.update({
    f"items.{item}": {
        "notes": notes,
        "ref": item_ref,
        "quantity" : quantity
        }
    })
    get_sub_collection_items.clear(collection, sub_coll)

def del_item_sub_coll(item:str, quantity:int, sub_coll:str, collection:str):
    """Removes an item to a users sub collection

    item: the id/name of the item
    quantitiy: how many to remove
    sub_coll: name of sub collection
    collection: name of parent collection
    """
    user_id = st.session_state.user_info['localId']
    db = get_firestore_client()
    sub_ref = db.collection('Users').document(user_id).collection('Collections').document(collection).collection("Sub Collections").document(sub_coll)
    ammount = int(sub_ref.get().to_dict()["items"][item]['quantity'])
    if ammount - quantity <= 0:
        sub_ref.update({f"items.{item}" : firestore.DELETE_FIELD})
    else:
        ammount -= quantity
        sub_ref.update({f"items.{item}.quantity": ammount})
    get_sub_collection_items.clear(collection, sub_coll)

###################################################################################################
############################################ [Other] ##############################################
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
            'name': movie.get('title'),
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
            'name': name,
            'creator': creator,
            'image': thumb_url,
            'format': fmt,
        })

    return results

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
                    "name": getattr(hit, 'Name', None),
                    "image": getattr(hit, 'Image', None),
                    "flavorText": getattr(hit, 'Flavor Text', None),
                    "hp": getattr(hit, 'HP', getattr(hit, 'HP', None))
                })
            return results
        
        elif index_name == "MovieSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "release_date": getattr(hit, 'Release Date', None),
                    "overview": getattr(hit, 'Overview', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results
        
        elif index_name == "DragonballSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "power": getattr(hit, 'Power', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results
        
        elif index_name == "DigimonSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "cardType": getattr(hit, 'Card Type', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results
        
        elif index_name == "OnepieceSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "type": getattr(hit, 'Type', None),
                    "image": getattr(hit, 'Image', None),
                    "rarity": getattr(hit, 'Rarity', None)
                })
            return results
        
        elif index_name == "LegoSetSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "year": getattr(hit, 'Year of Release', None),
                    "num_parts": getattr(hit, 'Number of Parts', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results

        elif index_name == "LegoMinifigSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "minifig_number": getattr(hit, 'Minifig Number', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results
        
        elif index_name == "MagicSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "mana_cost": getattr(hit, 'Mana Cost', None),
                    "type_line": getattr(hit, 'Type', None),
                    "oracle_text": getattr(hit, 'Set', None),
                    "image": getattr(hit, 'Image', None)
                })
            return results

        elif index_name == "MusicSearchResults":
            results = []
            for hit in hits:
                results.append({
                    "id": getattr(hit, 'object_id', None),
                    "name": getattr(hit, 'Name', None),
                    "artist": getattr(hit, 'Artist', None),
                    "release_year": getattr(hit, 'Year', None),
                    "image": getattr(hit, 'Image', None),
                    "format": getattr(hit, 'Format', None),
                    "genre": getattr(hit, 'Genre', None)
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
            'Name': item['title'],
            'Description': item['description'],
            # 'publisher': item.get('publisher', None) if item['publisher'] else None,
            'id': item['ean'],
            'Image': item['images'][0] if item['images'] else None, # Get the first image if available
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




def get_user_image_names(user_id: str, db) -> list[str]:
    docs = (
        db.collection("Users")
        .document(user_id)
        .collection("UserImages")
        .stream()
    )
    return [(doc.to_dict() or {}).get("image_name", "") for doc in docs]
