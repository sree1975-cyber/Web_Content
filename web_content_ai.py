# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Enhanced Version with All Features
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from streamlit_option_menu import option_menu
from streamlit_tags import st_tags
import logging
import os
from html import escape

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set page configuration
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    /* Main styles */
    .header {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    .card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
    }
    
    /* Dataframe styling */
    .dataframe {
        width: 100%;
    }
    
    /* Tag styling */
    .tag {
        display: inline-block;
        background: #e0e7ff;
        color: #4f46e5;
        padding: 0.2rem 0.5rem;
        border-radius: 1rem;
        font-size: 0.8rem;
        margin-right: 0.5rem;
        margin-bottom: 0.3rem;
    }
    
    /* Delete button styling */
    .delete-btn {
        background-color: #ff4b4b !important;
        color: white !important;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def init_data():
    """Initialize or load Excel file for storing links"""
    excel_file = 'web_links.xlsx'
    try:
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file, engine='openpyxl')
            # Convert tags from string to list
            if 'tags' in df.columns:
                df['tags'] = df['tags'].apply(lambda x: x.split(',') if isinstance(x, str) else [])
            logging.info("Loaded existing Excel file")
        else:
            df = pd.DataFrame(columns=[
                'id', 'url', 'title', 'description', 'tags', 
                'created_at', 'updated_at'
            ])
            logging.info("Created new Excel file")
        return df, excel_file
    except Exception as e:
        st.error(f"Failed to initialize data: {str(e)}")
        logging.error(f"Data initialization failed: {str(e)}")
        return pd.DataFrame(), excel_file

def save_data(df, excel_file):
    """Save DataFrame to Excel file"""
    try:
        # Convert tags from list to string before saving
        df_to_save = df.copy()
        if 'tags' in df_to_save.columns:
            df_to_save['tags'] = df_to_save['tags'].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else '')
        
        df_to_save.to_excel(excel_file, index=False, engine='openpyxl')
        logging.info("Data saved successfully")
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        logging.error(f"Data save failed: {str(e)}")
        return False

def save_link(df, url, title, description, tags):
    """Save or update a link in the DataFrame"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if URL already exists
        existing_index = df[df['url'] == url].index
        
        if not existing_index.empty:
            # Update existing entry
            idx = existing_index[0]
            df.at[idx, 'title'] = title
            df.at[idx, 'description'] = description
            df.at[idx, 'tags'] = [str(tag).strip() for tag in tags if str(tag).strip()]
            df.at[idx, 'updated_at'] = now
            action = "updated"
        else:
            # Create new entry
            new_id = df['id'].max() + 1 if not df.empty else 1
            new_entry = {
                'id': new_id,
                'url': url,
                'title': title,
                'description': description,
                'tags': [str(tag).strip() for tag in tags if str(tag).strip()],
                'created_at': now,
                'updated_at': now
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            action = "saved"
        
        return df, action
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")
        logging.error(f"Link save failed: {str(e)}")
        return df, None

def delete_link(df, excel_file, url):
    """Delete a link from the DataFrame"""
    try:
        if url in df['url'].values:
            df = df[df['url'] != url]
            if save_data(df, excel_file):
                st.success("✅ Link deleted successfully!")
                st.session_state['df'] = df
                st.balloons()
                return df
        else:
            st.warning("Link not found in database")
        return df
    except Exception as e:
        st.error(f"Error deleting link: {str(e)}")
        return df

def display_header():
    """Display beautiful header"""
    st.markdown("""
    <div class="header">
        <h1 style="color: white; margin-bottom: 0;">🔖 Web Content Manager</h1>
        <p style="color: white; opacity: 0.9; font-size: 1.1rem;">
        Save, organize, and rediscover your web treasures
        </p>
    </div>
    """, unsafe_allow_html=True)

def fetch_metadata(url):
    """Get page metadata with error handling"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        title = soup.title.string if soup.title else url
        description = soup.find('meta', attrs={'name': 'description'})
        description = description['content'] if description else ""
        
        # Try to get keywords if available
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = keywords['content'].split(',')[:5] if keywords else []
        
        return title, description, [k.strip() for k in keywords if k.strip()]
    except Exception as e:
        st.warning(f"Couldn't fetch metadata: {str(e)}")
        return url, "", []

