import os
import json
from datetime import datetime
import pytz
from config import supabase, load_csv_data, delete_all_rows
import pandas as pd
import ast

def load_cluster_presentations():
    """Load cluster presentations data"""
    print("Loading cluster presentations...")
    
    # Load and preprocess data
    df = load_csv_data('../realData/cluster_presentations.csv')
    df = df.fillna('')  # Fill NaN values with empty string
    
    # Delete existing data
    delete_all_rows('cluster_presentations')
    
    # Function to safely parse JSON string
    def parse_json_string(value):
        if not value:  # Empty string or None
            return {"items": []}
        try:
            if isinstance(value, str):
                # First use literal_eval to parse the Python list/dict syntax
                python_obj = ast.literal_eval(value)
                # Wrap the list in an items field
                json_obj = {"items": python_obj}
                return json_obj
            elif isinstance(value, (list, dict)):
                return {"items": value}
            return {"items": []}
        except Exception as e:
            print(f"Error parsing JSON: {str(e)}")
            return {"items": []}

    # Insert data
    for _, row in df.iterrows():
        try:
            data = {
                'cluster_name': row['cluster_name'],
                'process': row['process'],
                'status': row['status'],
                'message': row['message'],
                'cluster_summary.summary': row['cluster_summary.summary'],
                'similar_fact_checks.fact_checks': parse_json_string(row['similar_fact_checks.fact_checks']),
                'cluster_priority.level': row['cluster_priority.level'],
                'cluster_priority.rationale': row['cluster_priority.rationale'],
                'key_findings.findings': parse_json_string(row['key_findings.findings']),
                'recommended_actions.recommendations': parse_json_string(row['recommended_actions.recommendations'])
            }
            
            supabase.table('cluster_presentations').insert(data).execute()
            print(f"Successfully inserted cluster presentation: {data['cluster_name']}")
        except Exception as e:
            print(f"Error inserting cluster presentation: {str(e)}")
            continue

    print("Cluster presentations loaded successfully")
    return df['cluster_name'].tolist()

def load_posts():
    """Load posts data"""
    print("Loading posts...")
    
    # Load and preprocess data
    df = load_csv_data('../realData/posts.csv')
    
    # Delete existing data
    delete_all_rows('posts')
    
    # Keep track of successfully loaded post_ids
    loaded_post_ids = []
    
    # Insert new data
    for _, row in df.iterrows():
        try:
            # Keep timestamps as ISO format strings
            user_created = str(row['user_created']) if pd.notna(row['user_created']) else None
            date = str(row['date']) if pd.notna(row['date']) else None
            
            # Convert numeric fields
            user_followers = int(row['user_followers']) if pd.notna(row['user_followers']) else None
            user_friends = int(row['user_friends']) if pd.notna(row['user_friends']) else None
            user_favourites = int(row['user_favourites']) if pd.notna(row['user_favourites']) else None
            retweets = float(row['retweets']) if pd.notna(row['retweets']) else 0.0
            favorites = float(row['favorites']) if pd.notna(row['favorites']) else 0.0
            spam_score = float(row['spam_score']) if pd.notna(row['spam_score']) else 0.0
            
            # Convert boolean fields
            user_verified = bool(row['user_verified']) if pd.notna(row['user_verified']) else False
            is_retweet = bool(row['is_retweet']) if pd.notna(row['is_retweet']) else False
            
            # Convert hashtags
            hashtags_str = str(row['hashtags']) if pd.notna(row['hashtags']) else '[]'
            try:
                # Remove brackets and split by comma
                hashtags_str = hashtags_str.strip('[]')
                if hashtags_str:
                    # Split by comma and clean up each tag
                    hashtags = [tag.strip().strip("'\"") for tag in hashtags_str.split(',')]
                else:
                    hashtags = []
            except:
                hashtags = []
            
            data = {
                'post_id': str(row['post_id']),
                'user_name': str(row['user_name']) if pd.notna(row['user_name']) else None,
                'user_location': str(row['user_location']) if pd.notna(row['user_location']) else None,
                'user_description': str(row['user_description']) if pd.notna(row['user_description']) else None,
                'user_created': user_created,
                'user_followers': user_followers,
                'user_friends': user_friends,
                'user_favourites': user_favourites,
                'user_verified': user_verified,
                'date': date,
                'text': str(row['text']) if pd.notna(row['text']) else None,
                'hashtags': hashtags,
                'source': str(row['source']) if pd.notna(row['source']) else None,
                'retweets': retweets,
                'favorites': favorites,
                'is_retweet': is_retweet,
                'spam_score': spam_score,
                'spam_classification': str(row['spam_classification']) if pd.notna(row['spam_classification']) else None
            }
            
            supabase.table('posts').insert(data).execute()
            loaded_post_ids.append(row['post_id'])
        except Exception as e:
            print(f"Failed to load post {row['post_id']}: {str(e)}")
    
    print(f"Posts loaded successfully. Loaded {len(loaded_post_ids)} posts.")
    return loaded_post_ids

