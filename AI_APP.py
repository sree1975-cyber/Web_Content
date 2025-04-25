# -*- coding: utf-8 -*-
"""
WEB CONTENT MANAGER - Main App
Home page for the web content manager application.
"""
import streamlit as st

# Set page configuration (MUST be the first Streamlit command)
st.set_page_config(
    page_title="Web Content Manager",
    page_icon="🔖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display header
def display_header():
    """Display beautiful header with placeholder image"""
    header_html = """
    <div style="background-color:#4b8bbe;padding:10px;border-radius:10px">
        <h1 style="color:white;text-align:center;">🔖 Web Content Manager</h1>
        <p style="color:white;text-align:center;">Save, organize and rediscover your web treasures</p>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)

# Main function
def main():
    display_header()
    
    st.write("""
    **Welcome to Web Content Manager!**  
    Use the sidebar to:
    - Add new web links with AI-powered tagging
    - Browse your saved links
    - Search using semantic analysis
    - Manage tags
    - Adjust settings
    """)
    
    with st.expander("ℹ️ About this app", expanded=False):
        st.write("""
        **Web Content Manager** helps you save and organize web links with:
        - AI-powered tagging and search
        - Visual bookmark management
        - Semantic content analysis
        - Beautiful intuitive interface
        
        Navigate using the sidebar menu to get started!
        """)

if __name__ == "__main__":
    main()
