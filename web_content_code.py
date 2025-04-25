# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Final Working Version
Robust bookmark manager with:
- Pure Python implementation
- No external dependencies
- Full-text search
- Tag management
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from html.parser import HTMLParser
from urllib.parse import urlparse
import re

# Custom HTML Parser
class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.title = ""
        self.description = ""
        self.in_title = False
        
    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
        elif tag == "meta":
            attrs = dict(attrs)
            if 'name' in attrs and attrs['name'].lower() == 'description':
                self.description = attrs.get('content', '')
    
    def handle_data(self, data):
        if self.in_title:
            self.title += data
    
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False

def init_db():
    """Initialize database with proper error handling"""
    try:
        conn = sqlite3.connect('web_content.db')
        c = conn.cursor()
        
        # Main tables
        c.execute('''CREATE TABLE IF NOT EXISTS links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT UNIQUE,
                      title TEXT,
                      description TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS link_tags
                     (link_id INTEGER,
                      tag_id INTEGER,
                      PRIMARY KEY (link_id, tag_id))''')
        
        # Full-text search table
        c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS links_fts 
                     USING fts4(title, description)''')
        
        # Triggers to maintain FTS
        c.execute('''CREATE TRIGGER IF NOT EXISTS links_ai AFTER INSERT ON links
                     BEGIN
                         INSERT INTO links_fts(docid, title, description)
                         VALUES(new.id, new.title, new.description);
                     END''')
        
        c.execute('''CREATE TRIGGER IF NOT EXISTS links_ad AFTER DELETE ON links
                     BEGIN
                         DELETE FROM links_fts WHERE docid = old.id;
                     END''')
        
        c.execute('''CREATE TRIGGER IF NOT EXISTS links_au AFTER UPDATE ON links
                     BEGIN
                         UPDATE links_fts SET 
                             title = new.title,
                             description = new.description
                         WHERE docid = new.id;
                     END''')
        
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Database initialization failed: {str(e)}")
        return None

def fetch_metadata(url):
    """Get page metadata with robust error handling"""
    try:
        if not re.match(r'^https?://', url):
            url = 'https://' + url
            
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        parser = MetadataParser()
        parser.feed(response.text)
        
        return (
            parser.title.strip() or url,
            parser.description.strip()
        )
    except Exception as e:
        st.warning(f"Couldn't fetch metadata: {str(e)}")
        return url, ""

def browse_section(conn):
    """Display and filter saved links"""
    st.subheader("Your Saved Links")
    
    try:
        c = conn.cursor()
        
        # Get available tags
        tags = [t[0] for t in c.execute("SELECT name FROM tags").fetchall()]
        selected_tags = st.multiselect("Filter by tags", tags)
        
        # Build query - FIXED SYNTAX ERROR HERE
        query = """SELECT l.id, l.url, l.title, l.description 
                   FROM links l"""
        params = []
        
        if selected_tags:
            placeholders = ','.join(['?'] * len(selected_tags))
            query += f""" JOIN link_tags lt ON l.id = lt.link_id
                          JOIN tags t ON lt.tag_id = t.id
                          WHERE t.name IN ({placeholders})
                          GROUP BY l.id HAVING COUNT(DISTINCT t.name) = ?"""
            params.extend(selected_tags)
            params.append(len(selected_tags))
        
        query += " ORDER BY l.created_at DESC"
        results = c.execute(query, params).fetchall()
        
        if not results:
            st.info("No links found. Add your first link!")
            return
            
        for link in results:
            with st.expander(link[2]):
                st.write(link[3])
                st.caption(link[1])
                if st.button("Delete", key=f"del_{link[0]}"):
                    c.execute("DELETE FROM links WHERE id = ?", (link[0],))
                    conn.commit()
                    st.experimental_rerun()
    
    except Exception as e:
        st.error(f"Error browsing links: {str(e)}")

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Web Content Manager",
        page_icon="🔖",
        layout="wide"
    )
    
    st.title("🔖 Web Content Manager")
    
    conn = init_db()
    if not conn:
        st.stop()
    
    menu = ["Add Link", "Browse", "Search"]
    choice = st.sidebar.selectbox("Menu", menu)
    
    if choice == "Add Link":
        url = st.text_input("URL")
        if st.button("Fetch Metadata") and url:
            with st.spinner("Fetching..."):
                title, desc = fetch_metadata(url)
                st.session_state['title'] = title
                st.session_state['desc'] = desc
        
        title = st.text_input("Title", value=st.session_state.get('title', ''))
        desc = st.text_area("Description", value=st.session_state.get('desc', ''))
        
        if st.button("Save") and url:
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO links (url, title, description) VALUES (?, ?, ?)",
                    (url, title, desc)
                )
                conn.commit()
                st.success("Link saved successfully!")
            except Exception as e:
                st.error(f"Error saving link: {str(e)}")
    
    elif choice == "Browse":
        browse_section(conn)
    
    elif choice == "Search":
        query = st.text_input("Search your bookmarks")
        if query:
            results = conn.cursor().execute(
                "SELECT url, title FROM links_fts WHERE links_fts MATCH ?",
                (query,)
            ).fetchall()
            
            for url, title in results:
                st.write(f"[{title}]({url})")

if __name__ == "__main__":
    main()
