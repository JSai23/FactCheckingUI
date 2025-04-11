import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import pytz
from supabase import create_client
import json
from st_aggrid import AgGrid, GridOptionsBuilder

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
    
    # Add reviewed column
    display_posts = display_posts.copy()
    
    # Configure grid for posts
    gb = GridOptionsBuilder.from_dataframe(display_posts)
    
    # Configure selection
    gb.configure_selection(selection_mode='multiple', use_checkbox=True)
    
    # Configure columns
    gb.configure_column('post_id', header_name='Post ID')
    gb.configure_column('user_name', header_name='User')
    gb.configure_column('date', header_name='Date')
    gb.configure_column('text', header_name='Content')
    gb.configure_column('favorites', header_name='Favorites')
    gb.configure_column('retweets', header_name='Retweets')
    gb.configure_default_column(resizable=True, filterable=True)
    
    grid_options = gb.build()
    
    grid_response = AgGrid(
        display_posts,
        gridOptions=grid_options,
        height=600,
        width='100%',
        data_return_mode='AS_INPUT',
        update_mode='MODEL_CHANGED'
    )
    
    # Submit button for reviews
    if st.button("Submit Reviews", key="submit_reviews"):
        selected_df = pd.DataFrame(grid_response['selected_rows'])
        if not selected_df.empty:
            selected_post_ids = selected_df['post_id'].astype(str).tolist()
            st.success(f"Submitted {len(selected_post_ids)} reviews for posts: {', '.join(selected_post_ids)}")
        else:
            st.warning("No posts selected for review")

# Tab 2: Cluster Based Fact Checking
with tab2:
    st.header("Fact Checking Clusters")
    
    # Get clustered claims data
    claims_response = supabase.table('clustered_claims').select('*').execute()
    claims_df = pd.DataFrame(claims_response.data)
    
    # Dictionary to store helpful states
    helpful_states = {}
    
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
            # Add helpful checkbox at the top
            helpful_states[cluster['cluster_name']] = st.checkbox("Mark as Helpful", key=f"helpful_{cluster['cluster_name']}")
            
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
    
    # Submit button for helpful states
    if st.button("Submit Cluster Feedback", key="submit_helpful"):
        helpful_clusters = [cluster_name for cluster_name, is_helpful in helpful_states.items() if is_helpful]
        if helpful_clusters:
            st.success(f"Submitted feedback for {len(helpful_clusters)} clusters: {', '.join(helpful_clusters)}")
        else:
            st.warning("No clusters marked as helpful") 