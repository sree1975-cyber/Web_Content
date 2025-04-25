# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Enhanced Version
A beautiful single-page application to save and organize web links.
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

# Set up logging
logging.basicConfig(level=logging.DEBUG)

# Set page configuration (MUST be the first Streamlit command)
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for styling
st.markdown("""
<style>
    /* Main container styling */
    .stApp {
        background-color: #f8f9fa;
    }
    
    /* Header styling */
    .header {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white;
        padding: 2rem;
        border-radius: 10px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    /* Card styling */
    .card {
        background: white;
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s;
    }
    
    .card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    
    /* Button styling */
    .stButton>button {
        background: linear-gradient(135deg, #6e8efb, #a777e3);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    .stButton>button:hover {
        background: linear-gradient(135deg, #5a7df4, #9666d8);
        color: white;
    }
    
    /* Input field styling */
    .stTextInput>div>div>input, 
    .stTextArea>div>div>textarea {
        border-radius: 8px;
        border: 1px solid #e0e0e0;
    }
    
    /* Tag input styling */
    .stTags {
        border-radius: 8px;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        font-size: 1.1rem;
        font-weight: 600;
        color: #4a4a4a;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        background-color: #f8f9fa;
        border-right: 1px solid #e0e0e0;
    }
    
    /* Success message */
    .stAlert {
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def init_data():
    """Initialize or load Excel file for storing links"""
    excel_file = 'links.xlsx'
    try:
        if os.path.exists(excel_file):
            df = pd.read_excel(excel_file, engine='openpyxl')
            logging.info("Loaded existing Excel file")
        else:
            df = pd.DataFrame(columns=[
                'id', 'url', 'title', 'description', 'tags', 
                'created_at', 'updated_at'
            ])
            df.to_excel(excel_file, index=False, engine='openpyxl')
            logging.info("Created new Excel file")
        return df, excel_file
    except Exception as e:
        st.error(f"Failed to initialize Excel file: {str(e)}")
        logging.error(f"Failed to initialize Excel file: {str(e)}")
        return None, None

def save_link(df, excel_file, url, title, description, tags):
    """Save link to Excel file"""
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Check if URL already exists
        if url in df['url'].values:
            df = df[df['url'] != url]  # Remove existing entry
        
        # Create new entry
        new_id = df['id'].max() + 1 if not df.empty else 1
        new_entry = pd.DataFrame([{
            'id': new_id,
            'url': url,
            'title': title,
            'description': description,
            'tags': ','.join(tags),
            'created_at': now,
            'updated_at': now
        }])
        
        # Append and save to Excel
        df = pd.concat([df, new_entry], ignore_index=True)
        df.to_excel(excel_file, index=False, engine='openpyxl')
        
        logging.info(f"Link saved to Excel: {url}")
        st.success("✅ Link saved successfully!")
        st.balloons()
        
        # Clear session state
        if 'auto_title' in st.session_state:
            del st.session_state['auto_title']
        if 'auto_description' in st.session_state:
            del st.session_state['auto_description']
        
        return df
    except Exception as e:
        st.error(f"Error saving link: {str(e)}")
        logging.error(f"Error saving link: {str(e)}")
        return df

def display_header():
    """Display beautiful header with gradient background"""
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

def add_link_section(df, excel_file):
    """Section for adding new links with beautiful card layout"""
    with st.container():
        st.markdown("### 🌐 Add New Web Content")
        with st.form("add_link_form"):
            col1, col2 = st.columns([3, 1])
            with col1:
                url = st.text_input("URL*", placeholder="https://example.com", help="Enter the full URL including https://")
            with col2:
                st.write("")
                st.write("")
                if st.form_submit_button("Fetch Metadata", disabled=not url):
                    with st.spinner("Fetching..."):
                        title, description = fetch_metadata(url)
                        st.session_state['auto_title'] = title
                        st.session_state['auto_description'] = description
            
            title = st.text_input("Title*", value=st.session_state.get('auto_title', ''), 
                                help="Give your link a descriptive title")
            description = st.text_area("Description", value=st.session_state.get('auto_description', ''), 
                                     height=100, help="Add notes about why this link is important")
            
            tags = st_tags(
                label='Tags:',
                text='Press enter to add',
                value=[],
                suggestions=['research', 'tutorial', 'news', 'tool', 'inspiration'],
                help="Add tags to help with organization"
            )
            
            submitted = st.form_submit_button("💾 Save Link")
            if submitted and url:
                updated_df = save_link(df, excel_file, url, title, description, tags)
                return updated_df
    return df

def browse_section(df):
    """Section for browsing saved links with beautiful cards"""
    st.markdown("### 📚 Browse Saved Links")
    
    try:
        if df.empty:
            st.info("✨ No links saved yet. Add your first link to get started!")
            return
        
        # Search and filter functionality
        search_col, filter_col = st.columns([3, 1])
        with search_col:
            search_query = st.text_input("Search links", placeholder="Search by title, URL, or tags")
        with filter_col:
            tag_filter = st.multiselect("Filter by tags", options=get_all_tags(df))
        
        # Apply filters
        filtered_df = df.copy()
        if search_query:
            mask = (filtered_df['title'].str.contains(search_query, case=False, na=False)) | \
                   (filtered_df['url'].str.contains(search_query, case=False, na=False)) | \
                   (filtered_df['tags'].str.contains(search_query, case=False, na=False))
            filtered_df = filtered_df[mask]
        
        if tag_filter:
            mask = filtered_df['tags'].apply(lambda x: any(tag in x for tag in tag_filter))
            filtered_df = filtered_df[mask]
        
        if filtered_df.empty:
            st.warning("No links match your search criteria")
            return
        
        # Display cards
        for _, row in filtered_df.iterrows():
            with st.container():
                st.markdown(f"""
                <div class="card">
                    <h3>{row['title'] or row['url']}</h3>
                    <p><a href="{row['url']}" target="_blank">{row['url']}</a></p>
                    <p>{row['description'] or 'No description available'}</p>
                    <div style="margin-top: 0.5rem;">
                        {format_tags(row['tags'])}
                    </div>
                    <p style="font-size: 0.8rem; color: #666; margin-top: 0.5rem;">
                        Saved on: {row['created_at']}
                    </p>
                </div>
                """, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error fetching links: {str(e)}")
        logging.error(f"Error fetching links: {str(e)}")

def get_all_tags(df):
    """Get all unique tags from the dataframe"""
    try:
        all_tags = set()
        for tags in df['tags'].dropna():
            all_tags.update(tag.strip() for tag in tags.split(','))
        return sorted(all_tags)
    except:
        return []

def format_tags(tag_string):
    """Format tags as pretty pills"""
    if not tag_string or pd.isna(tag_string):
        return ""
    
    tags = tag_string.split(',')
    html_tags = []
    for tag in tags:
        if tag.strip():
            html_tags.append(f"""
            <span style="display: inline-block;
                         background: #e0e7ff;
                         color: #4f46e5;
                         padding: 0.2rem 0.5rem;
                         border-radius: 1rem;
                         font-size: 0.8rem;
                         margin-right: 0.5rem;
                         margin-bottom: 0.3rem;">
                {tag.strip()}
            </span>
            """)
    return "".join(html_tags)

def download_excel(excel_file):
    """Provide a download button for the Excel file"""
    try:
        st.markdown("### 📥 Export Your Links")
        with st.container():
            st.markdown("""
            <div class="card">
                <h3>Export Data</h3>
                <p>Download all your saved links as an Excel file for backup or analysis.</p>
            </div>
            """, unsafe_allow_html=True)
            
            with open(excel_file, 'rb') as f:
                st.download_button(
                    label="Download Excel File",
                    data=f,
                    file_name="my_web_links.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    help="Download all your saved links in Excel format"
                )
    except Exception as e:
        st.error(f"Error preparing download: {str(e)}")
        logging.error(f"Error preparing download: {str(e)}")

# Main function
def main():
    # Display beautiful header
    display_header()
    
    # About section
    with st.expander("ℹ️ About Web Content Manager", expanded=False):
        st.markdown("""
        <div style="padding: 1rem;">
            <h3>Your Personal Web Library</h3>
            <p>Web Content Manager helps you save and organize web links with:</p>
            <ul>
                <li>📌 One-click saving of important web resources</li>
                <li>🏷️ Smart tagging for easy organization</li>
                <li>🔍 Powerful search to rediscover your links</li>
                <li>📥 Export capability for backup and analysis</li>
            </ul>
            <p>Get started by adding your first link!</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Initialize components
    df, excel_file = init_data()
    
    if df is None or excel_file is None:
        return
    
    # Sidebar navigation with icons
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
        st.session_state['df'] = updated_df  # Update session state
    elif selected == "Browse Links":
        browse_section(st.session_state.get('df', df))
    elif selected == "Export Data":
        download_excel(excel_file)
    
if __name__ == "__main__":
    main()
