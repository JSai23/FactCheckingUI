import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client
import json

# Initialize Supabase client
supabase_url = st.secrets["supabase_url"]
supabase_key = st.secrets["supabase_key"]
supabase = create_client(supabase_url, supabase_key)

# Set page config
st.set_page_config(
    page_title="Fact Checking Dashboard",
    page_icon="🔍",
    layout="wide"
)

# Load data from Supabase
@st.cache_data
def load_data():
    # Load posts with cluster information
    posts_response = supabase.table('posts').select('*').execute()
    posts_df = pd.DataFrame(posts_response.data)
    
    clusters_response = supabase.table('cluster_presentations').select('*').execute()
    clusters_df = pd.DataFrame(clusters_response.data)
    
    # Convert timestamp strings to datetime objects with UTC timezone
    posts_df['timestamp'] = pd.to_datetime(posts_df['date']).dt.tz_convert('UTC')
    
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
reference_date = datetime(2025, 4, 4, tzinfo=pytz.UTC)  # Set to April 4, 2025 in UTC
if time_filter == "Last 24 Hours":
    date_threshold = reference_date - timedelta(days=1)
elif time_filter == "Last 7 Days":
    date_threshold = reference_date - timedelta(days=7)
elif time_filter == "Last 30 Days":
    date_threshold = reference_date - timedelta(days=30)
elif time_filter == "Last Year":
    date_threshold = reference_date - timedelta(days=365)
else:  # All Time
    date_threshold = datetime.min.replace(tzinfo=pytz.UTC)

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
        display_posts = filtered_posts_df[filtered_posts_df['text'].str.contains(search_term, case=False, na=False)]
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
    
    # Display posts for current page with scrolling
    st.dataframe(
        display_posts.iloc[start_idx:end_idx],
        use_container_width=True,
        height=500  # Set a fixed height for vertical scrolling
    )

# Tab 2: Cluster Based Fact Checking
with tab2:
    st.header("Fact Checking Clusters")
    
    # Get clustered claims data
    claims_response = supabase.table('clustered_claims').select('*').execute()
    claims_df = pd.DataFrame(claims_response.data)
    
    # Update cluster metrics based on filtered data
    for _, cluster in clusters_df.iterrows():
        cluster_claims = claims_df[claims_df['assigned_cluster'] == cluster['cluster_name']]
        cluster_posts = filtered_posts_df[filtered_posts_df['post_id'].isin(cluster_claims['post_id'])]
        current_cluster_count = len(cluster_posts)
        current_cluster_engagement = int(cluster_posts['favorites'].mean()) if not cluster_posts.empty else 0
        
        # Get priority level and format cluster name
        priority_level = cluster['cluster_priority.level'] if pd.notna(cluster['cluster_priority.level']) else 'Unknown'
        priority_color = {
            'High': '🔴',
            'Medium': '🟡',
            'Low': '🟢',
            'Unknown': '⚪'
        }.get(priority_level, '⚪')
        
        with st.expander(f"{priority_color} {cluster['cluster_name'].replace('_', ' ').title()} (Priority: {priority_level})"):
            # Create two columns for the layout
            col_left, col_right = st.columns([2, 1])
            
            with col_left:
                # Summary Section
                st.markdown("### Summary")
                st.markdown(cluster['cluster_summary.summary'] if cluster['cluster_summary.summary'] else 'No summary available')
                
                # Key Findings Section
                st.markdown("### Key Findings")
                findings = cluster['key_findings.findings']['items'] if cluster['key_findings.findings'] else []
                if findings:
                    for finding in findings:
                        st.markdown(f"**{finding.get('type', '')}**")
                        st.markdown(f"- {finding.get('description', '')}")
                else:
                    st.markdown("No findings available")
                
                # Recommended Actions Section
                st.markdown("### Recommended Actions")
                actions = cluster['recommended_actions.recommendations']['items'] if cluster['recommended_actions.recommendations'] else []
                if actions:
                    for action in actions:
                        st.markdown(f"**Action:** {action.get('action', '')}")
                        st.markdown(f"*Rationale:* {action.get('rationale', '')}")
                else:
                    st.markdown("No actions available")
            
            with col_right:
                # Metrics Section
                st.markdown("### Metrics")
                st.metric("Posts in Period", current_cluster_count)
                st.metric("Avg. Engagement", f"{current_cluster_engagement:,}")
                
                # Similar Fact Checks Section
                st.markdown("### Similar Fact Checks")
                fact_checks = cluster['similar_fact_checks.fact_checks']['items'] if cluster['similar_fact_checks.fact_checks'] else []
                if fact_checks:
                    for check in fact_checks:
                        confidence = check.get('match_confidence', 0) * 100  # Convert to percentage
                        source = check.get('source', '')
                        url = check.get('url', '')
                        if source and url:
                            st.markdown(f"**Source:** [{source}]({url})")
                            st.markdown(f"*Confidence:* {confidence:.0f}%")
                else:
                    st.markdown("No fact checks available")
            
            # Related Content Section (outside the columns)
            st.markdown("---")
            st.markdown("### Related Content")
            
            # Create tabs for related content
            posts_tab, claims_tab = st.tabs(["Related Posts", "Related Claims"])
            
            # Related Posts Tab
            with posts_tab:
                # Get claims for this cluster
                cluster_claims = claims_df[claims_df['assigned_cluster'] == cluster['cluster_name']]
                
                # Get posts for these claims
                cluster_posts = filtered_posts_df[filtered_posts_df['post_id'].isin(cluster_claims['post_id'])]
                
                if not cluster_posts.empty:
                    # Display posts in a dataframe
                    display_columns = ['post_id', 'user_name', 'date', 'text', 'favorites', 'retweets']
                    st.dataframe(
                        cluster_posts[display_columns],
                        use_container_width=True,
                        height=400
                    )
                else:
                    st.markdown("No posts available for this cluster")
            
            # Related Claims Tab
            with claims_tab:
                # Get claims for this cluster
                cluster_claims = claims_df[claims_df['assigned_cluster'] == cluster['cluster_name']]
                
                if not cluster_claims.empty:
                    # Display claims in a dataframe
                    display_columns = ['claim_id', 'post_id', 'claim', 'confidence', 'requires_additional_context']
                    st.dataframe(
                        cluster_claims[display_columns],
                        use_container_width=True,
                        height=400
                    )
                else:
                    st.markdown("No claims available for this cluster") 