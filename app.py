import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz

# Set page config
st.set_page_config(
    page_title="Fact Checking Dashboard",
    page_icon="🔍",
    layout="wide"
)

# Load data
@st.cache_data
def load_data():
    # Load posts with cluster information
    posts_df = pd.read_csv('posts.csv')
    clusters_df = pd.read_csv('clusters.csv')
    
    # Convert timestamp strings to datetime objects
    posts_df['timestamp'] = pd.to_datetime(posts_df['timestamp'])
    
    return posts_df, clusters_df

posts_df, clusters_df = load_data()

# Title
st.title("🔍 Fact Checking Dashboard")

# Date filter in sidebar
st.sidebar.header("Time Range Filter")
time_filter = st.sidebar.radio(
    "Select time range:",
    ["All Time", "Last 24 Hours", "Last 7 Days", "Last 30 Days", "Last Year"],
    key="time_filter"
)

# Calculate the date filter based on selection
reference_date = datetime(2025, 4, 4)  # Set to April 4, 2025
if time_filter == "Last 24 Hours":
    date_threshold = reference_date - timedelta(days=1)
elif time_filter == "Last 7 Days":
    date_threshold = reference_date - timedelta(days=7)
elif time_filter == "Last 30 Days":
    date_threshold = reference_date - timedelta(days=30)
elif time_filter == "Last Year":
    date_threshold = reference_date - timedelta(days=365)
else:  # All Time
    date_threshold = datetime.min

# Apply date filter to posts
filtered_posts_df = posts_df[posts_df['timestamp'] >= date_threshold]

# Create tabs
tab1, tab2 = st.tabs(["Simple Fact Checking", "Cluster Based Fact Checking"])

# Tab 1: Simple Fact Checking
with tab1:
    st.header("Social Media Posts")
    
    # Search functionality
    search_term = st.text_input("Search posts by content:", key="simple_search")
    
    # Filter posts based on search
    if search_term:
        display_posts = filtered_posts_df[filtered_posts_df['content'].str.contains(search_term, case=False, na=False)]
    else:
        display_posts = filtered_posts_df
    
    # Pagination
    items_per_page = 50
    total_items = len(display_posts)
    total_pages = (total_items - 1) // items_per_page + 1
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        current_page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, key="page_number")
    
    start_idx = (current_page - 1) * items_per_page
    end_idx = min(start_idx + items_per_page, total_items)
    
    # Display page info
    st.write(f"Showing {start_idx + 1} to {end_idx} of {total_items} posts")
    
    # Display posts for current page
    display_cols = [col for col in display_posts.columns if col != 'cluster_id']
    st.table(display_posts.iloc[start_idx:end_idx][display_cols])

# Tab 2: Cluster Based Fact Checking
with tab2:
    st.header("Fact Checking Clusters")
    
    # Update cluster metrics based on filtered data
    for _, cluster in clusters_df.iterrows():
        cluster_posts = filtered_posts_df[filtered_posts_df['cluster_id'] == cluster['cluster_id']]
        current_cluster_count = len(cluster_posts)
        current_cluster_engagement = int(cluster_posts['engagement_score'].mean()) if not cluster_posts.empty else 0
        
        with st.expander(f"📊 {cluster['cluster_name']} (Urgency: {cluster['urgency']})"):
            # Display cluster information
            st.markdown(f"**Summary:** {cluster['summary']}")
            
            # Metrics in columns with current period stats
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Amplifiability", cluster['amplifiability'])
            with col2:
                st.metric("Believability", cluster['believability'])
            with col3:
                st.metric("Posts in Period", current_cluster_count)
            with col4:
                st.metric("Current Avg. Engagement", f"{current_cluster_engagement:,}")
            
            # Button to show posts in this cluster
            if st.button(f"View Posts in Cluster {cluster['cluster_id']}", key=f"btn_{cluster['cluster_id']}"):
                # Get posts for this cluster from filtered data
                cluster_posts = filtered_posts_df[filtered_posts_df['cluster_id'] == cluster['cluster_id']]
                
                # Create a modal-like effect with a container
                with st.container():
                    st.subheader(f"Posts in {cluster['cluster_name']}")
                    display_cols = [col for col in cluster_posts.columns if col != 'cluster_id']
                    st.table(cluster_posts[display_cols]) 