def load_clustered_claims(valid_post_ids, valid_clusters):
    """Load clustered claims data"""
    print("Loading clustered claims...")
    
    # Load and preprocess data
    df = load_csv_data('../realData/clustered_claims.csv')
    df = df.fillna('')  # Fill NaN values with empty string
    
    # Function to safely parse JSON string
    def parse_json_string(value):
        if not value:  # Empty string or None
            return None
        try:
            if isinstance(value, str):
                # First use literal_eval to parse the Python list/dict syntax
                return ast.literal_eval(value)
            return value
        except Exception as e:
            print(f"Error parsing JSON: {str(e)}")
            return None
    
    # Filter claims to only include those with valid post_ids and clusters
    df = df[
        df['post_id'].isin(valid_post_ids) & 
        df['assigned_cluster'].isin(valid_clusters)
    ]
    
    # Delete existing data
    delete_all_rows('clustered_claims')
    
    # Insert data
    for _, row in df.iterrows():
        try:
            data = {
                'claim_id': str(row['claim_id']),
                'post_id': str(row['post_id']),
                'claim': row['claim'],
                'confidence': float(row['confidence']) if row['confidence'] else None,
                'location': row['location'],
                'requires_additional_context': bool(row['requires_additional_context']) if row['requires_additional_context'] else False,
                'reasoning': row['reasoning'],
                'context_flags': parse_json_string(row['context_flags']),
                'context_explanations': parse_json_string(row['context_explanations']),
                'search_queries_recommended': parse_json_string(row['search_queries_recommended']),
                'extracted_entities': parse_json_string(row['extracted_entities']),
                'famous_entities_identified': bool(row['famous_entities_identified']) if row['famous_entities_identified'] else False,
                'entity_resolution_summary': row['entity_resolution_summary'],
                'is_famous_poster': bool(row['is_famous_poster']) if row['is_famous_poster'] else False,
                'process': row['process'],
                'status': row['status'],
                'message': row['message'],
                'classification': parse_json_string(row['classification']),
                'amplifiability': parse_json_string(row['amplifiability']),
                'assigned_cluster': row['assigned_cluster']
            }
            
            supabase.table('clustered_claims').insert(data).execute()
            print(f"Successfully inserted claim: {data['claim_id']}")
        except Exception as e:
            print(f"Failed to load claim {row['claim_id']}: {str(e)}")
            continue
    
    print(f"Clustered claims loaded successfully. Loaded {len(df)} claims.")

def main():
    """Main function to load all data"""
    print("Starting data load...")
    
    # First delete all data in reverse order of dependencies
    print("Deleting existing data...")
    delete_all_rows('clustered_claims')  # Delete child table first
    delete_all_rows('posts')  # Delete independent table
    delete_all_rows('cluster_presentations')  # Delete parent table last
    
    # Then load new data in order of dependencies
    print("Loading new data...")
    valid_clusters = load_cluster_presentations()  # Load parent table first
    valid_post_ids = load_posts()  # Load independent table
    load_clustered_claims(valid_post_ids, valid_clusters)  # Load child table last with valid IDs
    
    print("All data loaded successfully!")

if __name__ == "__main__":
    main() 