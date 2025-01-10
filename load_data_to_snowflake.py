from snowflake.snowpark import Session
import pandas as pd
from datetime import datetime
import argparse

def clean_mutual_connections(text):
    """Clean the mutual connections text from LinkedIn format."""
    if pd.isna(text):
        return None
    return text.strip()

def get_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Load LinkedIn profiles to Snowflake')
    parser.add_argument('-p', '--profile', default='default',
                      help='Snowflake connection profile name (default: "default")')
    return parser.parse_args()

def main():
    args = get_args()
    try:
        # Use specified connection profile from ~/.snowsql/config
        session = Session.builder.config("connection_name", args.profile).create()
        print(f"Successfully connected to Snowflake using profile: {args.profile}")
        
        # Use correct database and schema
        session.use_database("ICE_BREAKER_DB")
        session.use_schema("NETWORKING")
        
        # Load CSV data into a DataFrame
        csv_file_path = 'linkedin_profiles.csv'
        print(f"Loading data from {csv_file_path}")
        data = pd.read_csv(csv_file_path)
        print(f"Loaded {len(data)} rows from CSV")
        
        # Clean and transform data
        data = data.rename(columns={
            'Name': 'full_name',
            'Profile Link': 'linkedin_url',
            'Title': 'title',
            'Location': 'location',
            'Mutual Connections': 'mutual_connections'
        })
        
        # Clean mutual connections and handle NaN values
        data['mutual_connections'] = data['mutual_connections'].apply(clean_mutual_connections)
        data['title'] = data['title'].fillna('')
        data['location'] = data['location'].fillna('')
        data['mutual_connections'] = data['mutual_connections'].fillna('')
        
        # Add metadata columns with ISO format timestamps
        current_time = datetime.now().isoformat()
        data['created_at'] = current_time
        data['updated_at'] = current_time
        data['networking_degree'] = 'SecondDegree'  # Default value
        
        print("Data transformation complete")
        print(f"Columns: {data.columns.tolist()}")
        
        # Convert DataFrame to list of tuples for Snowpark
        data_records = list(data.itertuples(index=False, name=None))
        column_names = data.columns.tolist()
        
        # Create a Snowpark DataFrame
        print("Creating Snowpark DataFrame")
        snowpark_df = session.create_dataframe(data_records, schema=column_names)
        
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