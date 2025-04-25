# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER
A single-page application to save and organize web links with AI-powered features.
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import numpy as np
from PIL import Image
import io
import base64
from sentence_transformers import SentenceTransformer
from streamlit_option_menu import option_menu
from streamlit_tags import st_tags
import logging
import boto3
import os

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set page configuration (MUST be the first Streamlit command)
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper functions
def get_image_base64():
    """Return base64 encoded placeholder image"""
    img = Image.new('RGB', (800, 400), color='#4b8bbe')
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

def init_db():
    """Initialize database with error handling"""
    try:
        # AWS S3 setup
        s3 = boto3.client('s3',
                         aws_access_key_id=st.secrets['AWS']['AWS_ACCESS_KEY_ID'],
                         aws_secret_access_key=st.secrets['AWS']['AWS_SECRET_ACCESS_KEY'])
        bucket_name = st.secrets['AWS']['S3_BUCKET']
        db_file = 'web_content.db'
        
        # Download database from S3 if it exists
        if not os.path.exists(db_file):
            try:
                s3.download_file(bucket_name, 'web_content.db', db_file)
                logging.info("Downloaded database from S3")
            except s3.exceptions.NoSuchKey:
                logging.info("No database found in S3, creating new one")
        
        conn = sqlite3.connect(db_file, check_same_thread=False)
        c = conn.cursor()
        
        c.execute('''CREATE TABLE IF NOT EXISTS links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT UNIQUE,
                      title TEXT,
                      description TEXT,
                      content TEXT,
                      created_at TIMESTAMP,
                      updated_at TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS link_tags
                     (link_id INTEGER,
                      tag_id INTEGER,
                      PRIMARY KEY (link_id, tag_id))''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS embeddings
                     (link_id INTEGER PRIMARY KEY,
                      embedding BLOB)''')
        
        conn.commit()
        # Upload initial database to S3
        s3.upload_file(db_file, bucket_name, 'web_content.db')
        logging.info("Uploaded initial database to S3")
        return conn
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        logging.error(f"Database initialization failed: {str(e)}")
        return None

def close_db(conn):
    """Close database connection and upload to S3"""
    if conn:
        try:
            s3 = boto3.client('s3',
                             aws_access_key_id=st.secrets['AWS']['AWS_ACCESS_KEY_ID'],
                             aws_secret_access_key=st.secrets['AWS']['AWS_SECRET_ACCESS_KEY'])
            bucket_name = st.secrets['AWS']['S3_BUCKET']
            db_file = 'web_content.db'
            s3.upload_file(db_file, bucket_name, 'web_content.db')
            logging.info("Uploaded database to S3 before closing")
            conn.close()
            logging.info("Database connection closed")
        except Exception as e:
            logging.error(f"Error closing database: {str(e)}")

def display_header():
    """Display beautiful header with AI image"""
    header_html = f"""
    <div style="background-color:#4b8bbe;padding:10px;border-radius:10px">
        <h1 style="color:white;text-align:center;">🔖 Web Content Manager</h1>
        <p style="color:white;text-align:center;">Save, organize and rediscover your web treasures</p>
        <img src="data:image/png;base64,{get_image_base64()}" style="width:100%;border-radius:10px;margin-top:10px;">
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

def fetch_metadata(url):
    """Get page metadata with error handling"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.title.string if soup.title else url
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else ""
        return title, description
    except Exception as e:
        st.warning(f"Couldn't fetch metadata: {str(e)}")
        logging.warning(f"Metadata fetch failed: {str(e)}")
        return url, ""

def load_model():
    """Load sentence transformer model with error handling"""
    try:
        logging.info("Loading SentenceTransformer model...")
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        logging.info("Model loaded successfully")
        return model
    except Exception as e:
        st.error(f"Model loading failed: {str(e)}")
        logging.error(f"Model loading failed: {str(e)}")
        st.info("Please ensure all requirements are installed and try again")
        return None

