import streamlit as st
import json
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import hmac
import re
import logging
from typing import Optional
from langchain_community.document_loaders import WebBaseLoader

# Function to save feedback to a file
def save_feedback(feedback_text):
    # Load the credentials from the secrets
    credentials_data = st.secrets["gcp"]["service_account_json"]
    # print(credentials_data)
    creds = json.loads(credentials_data, strict=False)

    # Set up the Google Sheets API credentials
    scope = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
    credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
    client = gspread.authorize(credentials)

    # Open the Google Sheet
    sheet_id = '1qnFzZZ7YI-9pXj3iAXafjRmC_EIQyK9gA98AjMv29DM'
    sheet = client.open_by_key(sheet_id).worksheet("linkedinposts")
    sheet.append_row([feedback_text])

# Password checking function
def check_password():
    """Returns `True` if the user had the correct password."""
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False

def setup_logging():
    """Configure logging for the application"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)

def ensure_url(string: str) -> str:
    """Ensures a given string is a properly formatted URL"""
    if not string.startswith(("http://", "https://")):
        string = "http://" + string

    url_regex = re.compile(
        r"^(https?:\/\/)?"
        r"(www\.)?"
        r"([a-zA-Z0-9.-]+)"
        r"(\.[a-zA-Z]{2,})?"
        r"(:\d+)?"
        r"(\/[^\s]*)?$",
        re.IGNORECASE,
    )

    if not url_regex.match(string):
        msg = f"Invalid URL: {string}"
        raise ValueError(msg)

    return string

def fetch_website_content(url: str, max_length: int = 10000) -> Optional[str]:
    """Fetch and process content from a website"""
    try:
        validated_url = ensure_url(url)
        web_loader = WebBaseLoader(web_paths=[validated_url], encoding="utf-8")
        text_docs = web_loader.load()
        
        if text_docs:
            return text_docs[0].page_content.strip()[:max_length]
        return None
    except Exception as e:
        logging.error(f"Error fetching website content: {str(e)}")
        return None