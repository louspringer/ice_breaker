from snowflake.snowpark import Session
import pandas as pd

# Establish a Snowpark session using the default connection profile
session = Session.builder.configs({"connection_name": "default"}).create()

# Load the Contact and InteractionPoint tables into Snowpark DataFrames
contact_df = session.table("Contact")
interaction_df = session.table("InteractionPoint")

# Perform the analysis using Snowpark DataFrames
result_df = contact_df.join(interaction_df, contact_df["id"] == interaction_df["contactId"], "left") \
    .group_by(contact_df["fullName"], contact_df["linkedInURL"]) \
    .agg(interaction_df["id"].count().alias("interaction_count")) \
    .sort("interaction_count", ascending=False)

# Collect the results into a pandas DataFrame
results = result_df.collect()
columns = ["fullName", "linkedInURL", "interaction_count"]
dataframe = pd.DataFrame(results, columns=columns)

# Display the analysis
print("Candidate Analysis:")
print(dataframe)

# Close the session
session.close() 