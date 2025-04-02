import pandas as pd
from bs4 import BeautifulSoup
import re  # Import the regular expressions module
import os
from datetime import datetime  # Import the datetime module

# Get the current date and format it as 'MMDDYYYY'
current_date = datetime.now().strftime("%m%d%Y")

# Construct the file path dynamically
file_path = f"DignityHospitals_{current_date}_description.xlsx"

# Check if the file exists
if not os.path.exists(file_path):
    print(f"File '{file_path}' does not exist.")
    exit()

# Load the dataset
data = pd.read_excel(file_path).fillna('')

# Function to extract structured data from HTML
def extract_overview_data(html_content):
    if not html_content:
        return {}

    soup = BeautifulSoup(html_content, 'html.parser')
    details = {}

    # Find all <span> tags with class 'job-info'
    for span in soup.find_all('span', class_='job-info'):
        # Find the <b> tag within the <span>
        b_tag = span.find('b')
        if b_tag:
            # Extract the label (text within <b>)
            label = b_tag.get_text(strip=True).strip(':')
            # Extract the value (text after </b> until </span>)
            value = ''.join(b_tag.next_siblings).strip()
            details[label] = value

    return details

# Function to extract the relevant section16 HTML segment
def extract_section16_segment(html_content):
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    section16_panel = soup.find('div', class_='section16__panel')
    
    if section16_panel:
        return str(section16_panel)
    return None

# Function to extract the ats-description segment
def extract_ats_description(html_content):
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    ats_description = soup.find('div', class_='ats-description')
    
    # Stop if the job-apply button is encountered
    job_apply_button = soup.find('a', class_='button job-apply bottom')
    if job_apply_button:
        # Extract only the content before the job-apply button
        ats_description = str(ats_description).split(str(job_apply_button))[0]
        return ats_description
    
    if ats_description:
        return str(ats_description)
    return None

# Function to extract desc-overview segment from job_details_html
def extract_desc_overview(html_content):
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    desc_overview = soup.find('span', class_='desc-overview')
    
    if desc_overview:
        # Find the parent container (e.g., <div class="ats-description">)
        parent_container = desc_overview.find_parent('div', class_='ats-description')
        if parent_container:
            # Extract the content until the read-more button
            read_more_button = parent_container.find('button', class_='read-more__btn')
            if read_more_button:
                # Extract only the content before the read-more button
                content = str(parent_container).split(str(read_more_button))[0]
                return content
            else:
                # If no read-more button, return the entire parent container
                return str(parent_container)
    return None

# Function to extract the pay range from the 'job-info posted-pay-range' column
def extract_pay_range(text):
    if not text:
        return text  # Return the original text if it's empty
    
    # Use regex to find the pay range pattern (e.g., $34.50 - $50.97 /hour)
    pay_range_pattern = r"\$\d+\.\d+\s*-\s*\$\d+\.\d+\s*\/hour"
    match = re.search(pay_range_pattern, text)
    
    if match:
        return match.group()  # Return the matched pay range
    else:
        return text  # Return the original text if no match is found

# Function to remove HTML tags and extract plain text
def extract_plain_text(html_content):
    if not html_content:
        return ""
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Extract and return the plain text
    return soup.get_text(separator="\n").strip()

# Function to split the text into sections
def split_sections(text):
    sections = {
        "Overview": "",
        "Responsibilities": "",
        "Qualifications": ""
    }
    
    # Split the text into sections
    overview_start = text.find("Overview")
    responsibilities_start = text.find("Responsibilities")
    qualifications_start = text.find("Qualifications")
    
    if overview_start != -1 and responsibilities_start != -1:
        sections["Overview"] = text[overview_start:responsibilities_start].strip()
    if responsibilities_start != -1 and qualifications_start != -1:
        sections["Responsibilities"] = text[responsibilities_start:qualifications_start].strip()
    if qualifications_start != -1:
        sections["Qualifications"] = text[qualifications_start:].strip()
    
    return sections

# Function to extract low and high pay values
def extract_pay_values(pay_range):
    if not pay_range:
        return None, None
    
    # Use regex to find the two pay values in the range
    pay_values = re.findall(r"\$\d+\.\d+", pay_range)
    
    if len(pay_values) == 2:
        pay_low = float(pay_values[0].replace("$", ""))  # Remove the dollar sign and convert to float
        pay_high = float(pay_values[1].replace("$", ""))  # Remove the dollar sign and convert to float
        return pay_low, pay_high
    else:
        return None, None  # Return None if the pay range is invalid
    
