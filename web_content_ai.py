# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER
A single-page application to save and organize web links with AI-powered features.
"""
import streamlit as st
import pandas as pd
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
    img = Image.new('RGB', (400, 200), color='#4b8bbe')  # Reduced size
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

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
    """Display header aligned to the right with smaller image"""
    header_html = f"""
    <div style="background-color:#4b8bbe;padding:10px;border-radius:10px;width:50%;float:right;margin-left:auto;margin-bottom:20px;">
        <h1 style="color:white;text-align:right;font-size:24px;">🔖 Web Content Manager</h1>
        <p style="color:white;text-align:right;font-size:14px;">Save, organize and rediscover your web treasures</p>
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
    """Load sentence transformer model with error handling (kept for potential future use)"""
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

def add_link_section(df, excel_file):
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
        updated_df = save_link(df, excel_file, url, title, description, tags)
        return updated_df
    return df

def browse_section(df):
    """Section for browsing saved links"""
    st.subheader("📚 Browse Saved Links")
    
    try:
        if df.empty:
            st.info("No links saved yet. Add a link to get started!")
            return
        
        for _, row in df.iterrows():
            with st.expander(f"{row['title'] or row['url']} (Saved: {row['created_at']})"):
                st.markdown(f"**URL**: {row['url']}")
                st.markdown(f"**Description**: {row['description'] or 'No description'}")
                tags = row['tags'].split(',') if row['tags'] else []
                st.markdown(f"**Tags**: {', '.join(tags) if tags else 'None'}")
    except Exception as e:
        st.error(f"Error fetching links: {str(e)}")
        logging.error(f"Error fetching links: {str(e)}")

def download_excel(excel_file):
    """Provide a download button for the Excel file"""
    try:
        with open(excel_file, 'rb') as f:
            st.download_button(
                label="📥 Download Links (Excel)",
                data=f,
                file_name="links.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    except Exception as e:
        st.error(f"Error preparing download: {str(e)}")
        logging.error(f"Error preparing download: {str(e)}")

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
    df, excel_file = init_data()
    model = load_model()  # Kept for potential future use
    
    if df is None or excel_file is None:
        return
    
    # Sidebar navigation
    with st.sidebar:
        selected = option_menu(
            "Main Menu",
            ["Add Link", "Browse", "Download"],
            icons=['plus-circle', 'book', 'download'],
            default_index=0
        )
    
    # Render selected section
    if selected == "Add Link":
        updated_df = add_link_section(df, excel_file)
        st.session_state['df'] = updated_df  # Update session state
    elif selected == "Browse":
        browse_section(st.session_state.get('df', df))
    elif selected == "Download":
        st.subheader("📥 Download Links")
        download_excel(excel_file)
    
if __name__ == "__main__":
    main()
