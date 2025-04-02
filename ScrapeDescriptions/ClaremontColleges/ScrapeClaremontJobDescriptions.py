from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import os
from pathlib import Path
from datetime import datetime  # Import datetime for timestamp generation

# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

# 👇 Add path calculation here (before `main()`)
parent_dir = Path(__file__).resolve().parent.parent.parent  # Go up 3 levels to C:\Scrape

# Generate dynamic timestamp for the input filename
timestamp = datetime.now().strftime("%m%d%y")  # Format: MMDDYY (2-digit year)
input_filename = f"ClaremontCollegesJobs_{timestamp}.xlsx"  # Dynamic filename (now .xlsx)
input_path = parent_dir / "ScrapeLinks" / "ClaremontColleges" / input_filename  # Input file path

# Generate output filename by adding "description" to the input filename
output_filename = f"ClaremontCollegesJobs_{timestamp}_description.xlsx"  # Add "description" to the filename (now .xlsx)
output_path = parent_dir / "ScrapeDescriptions" / "ClaremontColleges" / output_filename  # Output file path

def setup_driver():
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    return driver

def safe_find(parent, selector, default=None):
    """Safely find element with default return"""
    try:
        elements = parent.find_elements(By.CSS_SELECTOR, selector)
        return elements[0].text if elements else default
    except Exception as e:
        return default

def scrape_job_details(driver, url):
    """Scrape detailed information from a job posting page"""
    try:
        print(f"Processing job: {url}")
        driver.get(url)
        
        # Wait for page to fully load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "span.css-ttaaxj"))
        )
        
        # Wait for main content to load
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.css-gj3t6y"))
        )
        
        # Extract job details
        job_data = {
            'url': url,
            'title': safe_find(driver, 'h2[data-automation-id="jobPostingHeader"]'),
            'description': safe_find(driver, 'div.css-ey7qxc'),
            'details': {}
        }
        
        # Extract all sections from job details container
        details_container = driver.find_element(By.CSS_SELECTOR, 'div[data-automation-id="job-posting-details"]')
        sections = details_container.find_elements(By.CSS_SELECTOR, 'div.css-11p01j8')
        
        for section in sections:
            try:
                # Get section title
                title = safe_find(section, 'h3.css-1jh3q7a')
                if not title:
                    continue
                
                # Get section content
                content = safe_find(section, 'div.css-1t5f0fr')
                job_data['details'][title] = content
                
            except Exception as e:
                print(f"Error processing section: {str(e)[:100]}...")
                continue
        
        return job_data
    
    except TimeoutException:
        print(f"Timeout loading job page: {url}")
        return None
    except Exception as e:
        print(f"Error processing job page {url}: {str(e)[:100]}...")
        return None

def main():
    # Load the previously collected job links
    try:
        job_links = pd.read_excel(input_path)  # Updated to read Excel
    except FileNotFoundError:
        print(f"File not found: {input_path}. Check the path!")
        return
    
    # Initialize DataFrame for output
    if os.path.exists(output_path):
        # Load existing output file
        df = pd.read_excel(output_path)
        print(f"Found existing output file: {output_path}")
    else:
        # Create a new DataFrame with the required columns
        df = pd.DataFrame(columns=[
            'url', 'title', 'description', 'source_page', 'department', 
            'location', 'time_type', 'posted', 'requisition_id'
        ])
        # Create the output directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    driver = setup_driver()
    
    try:
        for index, row in job_links.iterrows():
            url = row['url']
            
            # Skip if URL is already processed
            if not df[df['url'] == url].empty:
                print(f"Skipping already processed URL: {url}")
                continue
            
            # Scrape job details
            job_details = scrape_job_details(driver, url)
            if job_details:
                # Add metadata from original listing
                job_details.update({
                    'source_page': row['source_page'],
                    'department': row['department'],
                    'location': row['location'],
                    'time_type': row['time_type'],
                    'posted': row['posted'],
                    'requisition_id': row['requisition_id']
                })
                
                # Append the new data to the DataFrame
                df = pd.concat([df, pd.DataFrame([job_details])], ignore_index=True)
                
                # Save progress after each row
                df.to_excel(output_path, index=False)
                print(f"Saved progress for URL: {url}")
            
            # Add delay between requests
            time.sleep(1.5)  # Adjust as needed
            
    finally:
        driver.quit()
    
    print(f"\nSuccess! Saved {len(df)} job details to {output_path}.")

if __name__ == '__main__':
    main()
