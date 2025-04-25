# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Enhanced Version with Owner Mode and Persistent Storage
"""
import streamlit as st
import pandas as pd
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from streamlit_option_menu import option_menu
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
    
    .dataframe {
        width: 100%;
    }
    
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
    
    .delete-btn {
        background-color: #ff4b4b !important;
        color: white !important;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

def init_data():
    """Initialize or load Excel files for public links"""
    public_excel_file = 'public_links.xlsx'
    try:
        if os.path.exists(public_excel_file):
            df = pd.read_excel(public_excel_file, engine='openpyxl')
            if 'tags' in df.columns:
                df['tags'] = df['tags'].apply(lambda x: x.split(',') if isinstance(x, str) else [] if pd.isna(x) else x)
            for col in ['title', 'url', 'description']:
                if col in df.columns:
                    df[col] = df[col].astype(str).replace('nan', '')
            df['source'] = 'Public'
            logging.info("Loaded public Excel file")
        else:
            df = pd.DataFrame(columns=[
                'id', 'url', 'title', 'description', 'tags', 
                'created_at', 'updated_at', 'source'
            ])
            logging.info("Created empty public Excel file")
        return df, public_excel_file
    except Exception as e:
        st.error(f"Failed to initialize public data: {str(e)}")
        logging.error(f"Public data initialization failed: {str(e)}")
        return pd.DataFrame(), public_excel_file

def save_data(df, excel_file):
    """Save DataFrame to Excel file"""
    try:
        logging.debug(f"Saving DataFrame to {excel_file}: {df.to_dict()}")
        df_to_save = df.copy()
        if 'tags' in df_to_save.columns:
            df_to_save['tags'] = df_to_save['tags'].apply(lambda x: ','.join(map(str, x)) if isinstance(x, list) else '')
        if 'source' in df_to_save.columns:
            df_to_save = df_to_save.drop(columns=['source'])
        
        if os.path.exists(excel_file):
            if not os.access(excel_file, os.W_OK):
                raise PermissionError(f"No write permission for {excel_file}")
        else:
            directory = os.path.dirname(excel_file) or '.'
            if not os.access(directory, os.W_OK):
                raise PermissionError(f"No write permission for directory {directory}")
        
        df_to_save.to_excel(excel_file, index=False, engine='openpyxl')
        logging.info("Data saved successfully")
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        logging.error(f"Data save failed: {str(e)}")
        return False

def save_link(df, url, title, description, tags, source='User'):
    """Save or update a link in the DataFrame"""
    try:
        logging.debug(f"Saving link: URL={url}, Title={title}, Description={description}, Tags={tags}, Source={source}")
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        existing_index = df[df['url'] == url].index
        
        if not existing_index.empty:
            st.warning(f"URL already exists: {url}. Updating existing entry.")
            idx = existing_index[0]
            df.at[idx, 'title'] = title
            df.at[idx, 'description'] = description if description else ""
            df.at[idx, 'tags'] = [str(tag).strip() for tag in tags if str(tag).strip()]
            df.at[idx, 'updated_at'] = now
            df.at[idx, 'source'] = source
            action = "updated"
        else:
            new_id = df['id'].max() + 1 if not df.empty else 1
            new_entry = {
                'id': new_id,
                'url': url,
                'title': title,
                'description': description if description else "",
                'tags': [str(tag).strip() for tag in tags if str(tag).strip()],
                'created_at': now,
                'updated_at': now,
                'source': source
            }
            df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
            action = "saved"
        
        logging.info(f"Link {action} successfully")
        return df, action
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")
        logging.error(f"Link save failed: {str(e)}")
        return df, None

def delete_selected_links(public_df, user_df, public_excel_file, selected_urls, owner_mode):
    """Delete selected links from the appropriate DataFrame"""
    try:
        logging.debug(f"Deleting URLs: {selected_urls}, Owner Mode: {owner_mode}")
        if not selected_urls:
            st.warning("No links selected for deletion")
            return public_df, user_df
        
        if owner_mode:
            # Owner can delete from both public and user DataFrames
            public_df = public_df[~public_df['url'].isin(selected_urls)]
            user_df = user_df[~user_df['url'].isin(selected_urls)]
            # Save public_df changes to file
            if public_df['source'].eq('Public').any():
                if not save_data(public_df, public_excel_file):
                    st.error("Failed to save public links after deletion")
        else:
            # Public users can only delete from user_df
            user_df = user_df[~user_df['url'].isin(selected_urls)]
        
        st.session_state['public_df'] = public_df
        st.session_state['user_df'] = user_df
        st.success(f"✅ {len(selected_urls)} link(s) deleted successfully!")
        st.balloons()
        return public_df, user_df
    except Exception as e:
        st.error(f"Error deleting links: {str(e)}")
        logging.error(f"Delete links failed: {str(e)}")
        return public_df, user_df

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
        
        keywords = soup.find('meta', attrs={'name': 'keywords'})
        keywords = keywords['content'].split(',')[:5] if keywords else []
        
        return title, description, [k.strip() for k in keywords if k.strip()]
    except Exception as e:
        st.warning(f"Couldn't fetch metadata: {str(e)}")
        return url, "", []

def add_link_section(public_df, public_excel_file, owner_mode):
    """Section for adding new links with working Fetch button"""
    st.markdown("### 🌐 Add New Web Content")
    
    # Initialize user DataFrame in session state
    if 'user_df' not in st.session_state:
        st.session_state['user_df'] = pd.DataFrame(columns=[
            'id', 'url', 'title', 'description', 'tags', 
            'created_at', 'updated_at', 'source'
        ])
    
    user_df = st.session_state['user_df']
    
    # URL input
    url = st.text_input(
        "URL*", 
        placeholder="https://example.com",
        key="url_input",
        help="Enter the full URL including https://"
    )
    
    is_url_valid = url.startswith(("http://", "https://")) if url else False
    
    if st.button("Fetch Metadata", disabled=not is_url_valid, key="fetch_metadata"):
        with st.spinner("Fetching..."):
            title, description, keywords = fetch_metadata(url)
            st.session_state['auto_title'] = title
            st.session_state['auto_description'] = description
            st.session_state['suggested_tags'] = keywords
    
    with st.form("add_link_form", clear_on_submit=True):
        title = st.text_input(
            "Title*", 
            value=st.session_state.get('auto_title', ''),
            help="Give your link a descriptive title",
            key="title_input"
        )
        
        description = st.text_area(
            "Description", 
            value=st.session_state.get('auto_description', ''),
            height=100,
            help="Add notes about why this link is important",
            key="description_input"
        )
        
        # Get all unique tags from public and user DataFrames
        all_tags = sorted({str(tag).strip() for sublist in public_df['tags'] 
                         for tag in (sublist if isinstance(sublist, list) else []) 
                         if str(tag).strip()})
        all_tags += sorted({str(tag).strip() for sublist in user_df['tags'] 
                          for tag in (sublist if isinstance(sublist, list) else []) 
                          if str(tag).strip()})
        suggested_tags = st.session_state.get('suggested_tags', []) + \
                       ['research', 'tutorial', 'news', 'tool', 'inspiration']
        all_tags = sorted(list(set(all_tags + [str(tag).strip() for tag in suggested_tags if str(tag).strip()])))
        
        selected_tags = st.multiselect(
            "Tags",
            options=all_tags,
            default=[],
            help="Select existing tags or add new ones below. Example: For a Python tutorial, use tags like 'python', 'tutorial', 'programming'.",
            key="existing_tags"
        )
        
        new_tag = st.text_input(
            "Add New Tag (optional)",
            placeholder="Type a new tag and press Enter",
            help="Enter a new tag to add to the selected tags",
            key="new_tag"
        )
        
        tags = selected_tags + ([new_tag.strip()] if new_tag.strip() else [])
        
        submitted = st.form_submit_button("💾 Save Link")
        
        if submitted:
            logging.debug(f"Form submitted: URL={url}, Title={title}, Description={description}, Tags={tags}, Owner Mode={owner_mode}")
            if not url:
                st.error("Please enter a URL")
            elif not title:
                st.error("Please enter a title")
            else:
                if owner_mode:
                    # Save to public_df and public_links.xlsx
                    public_df, action = save_link(public_df, url, title, description, tags, source='Public')
                    if action:
                        if save_data(public_df, public_excel_file):
                            st.session_state['public_df'] = public_df
                            st.success(f"✅ Link {action} successfully!")
                            st.balloons()
                            # Clear session state
                            for key in ['url_input', 'auto_title', 'auto_description', 'suggested_tags', 
                                      'title_input', 'description_input', 'existing_tags', 'new_tag']:
                                if key in st.session_state:
                                    del st.session_state[key]
                        else:
                            st.error("Failed to save link to public Excel file")
                    else:
                        st.error("Failed to process link")
                else:
                    # Save to user_df
                    user_df, action = save_link(user_df, url, title, description, tags, source='User')
                    if action:
                        st.session_state['user_df'] = user_df
                        st.success(f"✅ Link {action} successfully!")
                        st.balloons()
                        # Clear session state
                        for key in ['url_input', 'auto_title', 'auto_description', 'suggested_tags', 
                                  'title_input', 'description_input', 'existing_tags', 'new_tag']:
                            if key in st.session_state:
                                del st.session_state[key]
                    else:
                        st.error("Failed to process link")
    
    # Download user links (public users only)
    if not owner_mode and not user_df.empty:
        user_csv = user_df.drop(columns=['source']).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Your Links as CSV",
            data=user_csv,
            file_name="user_links.csv",
            mime="text/csv",
            help="Download your saved links as a CSV file",
            key="download_user_csv"
        )
    
    return public_df, user_df

def browse_section(public_df, public_excel_file, owner_mode):
    """Section for browsing saved links with powerful search and delete functionality"""
    st.markdown("### 📚 Browse Saved Links")
    
    user_df = st.session_state.get('user_df', pd.DataFrame(columns=[
        'id', 'url', 'title', 'description', 'tags', 
        'created_at', 'updated_at', 'source'
    ]))
    
    combined_df = pd.concat([public_df, user_df], ignore_index=True)
    
    if combined_df.empty:
        st.info("✨ No links saved yet. Add your first link to get started!")
        return
    
    with st.form("search_form"):
        search_col, tag_col = st.columns([3, 1])
        with search_col:
            search_query = st.text_input(
                "Search content",
                placeholder="Search by title, URL, description, or tags",
                key="search_query",
                help="Enter words to filter links (e.g., part of title or tag)"
            )
        with tag_col:
            all_tags = sorted({str(tag).strip() for sublist in combined_df['tags'] 
                             for tag in (sublist if isinstance(sublist, list) else []) 
                             if str(tag).strip()})
            selected_tags = st.multiselect(
                "Filter by tags",
                options=all_tags,
                key="tag_filter",
                help="Select tags to filter links"
            )
        
        submitted = st.form_submit_button("🔍 Search")
    
    filtered_df = combined_df.copy()
    
    if search_query or submitted:
        logging.debug(f"Applying search query: {search_query}")
        search_lower = search_query.lower()
        try:
            mask = (
                filtered_df['title'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['url'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['description'].str.lower().str.contains(search_lower, na=False) |
                filtered_df['tags'].apply(
                    lambda x: any(search_lower in str(tag).lower() for tag in (x if isinstance(x, list) else []))
                )
            )
            filtered_df = filtered_df[mask]
            logging.debug(f"Search results: {len(filtered_df)} links found")
        except Exception as e:
            st.error(f"Search error: {str(e)}")
            logging.error(f"Search failed: {str(e)}")
    
    if selected_tags:
        logging.debug(f"Applying tag filter: {selected_tags}")
        try:
            mask = filtered_df['tags'].apply(
                lambda x: any(str(tag) in map(str, (x if isinstance(x, list) else [])) 
                              for tag in selected_tags)
            )
            filtered_df = filtered_df[mask]
            logging.debug(f"Tag filter results: {len(filtered_df)} links found")
        except Exception as e:
            st.error(f"Tag filter error: {str(e)}")
            logging.error(f"Tag filter failed: {str(e)}")
    
    if filtered_df.empty:
        st.warning("No links match your search criteria")
    else:
        st.markdown(f"<small>Found <strong>{len(filtered_df)}</strong> link(s)</small>", unsafe_allow_html=True)
    
    if 'selected_urls' not in st.session_state:
        st.session_state.selected_urls = []

    with st.expander("📊 View All Links as Data Table", expanded=True):
        display_df = filtered_df.copy()
        display_df['tags'] = display_df['tags'].apply(
            lambda x: ', '.join(str(tag) for tag in (x if isinstance(x, list) else [])))
        
        display_df['Select'] = [False] * len(display_df)
        for i, row in display_df.iterrows():
            display_df.at[i, 'Select'] = row['url'] in st.session_state.selected_urls and \
                                       (owner_mode or row['source'] == 'User')
        
        edited_df = st.data_editor(
            display_df[['Select', 'source', 'title', 'url', 'description', 'tags', 'created_at']],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Select": st.column_config.CheckboxColumn("Select", help="Select links to delete (public links editable in Owner Mode)"),
                "source": "Source",
                "title": "Title",
                "url": st.column_config.LinkColumn("URL"),
                "description": "Description",
                "tags": "Tags",
                "created_at": "Date Added"
            },
            disabled=['source', 'title', 'url', 'description', 'tags', 'created_at'],
            key="data_editor"
        )
        
        st.session_state.selected_urls = edited_df[edited_df['Select']]['url'].tolist()
        
        if st.session_state.selected_urls:
            if st.button("🗑️ Delete Selected Links", key="delete_selected"):
                public_df, user_df = delete_selected_links(
                    public_df, user_df, public_excel_file, st.session_state.selected_urls, owner_mode)
                st.session_state['public_df'] = public_df
                st.session_state['user_df'] = user_df
                st.session_state.selected_urls = []

def format_tags(tags):
    """Format tags as pretty pills"""
    if not tags or (isinstance(tags, float) and pd.isna(tags)):
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

def download_section(public_df, public_excel_file, owner_mode):
    """Section for downloading data"""
    st.markdown("### 📥 Export Your Links")
    
    user_df = st.session_state.get('user_df', pd.DataFrame())
    
    if user_df.empty and public_df.empty:
        st.warning("No links available to export")
        return
    
    with st.container():
        st.markdown("""
        <div class="card">
            <h3>Export Options</h3>
            <p>Download your saved links or the public collection</p>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if not public_df.empty:
                with open(public_excel_file, 'rb') as f:
                    st.download_button(
                        label="Download Public Links (Excel)",
                        data=f,
                        file_name="public_links.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        help="Download the public collection of links",
                        key="download_public_excel"
                    )
        with col2:
            if not user_df.empty and not owner_mode:
                user_csv = user_df.drop(columns=['source']).to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="Download Your Links (CSV)",
                    data=user_csv,
                    file_name="user_links.csv",
                    mime="text/csv",
                    help="Download your saved links as a CSV file",
                    key="download_user_csv_section"
                )
        
        st.markdown(f"""
        <div style="margin-top: 1rem;">
            <p><strong>Stats:</strong> {len(public_df)} public links | {len(user_df)} user links | {len(set(tag for sublist in pd.concat([public_df, user_df])['tags'] for tag in (sublist if isinstance(sublist, list) else [])))} unique tags</p>
        </div>
        """, unsafe_allow_html=True)

