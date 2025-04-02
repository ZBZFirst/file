import pandas as pd
import re
from datetime import datetime  # Import the datetime module

# Generate the filename based on the current date
current_date = datetime.now().strftime("%m%d%y")  # Format: MMDDYY
filename = f"ClaremontCollegesJobs_{current_date}_description.xlsx"

try:
    # Load the Excel file
    df = pd.read_excel(filename)
except FileNotFoundError:
    print(f"Error: The file '{filename}' does not exist.")
    exit()  # Exit the script if the file is not found

# Function to extract salary ranges
def extract_salary(text):
    # List of regex patterns for salary formats
    salary_patterns = [
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[-–]\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # Annual or monthly range (e.g., $50,000-$60,000 or $6,666.67-$7,083.33)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?/\s*(?:hour|hr)',  # Hourly rate (e.g., $22.79/hour)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?/\s*(?:month|mo)',  # Monthly rate (e.g., $6,666.67/month)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # Annual salary without a range (e.g., $50,000)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*per\s*(?:hour|hr)',  # Hourly rate without a slash (e.g., $22.79 per hour)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*per\s*(?:month|mo)',  # Monthly rate without a slash (e.g., $6,666.67 per month)
        r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*to\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # Salary range with "to" (e.g., $50,000 to $60,000)
        r'\(\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[-–]\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*\)',  # Salary range in parentheses (e.g., ($50,000 - $60,000))
        r'Salary:\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?\s*[-–]\s*\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?',  # Salary range with "Salary:" prefix (e.g., Salary: $50,000 - $60,000)
    ]
    
    # Check each pattern and return the first match
    for pattern in salary_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group()  # Return the first match found
    return None  # Return None if no match is found

# Extract salary data
df['salary'] = df['description'].apply(extract_salary)

# Replace NaN values in the 'salary' column with "NoneFound"
df['salary'] = df['salary'].fillna("NoneFound")

# Generate the output filename by appending '_parsed' to the original filename
output_filename = filename.replace(".xlsx", "_parsed.xlsx")

# Save the modified DataFrame to a new Excel file
df.to_excel(output_filename, index=False)

print(f"\nFile saved successfully as '{output_filename}'.")
