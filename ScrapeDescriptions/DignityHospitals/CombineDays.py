import os
import pandas as pd

def find_and_load_parsed_files(directory):
    parsed_files = []

    # Walk through the directory to find relevant files
    for root, _, files in os.walk(directory):
        for file in files:
            if "parsed" in file and file.endswith(".csv"):
                full_path = os.path.join(root, file)
                parsed_files.append(full_path)

    # Load and combine DataFrames
    dataframes = []
    common_columns = None

    for file in parsed_files:
        try:
            df = pd.read_csv(file)

            # Initialize common_columns with the first DataFrame's columns
            if common_columns is None:
                common_columns = set(df.columns)

            # Append only if column names match
            if set(df.columns) == common_columns:
                dataframes.append(df)
                print(f"{os.path.basename(file)}: {len(df)} rows")
            else:
                print(f"{os.path.basename(file)} skipped (column mismatch)")

        except Exception as e:
            print(f"Failed to load {file}: {e}")

    # Combine, sort, and print
    if dataframes:
        combined_df = pd.concat(dataframes, ignore_index=True)
        if 'scraped_date' in combined_df.columns:
            combined_df = combined_df.sort_values(by='scraped_date')

        print("\nCombined Results:")
        print(combined_df)
    else:
        print("No valid data found.")

# Specify the directory to search
directory_to_search = "."

# Run the function
find_and_load_parsed_files(directory_to_search)
