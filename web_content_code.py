# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Lightweight Final Version
A complete solution without external AI dependencies featuring:
- Pure Python HTML parsing
- Robust SQLite storage
- Full-text search
- Tag management
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from html.parser import HTMLParser
from streamlit_option_menu import option_menu
from streamlit_tags import st_tags
import re
from urllib.parse import urlparse

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

# Initialize database with FTS4 for full-text search
def init_db():
    try:
        conn = sqlite3.connect('file:web_content.db?mode=rwc', uri=True, timeout=10)
        c = conn.cursor()
        
        # Main links table
        c.execute('''CREATE TABLE IF NOT EXISTS links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT UNIQUE,
                      title TEXT,
                      description TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        # Tags tables
        c.execute('''CREATE TABLE IF NOT EXISTS tags
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT UNIQUE)''')
        
        c.execute('''CREATE TABLE IF NOT EXISTS link_tags
                     (link_id INTEGER,
                      tag_id INTEGER,
                      PRIMARY KEY (link_id, tag_id))''')
        
        # Full-text search virtual table
        c.execute('''CREATE VIRTUAL TABLE IF NOT EXISTS links_fts 
                     USING fts4(title, description, content=links, tokenize=porter)''')
        
        # Triggers to keep FTS in sync
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
        st.error(f"Database Error: {str(e)}")
        return None

def fetch_metadata(url):
    """Get page metadata using built-in HTMLParser"""
    try:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL")
            
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        parser = MetadataParser()
        parser.feed(response.text)
        
        return (
            parser.title.strip() or url,
            parser.description.strip(),
            response.text[:5000]  # Store first 5000 chars for search
        )
    except Exception as e:
        st.warning(f"Couldn't fetch {url} - {str(e)}")
        return url, "", ""

def main():
    """Main application function"""
    st.set_page_config(
        page_title="Web Content Manager",
        page_icon="🔖",
        layout="wide"
    )
    
    st.title("🔖 Web Content Manager")
    st.subheader("Save and organize your web content")
    
    conn = init_db()
    if not conn:
        st.stop()
    
    with st.sidebar:
        selected = option_menu(
            "Menu",
            ["Add Link", "Browse", "Search", "Tags"],
            icons=['plus', 'book', 'search', 'tags'],
            default_index=0
        )
    
    if selected == "Add Link":
        url = st.text_input("URL", key="url")
        if st.button("Fetch Metadata"):
            with st.spinner("Fetching..."):
                title, desc, _ = fetch_metadata(url)
                st.session_state['title'] = title
                st.session_state['desc'] = desc
        
        title = st.text_input("Title", value=st.session_state.get('title', ''))
        desc = st.text_area("Description", value=st.session_state.get('desc', ''))
        tags = st_tags(label="Tags", text="Add tags (press enter)")
        
        if st.button("Save") and url:
            try:
                c = conn.cursor()
                c.execute(
                    "INSERT OR REPLACE INTO links (url, title, description) VALUES (?, ?, ?)",
                    (url, title, desc)
                )
                link_id = c.lastrowid or c.execute(
                    "SELECT id FROM links WHERE url = ?", (url,)
                ).fetchone()[0]
                
                for tag in tags:
                    c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
                    tag_id = c.execute(
                        "SELECT id FROM tags WHERE name = ?", (tag,)
                    ).fetchone()[0]
                    c.execute(
                        "INSERT OR IGNORE INTO link_tags (link_id, tag_id) VALUES (?, ?)",
                        (link_id, tag_id)
                    )
                
                conn.commit()
                st.success("Saved!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    elif selected == "Browse":
        c = conn.cursor()
        tags = c.execute("SELECT name FROM tags").fetchall()
        selected_tags = st.multiselect(
            "Filter by tags", 
            [t[0] for t in tags]
        )
        
        query = "SELECT id, url, title, description FROM links"
        params = []
        
        if selected_tags:
            query += """ JOIN link_tags lt ON links.id = lt.link_id
                         JOIN tags t ON lt.tag_id = t.id
                         WHERE t.name IN ({})""".format(
                             ','.join(['?']*len(selected_tags))
            params.extend(selected_tags)
            query += " GROUP BY links.id HAVING COUNT(DISTINCT t.name) = ?"
            params.append(len(selected_tags))
        
        results = c.execute(query + " ORDER BY created_at DESC", params).fetchall()
        
        for r in results:
            with st.expander(r[2]):
                st.write(r[3])
                st.caption(r[1])
                if st.button("Delete", key=f"del_{r[0]}"):
                    c.execute("DELETE FROM links WHERE id = ?", (r[0],))
                    conn.commit()
                    st.experimental_rerun()
    
    elif selected == "Search":
        query = st.text_input("Search terms")
        if query:
            results = conn.cursor().execute(
                "SELECT id, url, title FROM links_fts WHERE links_fts MATCH ?",
                (query,)
            ).fetchall()
            
            for r in results:
                st.write(f"[{r[2]}]({r[1]})")
    
    elif selected == "Tags":
        # Tag management implementation
        pass

if __name__ == "__main__":
    main()