def save_link(conn, model, url, title, description, tags):
    """Save link to database"""
    try:
        now = datetime.now()
        c = conn.cursor()
        
        # Save link
        logging.info(f"Saving link: {url}")
        c.execute("""
            INSERT OR REPLACE INTO links 
            (url, title, description, created_at, updated_at) 
            VALUES (?, ?, ?, ?, ?)
        """, (url, title, description, now, now))
        
        link_id = c.lastrowid if c.lastrowid else c.execute(
            "SELECT id FROM links WHERE url = ?", (url,)
        ).fetchone()[0]
        
        # Process tags
        for tag in tags:
            c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
            tag_id = c.execute(
                "SELECT id FROM tags WHERE name = ?", (tag,)
            ).fetchone()[0]
            c.execute("""
                INSERT OR IGNORE INTO link_tags (link_id, tag_id) 
                VALUES (?, ?)
            """, (link_id, tag_id))
        
        # Generate and store embedding
        text_to_embed = f"{title} {description}"
        embedding = model.encode(text_to_embed)
        c.execute("""
            INSERT OR REPLACE INTO embeddings (link_id, embedding) 
            VALUES (?, ?)
        """, (link_id, embedding.tobytes()))
        
        conn.commit()
        # Upload to S3 after commit
        s3 = boto3.client('s3',
                         aws_access_key_id=st.secrets['AWS']['AWS_ACCESS_KEY_ID'],
                         aws_secret_access_key=st.secrets['AWS']['AWS_SECRET_ACCESS_KEY'])
        bucket_name = st.secrets['AWS']['S3_BUCKET']
        s3.upload_file('web_content.db', bucket_name, 'web_content.db')
        logging.info("Uploaded database to S3 after saving link")
        
        st.success("✅ Link saved successfully!")
        st.balloons()
        
        # Clear session state
        if 'auto_title' in st.session_state:
            del st.session_state['auto_title']
        if 'auto_description' in st.session_state:
            del st.session_state['auto_description']
            
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")
        logging.error(f"Error saving link: {str(e)}")
        conn.rollback()

def add_link_section(conn, model):
    """Section for adding new links"""
    st.subheader("🌐 Add New Web Content")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        url = st.text_input("URL", placeholder="https://example.com")
    with col2:
        st.write("")
        st.write("")
        if st.button("Fetch Metadata", disabled=not url):
            with st.spinner("Fetching..."):
                title, description = fetch_metadata(url)
                st.session_state['auto_title'] = title
                st.session_state['auto_description'] = description
    
    title = st.text_input("Title", value=st.session_state.get('auto_title', ''))
    description = st.text_area("Description", value=st.session_state.get('auto_description', ''), height=100)
    
    tags = st_tags(
        label='Tags:',
        text='Press enter to add',
        value=[],
        suggestions=['research', 'tutorial', 'news', 'tool', 'inspiration']
    )
    
    if st.button("💾 Save Link", disabled=not url):
        save_link(conn, model, url, title, description, tags)

def browse_section(conn):
    """Section for browsing saved links"""
    st.subheader("📚 Browse Saved Links")
    
    try:
        c = conn.cursor()
        c.execute("SELECT id, url, title, description, created_at FROM links ORDER BY created_at DESC")
        links = c.fetchall()
        
        if not links:
            st.info("No links saved yet. Add a link to get started!")
            return
        
        for link_id, url, title, description, created_at in links:
            with st.expander(f"{title or url} (Saved: {created_at})"):
                st.markdown(f"**URL**: {url}")
                st.markdown(f"**Description**: {description or 'No description'}")
                # Fetch tags
                c.execute("""
                    SELECT t.name FROM tags t
                    JOIN link_tags lt ON t.id = lt.tag_id
                    WHERE lt.link_id = ?
                """, (link_id,))
                tags = [row[0] for row in c.fetchall()]
                st.markdown(f"**Tags**: {', '.join(tags) if tags else 'None'}")
    except Exception as e:
        st.error(f"Error fetching links: {str(e)}")
        logging.error(f"Error fetching links: {str(e)}")

# Main function
def main():
    # Display header
    display_header()
    
    # About section
    with st.expander("ℹ️ About this app", expanded=False):
        st.write("""
        **Web Content Manager** helps you save and organize web links with:
        - AI-powered tagging and search
        - Visual bookmark management
        - Semantic content analysis
        - Beautiful intuitive interface
        
        Get started by selecting an option from the sidebar!
        """)
    
    # Initialize components
    conn = init_db()
    model = load_model()
    
    if conn is None or model is None:
        close_db(conn)
        return
    
    # Sidebar navigation
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Add Link", "Browse"],
            icons=['plus-circle', 'book'],
            default_index=0
        )
    
    # Render selected section
    if selected == "Add Link":
        add_link_section(conn, model)
    elif selected == "Browse":
        browse_section(conn)
    
    # Close database connection
    close_db(conn)

if __name__ == "__main__":
    main()