# Extract structured data from 'overview_html'
overview_data = data['overview_html'].apply(extract_overview_data)
overview_df = pd.DataFrame(overview_data.tolist()).fillna('')

# Extract the relevant segment from 'section16_html'
section16_segment = data['section16_html'].apply(extract_section16_segment)

# If 'overview_html' is empty, copy the extracted segment from 'section16_html'
for idx, row in data.iterrows():
    if not row['overview_html'] and section16_segment[idx]:
        data.at[idx, 'overview_html'] = section16_segment[idx]

# Extract the ats-description segment from 'section16_html'
ats_description_segment = data['section16_html'].apply(extract_ats_description)

# If 'job_details_html' is empty, copy the extracted segment from 'section16_html'
for idx, row in data.iterrows():
    if not row['job_details_html'] and ats_description_segment[idx]:
        data.at[idx, 'job_details_html'] = ats_description_segment[idx]

# If 'section16_html' is empty, extract desc-overview from 'job_details_html'
for idx, row in data.iterrows():
    if not row['section16_html'] and row['job_details_html']:
        desc_overview_segment = extract_desc_overview(row['job_details_html'])
        if desc_overview_segment:
            data.at[idx, 'job_details_html'] = desc_overview_segment

# Re-extract structured data from the updated 'overview_html'
overview_data = data['overview_html'].apply(extract_overview_data)
overview_df = pd.DataFrame(overview_data.tolist()).fillna('')

# Extract structured data from 'section16_html'
section16_data = data['section16_html'].apply(extract_overview_data)
section16_df = pd.DataFrame(section16_data.tolist()).fillna('')

# Combine original data with extracted overview and section16 data
cleaned_data = pd.concat([data, overview_df.add_prefix('overview_'), section16_df.add_prefix('section16_')], axis=1)

# Extract and clean the 'job-info posted-pay-range' column
cleaned_data['job-info posted-pay-range'] = cleaned_data['job-info posted-pay-range'].apply(extract_pay_range)

# List of source columns to preserve
source_columns = ['section16_html', 'overview_html', 'job_details_html']

# Combine columns with shared suffixes
columns = cleaned_data.columns.tolist()
suffixes = set()

# Identify shared suffixes (excluding source columns)
for col in columns:
    if (col.startswith('overview_') or col.startswith('section16_')) and col not in source_columns:
        suffix = col.split('_', 1)[1]
        suffixes.add(suffix)

# Merge columns with shared suffixes
for suffix in suffixes:
    overview_col = f'overview_{suffix}'
    section16_col = f'section16_{suffix}'
    
    # Check if both columns exist
    if overview_col in columns and section16_col in columns:
        # Combine the columns, prioritizing non-empty values
        cleaned_data[suffix] = cleaned_data[overview_col].combine_first(cleaned_data[section16_col])
        
        # Drop the original columns (only if they are not source columns)
        if overview_col not in source_columns and section16_col not in source_columns:
            cleaned_data.drop(columns=[overview_col, section16_col], inplace=True)
    elif overview_col in columns and overview_col not in source_columns:
        # Rename the overview column to the suffix
        cleaned_data.rename(columns={overview_col: suffix}, inplace=True)
    elif section16_col in columns and section16_col not in source_columns:
        # Rename the section16 column to the suffix
        cleaned_data.rename(columns={section16_col: suffix}, inplace=True)

# Apply the function to the 'job_details_html' column
cleaned_data['job_details_plain_text'] = cleaned_data['job_details_html'].apply(extract_plain_text)

# Apply the function to the 'job_details_plain_text' column
split_data = cleaned_data['job_details_plain_text'].apply(split_sections).apply(pd.Series)

# Combine the split data with the original DataFrame
cleaned_data = pd.concat([cleaned_data, split_data], axis=1)

# Apply the function to the 'job-info posted-pay-range' column
cleaned_data[['pay_low', 'pay_high']] = cleaned_data['job-info posted-pay-range'].apply(
    lambda x: pd.Series(extract_pay_values(x))
)

# Calculate the difference between pay_high and pay_low
cleaned_data['pay_difference'] = (cleaned_data['pay_high'] - cleaned_data['pay_low']).round(2)

# Extract the base filename (without extension) from the input file path
base_filename = os.path.splitext(os.path.basename(file_path))[0]

# Construct the output filename by appending '_parsed.xlsx'
output_filename = f"{base_filename}_parsed.xlsx"

# Save the combined data to Excel with the new filename
output_path = os.path.join(os.path.dirname(file_path), output_filename)
cleaned_data.to_excel(output_path, index=False, engine='openpyxl')

print(f"Combined structured data saved to '{output_path}'.")
