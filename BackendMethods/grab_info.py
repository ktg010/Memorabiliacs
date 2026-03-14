import json
from pathlib import Path
from google.cloud import firestore
from google.cloud import firestore
import streamlit as st

try:
    db = firestore.Client.from_service_account_info(st.secrets["firebase"])
except Exception as e:
    st.error(f"Failed to initialize Firestore: {e}")
    st.stop()   


def main():
    print("Grabbing info")
    
# Folder containing the pokemon card JSON files


# Firestore client
db = firestore.Client()

print("Starting upload...")





