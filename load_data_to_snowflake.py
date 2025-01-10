from snowflake.snowpark import Session
import pandas as pd

# Establish a Snowpark session using the default connection profile
session = Session.builder.configs("default").create()

# Load CSV data into a DataFrame
csv_file_path = 'linkedin_profiles.csv'
data = pd.read_csv(csv_file_path)

# Create a Snowpark DataFrame from the pandas DataFrame
df = session.create_dataframe(data)

# Write the data to the Contact table
df.write.mode('overwrite').save_as_table('Contact')

print("Data loaded successfully into Snowflake using Snowpark.")

# Close the session
session.close() 