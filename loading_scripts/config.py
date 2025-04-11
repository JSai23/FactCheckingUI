import os
from supabase import create_client
import pandas as pd
import json

# Supabase configuration
SUPABASE_URL = "https://jexerobmznypbkwsenyb.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpleGVyb2Jtem55cGJrd3NlbnliIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDM3NjU0NSwiZXhwIjoyMDU5OTUyNTQ1fQ.RX7p0W13_I88FV4jwqewn92UoVgXywUu9RQsBm2_RNw"  # Replace with your key

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def delete_all_rows(table_name):
    """Delete all rows from a table"""
    # Different tables have different primary keys
    if table_name == 'cluster_presentations':
        # For cluster_presentations, we use cluster_name
        supabase.table(table_name).delete().neq('cluster_name', '').execute()
    elif table_name == 'clustered_claims':
        supabase.table(table_name).delete().neq('claim_id', 'dummy').execute()
    elif table_name == 'posts':
        supabase.table(table_name).delete().neq('post_id', 'dummy').execute()
    else:
        # For other tables that might have an id column
        supabase.table(table_name).delete().neq('id', 'dummy').execute()

def load_csv_data(file_path):
    """Load CSV data and handle JSON columns"""
    df = pd.read_csv(file_path)
    
    # Convert string representations of lists and dicts to proper JSON
    for col in df.columns:
        if df[col].dtype == 'object':
            try:
                # Try to parse as JSON if it looks like a JSON string
                sample = df[col].iloc[0] if not df[col].isna().all() else None
                if sample and isinstance(sample, str) and (sample.startswith('[') or sample.startswith('{')):
                    df[col] = df[col].apply(lambda x: json.loads(x) if pd.notna(x) else None)
            except:
                pass
    
    return df 