def add_link_section(df, excel_file):
    """Section for adding new links with working Fetch button"""
    st.markdown("### 🌐 Add New Web Content")
    
    # Use session state to track URL changes
    if 'url_input' not in st.session_state:
        st.session_state.url_input = ""
    
    # URL input (outside form to allow real-time changes)
    url = st.text_input(
        "URL*", 
        placeholder="https://example.com",
        key="url_input",
        help="Enter the full URL including https://"
    )
    
    # Check if URL is non-empty and valid (basic check)
    is_url_valid = url.startswith(("http://", "https://")) if url else False
    
    # Fetch button (now enabled only if URL is valid)
    if st.button("Fetch Metadata", disabled=not is_url_valid):
        with st.spinner("Fetching..."):
            title, description, keywords = fetch_metadata(url)
            st.session_state['auto_title'] = title
            st.session_state['auto_description'] = description
            st.session_state['suggested_tags'] = keywords
            st.rerun()
    
    # The rest of the form
    with st.form("add_link_form", clear_on_submit=True):
        title = st.text_input(
            "Title*", 
            value=st.session_state.get('auto_title', ''),
            help="Give your link a descriptive title"
        )
        
        description = st.text_area(
            "Description", 
            value=st.session_state.get('auto_description', ''),
            height=100,
            help="Add notes about why this link is important"
        )
        
        # Smart tags with validation
        suggested_tags = st.session_state.get('suggested_tags', []) + \
                       ['research', 'tutorial', 'news', 'tool', 'inspiration']
        suggested_tags = [str(tag).strip() for tag in suggested_tags if str(tag).strip()]
        
        st.markdown("**Tags:** (Press Enter after each tag)")
        tags = st_tags(
            label='',
            text='Add a tag and press Enter',
            value=[],
            suggestions=list(set(suggested_tags)),
            key="tags_input"
        )
        
        submitted = st.form_submit_button("💾 Save Link")
        
        if submitted:
            if not url:
                st.error("Please enter a URL")
            elif not title:
                st.error("Please enter a title")
            else:
                df, action = save_link(df, url, title, description, tags)
                if action:
                    if save_data(df, excel_file):
                        st.success(f"✅ Link {action} successfully!")
                        st.balloons()
                        # Clear auto-filled fields
                        for key in ['auto_title', 'auto_description', 'suggested_tags']:
                            if key in st.session_state:
                                del st.session_state[key]
                        st.rerun()
    
    return df

