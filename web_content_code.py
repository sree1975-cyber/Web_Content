# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Lightweight Version
A complete solution for saving and organizing web content using only:
- Python's built-in html.parser
- Robust error handling
- No external HTML parsing dependencies
"""
import streamlit as st
import sqlite3
from datetime import datetime
import requests
from html.parser import HTMLParser
import numpy as np
from PIL import Image
import io
import base64
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
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
        self.in_description = False
        
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

# Configuration
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

def display_header():
    """Display application header with pure Streamlit"""
    st.title("🔖 Web Content Manager")
    st.subheader("Save, organize and rediscover your web treasures")
    st.markdown("---")

def init_db():
    """Initialize database with error handling"""
    try:
        conn = sqlite3.connect('file:web_content.db?mode=rwc', uri=True, timeout=10)
        c = conn.cursor()
        
        # Tables with improved schema
        c.execute('''CREATE TABLE IF NOT EXISTS links
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      url TEXT UNIQUE,
                      title TEXT,
                      description TEXT,
                      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
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
        
        # Add indexes for performance
        c.execute("CREATE INDEX IF NOT EXISTS idx_url ON links(url)")
        c.execute("CREATE INDEX IF NOT EXISTS idx_link_tags ON link_tags(link_id)")
        conn.commit()
        return conn
    except Exception as e:
        st.error(f"Database Error: {str(e)}")
        return None

def fetch_metadata(url):
    """Get page metadata using built-in HTMLParser"""
    try:
        # Validate and normalize URL
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
            
        parsed = urlparse(url)
        if not parsed.netloc:
            raise ValueError("Invalid URL format")
            
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'text/html'
        }
        
        response = requests.get(
            url, 
            headers=headers, 
            timeout=10,
            allow_redirects=True
        )
        response.raise_for_status()
        
        # Parse with built-in HTMLParser
        parser = MetadataParser()
        parser.feed(response.text)
        
        title = parser.title.strip() or url
        description = parser.description.strip()
        
        return title, description
    
    except requests.RequestException as e:
        st.warning(f"Couldn't fetch {url} - Network error")
        return url, ""
    except Exception as e:
        st.warning(f"Couldn't parse {url} - {str(e)}")
        return url, ""

def load_model():
    """Load sentence transformer model with fallback"""
    try:
        # Use smaller model for better compatibility
        return SentenceTransformer('all-MiniLM-L6-v2')
    except Exception as e:
        st.error(f"AI Model Error: {str(e)}")
        return None

def add_link_section(conn, model):
    """Section for adding new links"""
    st.subheader("🌐 Add New Web Content")
    
    url = st.text_input("URL", placeholder="https://example.com", key="url_input")
    
    if st.button("Fetch Metadata", disabled=not url):
        with st.spinner("Fetching..."):
            title, description = fetch_metadata(url)
            st.session_state['auto_title'] = title
            st.session_state['auto_description'] = description
    
    title = st.text_input("Title", 
                         value=st.session_state.get('auto_title', ''),
                         key="title_input")
    description = st.text_area("Description", 
                              value=st.session_state.get('auto_description', ''),
                              height=100,
                              key="desc_input")
    
    tags = st_tags(
        label='Tags:',
        text='Press enter to add',
        value=[],
        suggestions=['research', 'tutorial', 'news', 'tool']
    )
    
    if st.button("💾 Save Link", disabled=not url):
        save_link(conn, model, url, title, description, tags)

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
        
        # Generate and store embedding if model is available
        if model:
            text_to_embed = f"{title} {description}"
            embedding = model.encode(text_to_embed)
            c.execute("""
                INSERT OR REPLACE INTO embeddings (link_id, embedding) 
                VALUES (?, ?)
            """, (link_id, embedding.tobytes()))
        
        conn.commit()
        st.success("✅ Link saved successfully!")
        
        # Clear inputs
        if 'auto_title' in st.session_state:
            del st.session_state['auto_title']
        if 'auto_description' in st.session_state:
            del st.session_state['auto_description']
            
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")

def main():
    """Main application function"""
    display_header()
    
    with st.expander("ℹ️ About this app", expanded=False):
        st.write("""
        **Web Content Manager** (Lightweight Version) helps you:
        - Save web links with metadata
        - Organize with custom tags
        - Search your collection
        - No external HTML parsing dependencies
        """)
    
    # Initialize components
    conn = init_db()
    model = None  # Initialize without model
    
    # Try loading model but continue without if fails
    with st.spinner("Loading AI components..."):
        model = load_model()
        if not model:
            st.warning("Running in limited mode without AI features")
    
    if not conn:
        st.error("Failed to initialize database")
        return
    
    # Navigation
    try:
        with st.sidebar:
            selected = option_menu(
                "Main Menu",
                ["Add Link", "Browse", "Search", "Tags"],
                icons=['plus-circle', 'book', 'search', 'tags'],
                default_index=0
            )
    except:
        selected = "Add Link"  # Fallback
    
    # Route to selected section
    if selected == "Add Link":
        add_link_section(conn, model)
    elif selected == "Browse":
        browse_section(conn)
    elif selected == "Search":
        search_section(conn, model)
    elif selected == "Tags":
        tags_section(conn)

def browse_section(conn):
    """Display saved links"""
    st.subheader("📚 Your Saved Links")
    
    try:
        c = conn.cursor()
        
        # Get all tags for filtering
        tags = c.execute("SELECT name FROM tags").fetchall()
        selected_tags = st.multiselect(
            "Filter by tags", 
            [tag[0] for tag in tags],
            key="tag_filter"
        )
        
        # Build query based on selected tags
        query = """SELECT l.id, l.url, l.title, l.description, l.created_at 
                   FROM links l"""
        params = []
        
        if selected_tags:
            placeholders = ','.join(['?']*len(selected_tags))
            query += f""" JOIN link_tags lt ON l.id = lt.link_id
                         JOIN tags t ON lt.tag_id = t.id
                         WHERE t.name IN ({placeholders})
                         GROUP BY l.id HAVING COUNT(DISTINCT t.name) = ?"""
            params.extend(selected_tags)
            params.append(len(selected_tags))
        
        query += " ORDER BY l.created_at DESC"
        links = c.execute(query, params).fetchall()
        
        if not links:
            st.info("No links found. Add your first link!")
            return
            
        for link in links:
            with st.expander(f"{link[2]} ({link[4].split()[0]})"):
                st.caption(link[1])
                st.write(link[3])
                if st.button("Delete", key=f"del_{link[0]}"):
                    delete_link(conn, link[0])
                    st.experimental_rerun()
                    
    except Exception as e:
        st.error(f"Error browsing links: {str(e)}")

def delete_link(conn, link_id):
    """Delete a link from database"""
    try:
        c = conn.cursor()
        c.execute("DELETE FROM links WHERE id = ?", (link_id,))
        c.execute("DELETE FROM link_tags WHERE link_id = ?", (link_id,))
        c.execute("DELETE FROM embeddings WHERE link_id = ?", (link_id,))
        conn.commit()
        st.success("Link deleted")
    except Exception as e:
        st.error(f"Error deleting link: {str(e)}")

def search_section(conn, model):
    """Search through saved links"""
    st.subheader("🔍 Search Your Collection")
    
    search_type = st.radio(
        "Search type", 
        ["Keyword", "Semantic"] if model else ["Keyword"],
        horizontal=True
    )
    
    search_query = st.text_input("Search query", key="search_query")
    
    if st.button("Search", disabled=not search_query):
        with st.spinner("Searching..."):
            try:
                c = conn.cursor()
                
                if search_type == "Keyword":
                    # Basic keyword search
                    query = """SELECT id, url, title, description 
                               FROM links
                               WHERE title LIKE ? OR description LIKE ?"""
                    params = (f"%{search_query}%", f"%{search_query}%")
                    results = c.execute(query, params).fetchall()
                    
                elif search_type == "Semantic" and model:
                    # Semantic search
                    query_embedding = model.encode(search_query)
                    
                    # Get all embeddings
                    embeddings = c.execute("""
                        SELECT l.id, l.title, l.description, e.embedding 
                        FROM links l JOIN embeddings e ON l.id = e.link_id
                    """).fetchall()
                    
                    # Calculate similarities
                    results = []
                    for link_id, title, description, embedding_bytes in embeddings:
                        stored_embedding = np.frombuffer(embedding_bytes, dtype=np.float32)
                        similarity = cosine_similarity(
                            [query_embedding], 
                            [stored_embedding]
                        )[0][0]
                        results.append((link_id, title, description, similarity))
                    
                    # Sort by similarity
                    results.sort(key=lambda x: x[3], reverse=True)
                    results = [(r[0], r[1], r[2]) for r in results]  # Format results
                
                # Display results
                if results:
                    st.subheader(f"Found {len(results)} results")
                    for result in results[:20]:  # Limit to top 20
                        with st.expander(result[1]):
                            st.write(result[2])
                            st.caption(f"ID: {result[0]}")
                else:
                    st.info("No results found")
                    
            except Exception as e:
                st.error(f"Search failed: {str(e)}")

def tags_section(conn):
    """Manage tags"""
    st.subheader("🏷️ Tag Management")
    
    try:
        c = conn.cursor()
        
        # Show all tags with counts
        tags = c.execute("""
            SELECT t.name, COUNT(lt.link_id) 
            FROM tags t LEFT JOIN link_tags lt ON t.id = lt.tag_id
            GROUP BY t.name
            ORDER BY COUNT(lt.link_id) DESC
        """).fetchall()
        
        if tags:
            st.write("### Your Tags")
            for tag, count in tags:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{tag}**")
                with col2:
                    st.write(f"{count} links")
                    if st.button("✕", key=f"del_tag_{tag}"):
                        delete_tag(conn, tag)
                        st.experimental_rerun()
            st.markdown("---")
        
        # Add new tag
        new_tag = st.text_input("Create new tag")
        if st.button("Add Tag") and new_tag:
            try:
                c.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (new_tag,))
                conn.commit()
                st.success(f"Tag '{new_tag}' added")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error adding tag: {str(e)}")
                
    except Exception as e:
        st.error(f"Error loading tags: {str(e)}")

def delete_tag(conn, tag_name):
    """Delete a tag"""
    try:
        c = conn.cursor()
        c.execute("DELETE FROM tags WHERE name = ?", (tag_name,))
        conn.commit()
        st.success(f"Tag '{tag_name}' deleted")
    except Exception as e:
        st.error(f"Error deleting tag: {str(e)}")

if __name__ == "__main__":
    main()
