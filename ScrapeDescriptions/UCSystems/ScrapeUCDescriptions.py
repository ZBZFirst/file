import os
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from datetime import datetime
import time

# Constants
MAX_CELL_SIZE = 30000  # Conservative limit for Excel cell size
SCRAPE_DIR = r"C:\Scrape\ScrapeLinks\UCSystems"
OUTPUT_DIR = r"C:\Scrape\ScrapeDescriptions\UCSystems"

def split_html_for_excel(html):
    """Split HTML content into chunks that fit in Excel cells"""
    if not html or not isinstance(html, str):
        return [""]
    
    chunks = []
    for i in range(0, len(html), MAX_CELL_SIZE):
        chunks.append(html[i:i+MAX_CELL_SIZE])
    return chunks

def setup_driver():
    """Configure and return Chrome WebDriver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.set_page_load_timeout(30)
    return driver

def get_input_file():
    """Find and select the appropriate input file"""
    today = datetime.now().strftime("%m%d%Y")
    matching_files = [f for f in os.listdir(SCRAPE_DIR) 
                     if f.startswith(f"ucjobs_{today}") and f.endswith(".xlsx")]
    
    if not matching_files:
        raise FileNotFoundError(f"No files found for today ({today}) in directory: {SCRAPE_DIR}")
    
    if len(matching_files) == 1:
        return os.path.join(SCRAPE_DIR, matching_files[0])
    
    print("Multiple files found for today. Please select one:")
    for i, file in enumerate(matching_files, 1):
        print(f"{i}. {file}")
    selection = int(input("Enter the number of the file to use: ")) - 1
    return os.path.join(SCRAPE_DIR, matching_files[selection])

def initialize_output_df(input_file, output_path):
    """Initialize or load existing output dataframe"""
    if os.path.exists(output_path):
        print(f"Loading existing output file: {output_path}")
        existing_df = pd.read_excel(output_path)
        processed_urls = set(existing_df['Job Link'].dropna())
        return existing_df, processed_urls
    
    print("Creating new output file")
    original_df = pd.read_excel(input_file)
    processed_urls = set()
    
    # Create output dataframe with columns for HTML chunks
    base_columns = list(original_df.columns) + ['Status', 'Final URL']
    html_columns = [f'HTML_{i+1}' for i in range(20)]  # Support up to 300,000 characters
    output_columns = base_columns + html_columns
    
    return pd.DataFrame(columns=output_columns), processed_urls

def process_url(driver, job_link, job_title):
    """Process a single URL and return results"""
    result = {
        'Status': '',
        'Final URL': '',
        'HTML': ''
    }
    
    try:
        driver.get(job_link)
        final_url = driver.current_url
        
        if final_url != job_link:
            result.update({
                'Status': 'REDIRECTED',
                'Final URL': final_url
            })
            return result
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, "body")))
        
        html = driver.page_source
        result.update({
            'Status': 'SUCCESS',
            'Final URL': final_url,
            'HTML': html
        })
        
    except TimeoutException:
        result['Status'] = 'PAGE NOT FOUND'
    except WebDriverException as e:
        error_msg = str(e)
        if "net::ERR_NAME_NOT_RESOLVED" in error_msg or "net::ERR_CONNECTION_REFUSED" in error_msg:
            result['Status'] = 'PAGE NOT FOUND'
        else:
            result['Status'] = f'ERROR: {error_msg[:100]}'
    except Exception as e:
        result['Status'] = f'ERROR: {str(e)[:100]}'
    
    return result

def main():
    input_file = get_input_file()
    print(f"Using input file: {input_file}")
    
    today = datetime.now().strftime("%m%d%Y")
    output_path = os.path.join(OUTPUT_DIR, f"ucjobs_html_{today}.xlsx")
    
    output_df, processed_urls = initialize_output_df(input_file, output_path)
    original_df = pd.read_excel(input_file)
    driver = setup_driver()
    
    try:
        for index, row in original_df.iterrows():
            job_title = row['Job Title']
            job_link = row['Job Link']
            
            if pd.isna(job_link) or not isinstance(job_link, str) or not job_link.startswith('http'):
                print(f"Skipping invalid link for: {job_title}")
                continue
            
            if job_link in processed_urls:
                print(f"Skipping already processed URL: {job_link}")
                continue
            
            print(f"Processing {index + 1}/{len(original_df)}: {job_title[:50]}...")
            result = process_url(driver, job_link, job_title)
            
            # Prepare new row data
            new_row = row.to_dict()
            new_row.update({
                'Status': result['Status'],
                'Final URL': result['Final URL']
            })
            
            # Split HTML into chunks and add to columns
            html_chunks = split_html_for_excel(result['HTML'])
            for i, chunk in enumerate(html_chunks):
                if i < 20:  # Only keep first 10 chunks
                    new_row[f'HTML_{i+1}'] = chunk
            
            # Add to output dataframe
            output_df = pd.concat([output_df, pd.DataFrame([new_row])], ignore_index=True)
            
            # Save progress after each URL
            output_df.to_excel(output_path, index=False)
            processed_urls.add(job_link)
            
            time.sleep(1)
            
    finally:
        driver.quit()
        output_df.to_excel(output_path, index=False)
        print(f"Processing complete. Results saved to: {output_path}")

if __name__ == "__main__":
    main()