def browse_section(df, excel_file):
    """Section for browsing saved links with powerful search and delete functionality"""
    st.markdown("### 📚 Browse Saved Links")
    
    if df.empty:
        st.info("✨ No links saved yet. Add your first link to get started!")
        return
    
    # Powerful search functionality
    search_col, tag_col = st.columns([3, 1])
    with search_col:
        search_query = st.text_input("Search content", 
                                    placeholder="Search by title, URL, description or tags")
    with tag_col:
        # Get all unique tags
        all_tags = sorted({str(tag).strip() for sublist in df['tags'] 
                         for tag in (sublist if isinstance(sublist, list) else []) 
                         if str(tag).strip()})
        selected_tags = st.multiselect("Filter by tags", options=all_tags)
    
    # Apply search filters
    filtered_df = df.copy()
    
   if search_query:
    search_lower = search_query.lower()
    mask = (
        filtered_df['title'].str.lower().str.contains(search_lower, na=False) |
        filtered_df['url'].str.lower().str.contains(search_lower, na=False) |
        filtered_df['description'].str.lower().str.contains(search_lower, na=False) |
        filtered_df['tags'].apply(
            lambda x: any(search_lower in str(tag).lower() for tag in (x if isinstance(x, list) else []))
        )
    )
    filtered_df = filtered_df[mask]
    
    if selected_tags:
        mask = filtered_df['tags'].apply(
            lambda x: any(str(tag) in map(str, (x if isinstance(x, list) else [])) 
                      for tag in selected_tags)
        )
        filtered_df = filtered_df[mask]
    
    if filtered_df.empty:
        st.warning("No links match your search criteria")
        return
    
    # Display expandable DataFrame view
    with st.expander("📊 View All Links as Data Table", expanded=False):
        display_df = filtered_df.copy()
        display_df['tags'] = display_df['tags'].apply(
            lambda x: ', '.join(str(tag) for tag in (x if isinstance(x, list) else []))
        st.dataframe(
            display_df[['title', 'url', 'tags', 'created_at']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "title": "Title",
                "url": st.column_config.LinkColumn("URL"),
                "tags": "Tags",
                "created_at": "Date Added"
            }
        )
    
    # Display individual cards with delete functionality
    for _, row in filtered_df.iterrows():
        with st.expander(f"🔗 {escape(str(row['title']))}", expanded=False):
            st.markdown(f"""
            <div class="card">
                <p><strong>URL:</strong> <a href="{escape(str(row['url']))}" target="_blank">{escape(str(row['url']))}</a></p>
                <p><strong>Description:</strong> {escape(str(row['description'])) if pd.notna(row['description']) else 'No description available'}</p>
                <div style="margin-top: 0.5rem;">
                    {format_tags(row['tags'])}
                </div>
                <p style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
                    <strong>Added:</strong> {escape(str(row['created_at']))} | 
                    <strong>Updated:</strong> {escape(str(row['updated_at']))}
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            # Delete button
            if st.button("🗑️ Delete Link", key=f"delete_{row['url']}", 
                        on_click=lambda u=row['url']: delete_link(df, excel_file, u)):
                st.rerun()

def format_tags(tags):
    """Format tags as pretty pills"""
    if not tags or (isinstance(tags, float) and pd.isna(tags):
        return ""
    
    if isinstance(tags, str):
        tags = tags.split(',')
    
    html_tags = []
    for tag in tags:
        if tag and str(tag).strip():
            html_tags.append(f"""
            <span class="tag">
                {escape(str(tag).strip())}
            </span>
            """)
    return "".join(html_tags)

def download_section(df, excel_file):
    """Section for downloading data"""
    st.markdown("### 📥 Export Your Links")
    
    if df.empty:
        st.warning("No links available to export")
        return
    
    with st.container():
        st.markdown("""
        <div class="card">
            <h3>Export Options</h3>
            <p>Download your saved links in different formats</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            # Excel download
            with open(excel_file, 'rb') as f:
                st.download_button(
                    label="Download Excel",
                    data=f,
                    file_name="web_links.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download all links in Excel format"
                )
        with col2:
            # CSV download
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="web_links.csv",
                mime="text/csv",
                help="Download all links in CSV format"
            )
        
        # Display stats
        st.markdown(f"""
        <div style="margin-top: 1rem;">
            <p><strong>Stats:</strong> {len(df)} links saved | {len(set(tag for sublist in df['tags'] for tag in (sublist if isinstance(sublist, list) else [])))} unique tags</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    # Display header
    display_header()
    
    # Initialize data
    if 'df' not in st.session_state:
        df, excel_file = init_data()
        st.session_state['df'] = df
        st.session_state['excel_file'] = excel_file
    else:
        df = st.session_state['df']
        excel_file = st.session_state['excel_file']
    
    # About section
    with st.expander("ℹ️ About Web Content Manager", expanded=False):
        st.markdown("""
        <div style="padding: 1rem;">
            <h3>Your Personal Web Library</h3>
            <p>Web Content Manager helps you save and organize web links with:</p>
            <ul>
                <li>📌 One-click saving of important web resources</li>
                <li>🏷️ <strong>Smart tagging</strong> - Automatically suggests tags from page metadata</li>
                <li>🔍 <strong>Powerful search</strong> - Full-text search across all fields with tag filtering</li>
                <li>🗑️ <strong>Delete functionality</strong> - Remove unwanted links</li>
                <li>📊 <strong>Data Table View</strong> - See all links in a sortable, filterable table</li>
                <li>📥 <strong>Export capability</strong> - Download your collection in Excel or CSV format</li>
                <li>💾 <strong>Persistent storage</strong> - Your data is saved automatically and persists between sessions</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem;">
            <h2 style="margin-bottom: 1.5rem;">Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        
        selected = option_menu(
            menu_title=None,
            options=["Add Link", "Browse Links", "Export Data"],
            icons=['plus-circle', 'book', 'download'],
            default_index=0,
            styles={
                "container": {"padding": "0!important"},
                "icon": {"color": "#6e8efb", "font-size": "1rem"}, 
                "nav-link": {"font-size": "1rem", "text-align": "left", "margin": "0.5rem 0", "padding": "0.5rem 1rem"},
                "nav-link-selected": {"background-color": "#6e8efb", "font-weight": "normal"},
            }
        )
    
    # Render selected section
    if selected == "Add Link":
        updated_df = add_link_section(df, excel_file)
        st.session_state['df'] = updated_df
    elif selected == "Browse Links":
        browse_section(df, excel_file)
    elif selected == "Export Data":
        download_section(df, excel_file)

if __name__ == "__main__":
    main()
