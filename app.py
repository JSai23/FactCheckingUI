import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client
import json
from st_aggrid import AgGrid, GridOptionsBuilder, JsCode
from parsers import parse_display_output
import re

# Initialize Supabase client
supabase_url = st.secrets["supabase_url"]
supabase_key = st.secrets["supabase_key"]
supabase = create_client(supabase_url, supabase_key)

# Set page config
st.set_page_config(
    page_title="ClaimFinder",
    page_icon="🔍",
    layout="wide"
)

# Session state initialization
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None

# Login page
def show_login():
    st.title("🔍 ClaimFinder")
    st.header("Login")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Login")
        
        if submit:
            # Demo login - accept any non-empty username/password
            if username and password:
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Please enter both username and password")

# Main application
def show_main_app():
    # Title
    st.title("🔍 ClaimFinder")
    
    # Load and parse data
    parsed_data = parse_display_output("newRealData/display_output.csv")
    
    # User info in sidebar
    st.sidebar.header("User Information")
    st.sidebar.text(f"Logged in as: {st.session_state.username}")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = None
        st.rerun()
    
    # Date filter in sidebar
    st.sidebar.header("Time Range Filter")
    time_filter = st.sidebar.radio(
        "Select time range:",
        ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last Year"]
    )
    
    # Create tabs
    tab1, tab2 = st.tabs(["All Posts", "AI-Sourced Posts"])
    
    # Tab 1: All Posts
    with tab1:
        st.header("Social Media Posts")
        
        # Search functionality
        search_term = st.text_input("Search posts by content:", key="simple_search")
        
        # Prepare data for display
        posts_data = []
        for _, post in parsed_data:
            raw_id = str(post.post_id)
            # Strip common synthetic prefixes (e.g., original_ngt_, generated_gt_)
            raw_id = re.sub(r"^(original_ngt_|generated_gt_)", "", raw_id)
            # Extract numeric portion of the post ID (fallback to raw if no match)
            match = re.search(r"\d{5,}", raw_id)  # long numeric chunk
            clean_id = match.group(0) if match else raw_id

            # Prefer user_handle, fallback to user_name, else 'anyuser'
            handle = getattr(post, 'user_handle', None) or getattr(post, 'user_name', None) or 'anyuser'
            # Remove spaces or invalid URL characters from handle
            handle = re.sub(r"[^A-Za-z0-9_]+", "", str(handle))

            url = f"https://x.com/{handle}/status/{clean_id}"
            posts_data.append({
                'post_url': url,
                'date': post.user_created,
                'content': post.text,
                'retweets': post.retweets,
                'favorites': post.favorites,
                'user_name': post.user_name,
                'user_created': post.user_created,
                'followers': post.user_followers,
                'friends': post.user_friends
            })
        
        posts_df = pd.DataFrame(posts_data)
        
        # Filter based on search
        if search_term:
            posts_df = posts_df[posts_df['content'].str.contains(search_term, case=False, na=False)]
        
        # Configure grid
        gb = GridOptionsBuilder.from_dataframe(posts_df)
        gb.configure_column('post_url', header_name='Post URL')
        gb.configure_column('date', header_name='Date')
        gb.configure_column('content', header_name='Content')
        gb.configure_column('retweets', header_name='Retweets')
        gb.configure_column('favorites', header_name='Favorites')
        gb.configure_column('user_name', header_name='User Name')
        gb.configure_column('user_created', header_name='Account Created')
        gb.configure_column('followers', header_name='Followers')
        gb.configure_column('friends', header_name='Following')
        
        gb.configure_default_column(resizable=True, filterable=True)
        grid_options = gb.build()
        
        AgGrid(
            posts_df,
            gridOptions=grid_options,
            height=600,
            width='100%',
            allow_unsafe_jscode=True
        )
    
    # Tab 2: AI-Sourced Posts
    with tab2:
        st.header("AI-Analyzed Claims")
        
        # Show only posts with priority_score > 0.6 and sort by priority_score descending
        ai_posts = [(pres, post) for pres, post in parsed_data if getattr(post, 'priority_score', 0) > 0.6]
        ai_posts.sort(key=lambda x: -x[1].priority_score)
        
        for presentation, post in ai_posts:
            with st.expander(f"{presentation.title} (Priority: {post.priority_score:.2f})"):
                # Create two columns for the layout
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.markdown("### Key Findings")
                    for finding in presentation.key_findings.findings:
                        st.markdown(f"**{finding.type}**")
                        st.markdown(f"- {finding.description}")
                    
                    st.markdown("### Recommended Actions")
                    for action in presentation.recommended_actions.recommendations:
                        st.markdown(f"**Action:** {action.action}")
                        st.markdown(f"*Rationale:* {action.rationale}")
                
                with col2:
                    st.markdown("### Post Details")
                    st.markdown(f"**Urgency:** {post.max_urgency}")
                    st.markdown(f"**Amplifiability:** {post.max_amplifiability}")
                    st.markdown(f"**Claims Found:** {post.num_claims}")
                    st.markdown(f"**Engagement:**")
                    st.markdown(f"- Retweets: {post.retweets}")
                    st.markdown(f"- Favorites: {post.favorites}")
                    
                st.markdown("### Original Post")
                st.markdown(f"*{post.text}*")
                st.markdown(f"Posted by: **{post.user_name}**")

# Main flow
if not st.session_state.logged_in:
    show_login()
else:
    show_main_app() 