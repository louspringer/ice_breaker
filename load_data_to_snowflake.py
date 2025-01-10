from snowflake.snowpark import Session
import pandas as pd
from datetime import datetime

def clean_mutual_connections(text):
    """Clean the mutual connections text from LinkedIn format."""
    if pd.isna(text):
        return None
    return text.strip()

def main():
    try:
        # Use default connection profile from ~/.snowsql/config
        session = Session.builder.configs("default").create()
        print("Successfully connected to Snowflake")
        
        # Use correct database and schema
        session.use_database("ICE_BREAKER_DB")
        session.use_schema("NETWORKING")
        
        # Load CSV data into a DataFrame
        csv_file_path = 'linkedin_profiles.csv'
        data = pd.read_csv(csv_file_path)
        
        # Clean and transform data
        data = data.rename(columns={
            'Name': 'full_name',
            'Profile Link': 'linkedin_url',
            'Title': 'title',
            'Location': 'location',
            'Mutual Connections': 'mutual_connections'
        })
        
        # Clean mutual connections
        data['mutual_connections'] = data['mutual_connections'].apply(clean_mutual_connections)
        
        # Add metadata columns
        current_time = datetime.now()
        data['created_at'] = current_time
        data['updated_at'] = current_time
        data['networking_degree'] = 'SecondDegree'  # Default value
        
        # Create a Snowpark DataFrame
        snowpark_df = session.create_dataframe(data)
        
        # Write to Snowflake table
        snowpark_df.write.mode('overwrite').save_as_table('CONTACTS')
        print(f"Successfully loaded {len(data)} profiles into Snowflake")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        raise
    finally:
        if 'session' in locals():
            session.close()
            print("Snowflake session closed")

if __name__ == "__main__":
    main() 