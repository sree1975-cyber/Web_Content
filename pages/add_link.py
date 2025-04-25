# -*- coding: utf-8 -*-
"""
Add Link Page
Page for adding new web links with metadata extraction and AI tagging.
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import numpy as np
from sentence_transformers import SentenceTransformer
from streamlit_tags import st_tags

# Initialize database
def init_db():
    """Initialize database with error handling"""
    try:
        conn = sqlite3.connect('web_content.db')
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
        return conn
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        return None

# Fetch metadata
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
        return url, ""

# Load model
def load_model():
    """Load sentence transformer model with error handling"""
    try:
        # Explicitly load model on CPU for Streamlit Cloud
        model = SentenceTransformer('all-MiniLM-L6-v2', device='cpu')
        return model
    except Exception as e:
        st.error(f"Model loading failed: {str(e)}")
        st.info("Please ensure all requirements are installed and try again")
        return None

# Save link
def save_link(conn, model, url, title, description, tags):
    """Save link to database"""
    try:
        now = datetime.now()
        c = conn.cursor()
        
        # Save link
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
        st.success("✅ Link saved successfully!")
        st.balloons()
        
        # Clear session state
        if 'auto_title' in st.session_state:
            del st.session_state['auto_title']
        if 'auto_description' in st.session_state:
            del st.session_state['auto_description']
            
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")

# Main function for this page
def main():
    st.subheader("🌐 Add New Web Content")
    
    # Initialize components
    conn = init_db()
    model = load_model()
    
    if conn is None or model is None:
        return
    
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
    
    # Tag input
    tags = st_tags(
        label='Tags:',
        text='Press enter to add',
        value=[],
        suggestions=['research', 'tutorial', 'news', 'tool', 'inspiration']
    )
    
    if st.button("💾 Save Link", disabled=not url):
        save_link(conn, model, url, title, description, tags)

if __name__ == "__main__":
    main()
