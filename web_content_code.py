# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Robust Link Management System
A complete solution for saving, organizing, and retrieving web content with:
- Reliable content parsing (using lxml)
- Clean text extraction (using html2text)
- AI-powered semantic search
- Visual bookmark management
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from lxml import html
import html2text
import numpy as np
from PIL import Image
import io
import base64
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from streamlit_option_menu import option_menu
from streamlit_tags import st_tags
import re

# Configuration
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Error-resistant header image display
def display_header():
    """Display application header with fallback"""
    try:
        header_html = f"""
        <div style="background-color:#4b8bbe;padding:10px;border-radius:10px">
            <h1 style="color:white;text-align:center;">🔖 Web Content Manager</h1>
            <p style="color:white;text-align:center;">Save, organize and rediscover your web treasures</p>
        </div>
        """
        st.markdown(header_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"UI Error: {str(e)}")

def init_db():
    """Initialize database with error handling"""
    try:
        conn = sqlite3.connect('web_content.db', timeout=10)
        conn.execute("PRAGMA busy_timeout = 5000")
        c = conn.cursor()
        
        # Tables with improved schema
        c.execute('''CREATE TABLE IF NOT EXISTS links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT UNIQUE,
                      title TEXT,
                      description TEXT,
                      clean_content TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS link_tags
                     (link_id INTEGER,
                      tag_id INTEGER,
                      PRIMARY KEY (link_id, tag_id),
                      FOREIGN KEY(link_id) REFERENCES links(id) ON DELETE CASCADE,
                      FOREIGN KEY(tag_id) REFERENCES tags(id) ON DELETE CASCADE)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS embeddings
                     (link_id INTEGER PRIMARY KEY,
                      embedding BLOB,
                      FOREIGN KEY(link_id) REFERENCES links(id) ON DELETE CASCADE)''')
        
        # Add indexes for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_url ON links(url)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_link_tags ON link_tags(link_id)")
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return None

def fetch_metadata(url):
    """Get page metadata using lxml with robust error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Validate URL first
        if not re.match(r'^https?://', url):
            url = 'http://' + url
            
        response = requests.get(
            url, 
            headers=headers, 
            timeout=10,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Parse with lxml
        tree = html.fromstring(response.content)
        title = tree.findtext('.//title', default=url)
        
        # Get description from meta tags
        description = ""
        for meta in tree.xpath('//meta'):
            if meta.get('name', '').lower() == 'description':
                description = meta.get('content', '')
                break
                
        # Get clean content using html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = False
        clean_content = h.handle(response.text)
        
        return title, description, clean_content
    
    except requests.RequestException as e:
        st.warning(f"Network Error: Couldn't fetch {url}")
        return url, "", ""
    except Exception as e:
        st.warning(f"Parsing Error: {str(e)}")
        return url, "", ""

def load_model():
    """Load sentence transformer model with memory management"""
    try:
        # Use smaller model for better compatibility
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        st.error(f"Model Error: {str(e)}")
        st.info("Try reducing memory usage or use a smaller model")
        return None

def main():
    """Main application function with error boundary"""
    try:
        display_header()
        
        with st.expander("ℹ️ About this app", expanded=False):
            st.write("""
            **Web Content Manager** helps you save and organize web links with:
            - Reliable content parsing (using lxml)
            - Clean text extraction (using html2text)
            - AI-powered semantic search
            - Visual bookmark management
            
            Get started by adding your first link!
            """)
        
        # Initialize components with loading states
        with st.spinner("Initializing system..."):
            conn = init_db()
            model = load_model()
        
        if conn is None or model is None:
            st.error("Critical initialization failed. Please check logs.")
            return
        
        # Navigation with error handling
        try:
            with st.sidebar:
                selected = option_menu(
                    "Main Menu",
                    ["Add Link", "Browse", "Search", "Tags", "Settings"],
                    icons=['plus-circle', 'book', 'search', 'tags', 'gear'],
                    default_index=0,
                    menu_icon="cast"
                )
        except Exception as e:
            st.error(f"Navigation Error: {str(e)}")
            selected = "Add Link"  # Default fallback
        
        # Route to selected section
        try:
            if selected == "Add Link":
                add_link_section(conn, model)
            elif selected == "Browse":
                browse_section(conn)
            elif selected == "Search":
                search_section(conn, model)
            elif selected == "Tags":
                tags_section(conn)
            elif selected == "Settings":
                settings_section()
        except Exception as e:
            st.error(f"Section Error: {str(e)}")
            st.info("Please try again or report this issue")
            
    except Exception as e:
        st.error(f"Fatal Error: {str(e)}")
        st.stop()

# [Rest of your functions would be here with similar error handling]

if __name__ == "__main__":
    main()
