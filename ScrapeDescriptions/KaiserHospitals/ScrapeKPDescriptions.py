from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import re
import os
from pathlib import Path
from datetime import datetime  # Import datetime for timestamp generation

def clean_html_content(html):
    """Remove extra newlines and spaces from HTML content while preserving structure."""
    # Remove leading and trailing whitespace
    html = html.strip()
    
    # Replace multiple newlines with a single newline
    html = re.sub(r'\n+', '\n', html)
    
    # Replace multiple spaces with a single space
    html = re.sub(r'[ ]+', ' ', html)
    
    # Remove spaces between HTML tags, but preserve newlines after specific tags
    html = re.sub(r'>\s+<', '><', html)
    
    # Add newlines after specific tags (e.g., <p>, <b>, <div>, <h1>, etc.)
    tags_to_preserve = ['p', 'b', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'li']
    for tag in tags_to_preserve:
        html = re.sub(fr'(<{tag}[^>]*>.*?</{tag}>)', r'\1\n', html)
    
    return html

def scrape_job_html(driver, url):
    """Scrape HTML content from job-left section"""
    driver.get(url)
    try:
        # Wait for job-left section to load
        job_left = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.job-left"))
        )
        html_content = job_left.get_attribute("innerHTML")
        
        # Clean up the HTML content
        cleaned_html = clean_html_content(html_content)
        
        return cleaned_html
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

# 👇 Calculate paths relative to project root
parent_dir = Path(__file__).resolve().parent.parent.parent  # Goes up to C:\Scrape

# Generate dynamic timestamp for the input filename
timestamp = datetime.now().strftime("%m%d%Y")  # Format: MMDDYYYY
input_filename = f"kpjobs_{timestamp}.xlsx"  # Dynamic filename (now .xlsx)
input_path = parent_dir / "ScrapeLinks" / "KaiserHospitals" / input_filename  # Input file path

# Generate output filename by adding "description" to the input filename
output_filename = f"kpjobs_{timestamp}_description.xlsx"  # Add "description" to the filename (now .xlsx)
output_path = parent_dir / "ScrapeDescriptions" / "KaiserHospitals" / output_filename  # Output file path

# Initialize the Selenium WebDriver
driver = webdriver.Chrome()  # or whichever driver you are using

# Check if the output file exists
if os.path.exists(output_path):
    df = pd.read_excel(output_path)  # Updated to read Excel
    # Check if the 'scraped_html' column exists
    if 'scraped_html' not in df.columns:
        df['scraped_html'] = None
else:
    # Create directory if it doesn't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    # Load from input Excel file
    df = pd.read_excel(input_path)  # Updated to read Excel
    df['scraped_html'] = None

# Iterate through each row
total_rows = len(df)  # Total number of rows in the DataFrame
for index, row in df.iterrows():
    if pd.isna(row['scraped_html']):  # Check if 'scraped_html' is empty
        url = row['URL']  # Assuming the column with URLs is named 'URL'
        scraped_html = scrape_job_html(driver, url)
        if scraped_html:
            df.at[index, 'scraped_html'] = scraped_html
            df.to_excel(output_path, index=False)  # Updated to write Excel
            print(f"Scraped and saved HTML for URL: {url} ({index + 1} out of {total_rows})")
        else:
            print(f"Failed to scrape HTML for URL: {url} ({index + 1} out of {total_rows})")
    else:
        print(f"Skipping URL: {row['URL']} (Data already present in 'scraped_html') ({index + 1} out of {total_rows})")

# Close the WebDriver
driver.quit()