def main():
    display_header()
    
    if 'public_df' not in st.session_state:
        public_df, public_excel_file = init_data()
        st.session_state['public_df'] = public_df
        st.session_state['public_excel_file'] = public_excel_file
    else:
        public_df = st.session_state['public_df']
        public_excel_file = st.session_state['public_excel_file']
    
    # Owner Mode toggle
    with st.sidebar:
        st.markdown("""
        <div style="padding: 1rem;">
            <h2 style="margin-bottom: 1.5rem;">Navigation</h2>
        </div>
        """, unsafe_allow_html=True)
        
        owner_mode = st.checkbox("Owner Mode", help="Enable to save links persistently and edit public links")
        
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
    
    with st.expander("ℹ️ About Web Content Manager", expanded=False):
        st.markdown("""
        <div style="padding: 1rem;">
            <h3>Your Personal Web Library</h3>
            <p>Web Content Manager helps you save and organize web links with:</p>
            <ul>
                <li>📌 One-click saving of important web resources</li>
                <li>🏷️ <strong>Smart tagging</strong> - Automatically suggests tags from page metadata</li>
                <li>🔍 <strong>Powerful search</strong> - Full-text search across all fields with tag filtering</li>
                <li>🗑️ <strong>Delete functionality</strong> - Remove your links (public links editable in Owner Mode)</li>
                <li>📊 <strong>Data Table View</strong> - See all links in a sortable, filterable table</li>
                <li>📥 <strong>Export capability</strong> - Download your collection or the public collection</li>
                <li>💾 <strong>Persistent storage</strong> - Owner links saved permanently; public user links exportable</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    if selected == "Add Link":
        public_df, user_df = add_link_section(public_df, public_excel_file, owner_mode)
        st.session_state['public_df'] = public_df
        st.session_state['user_df'] = user_df
    elif selected == "Browse Links":
        browse_section(public_df, public_excel_file, owner_mode)
    elif selected == "Export Data":
        download_section(public_df, public_excel_file, owner_mode)

if __name__ == "__main__":
    main()
