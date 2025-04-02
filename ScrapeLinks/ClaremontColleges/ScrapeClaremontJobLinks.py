from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time
import os
from datetime import datetime

# Configure Chrome options
options = webdriver.ChromeOptions()
options.add_argument("--start-maximized")
options.add_experimental_option("excludeSwitches", ["enable-automation"])
options.add_experimental_option("useAutomationExtension", False)

CAREER_PAGES = [
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/TCCS_Careers",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/en-US/CGU_Careers",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/HMC_Careers",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/SCR_Career_Staff",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/CMC_Staff",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/PIT_Staff",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/en-US/KGI_Careers",
    "https://theclaremontcolleges.wd1.myworkdayjobs.com/POM_Careers"
]

def safe_find(parent, selector, default=None):
    """Safely find element with default return"""
    try:
        elements = parent.find_elements(By.CSS_SELECTOR, selector)
        return elements[0].text if elements else default
    except Exception as e:
        print(f"Error in safe_find: {str(e)[:100]}...")
        return default

def setup_driver():
    print("Setting up Chrome driver...")
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(3)
    print("Driver setup complete.")
    return driver

def get_page_count(driver):
    """Get total number of pages from pagination"""
    try:
        print("Fetching page count...")
        page_buttons = driver.find_elements(By.CSS_SELECTOR, "button[data-uxi-widget-type='paginationPageButton']")
        print(f"Found {len(page_buttons)} pages.")
        return len(page_buttons)
    except NoSuchElementException:
        print("No pagination found. Assuming single page.")
        return 1  # If no pagination found, assume single page

def process_page(driver, url):
    """Process a single page of results"""
    print(f"Processing page: {url}")
    jobs = []
    job_containers = driver.find_elements(By.CSS_SELECTOR, "li.css-1q2dra3")
    print(f"Found {len(job_containers)} job containers on this page.")
    
    for index, job in enumerate(job_containers):
        try:
            print(f"Processing job {index + 1} of {len(job_containers)}...")
            
            # Extract title and URL first as they're critical
            title_elem = job.find_element(By.CSS_SELECTOR, 'a[data-automation-id="jobTitle"]')
            title = title_elem.text
            job_url = title_elem.get_attribute('href')
            print(f"Job title: {title}")
            
            # Use safe extraction for other elements
            location = safe_find(job, 'div[data-automation-id="locations"] dd')
            time_type = safe_find(job, 'div[data-automation-id="time"] dd')
            posted = safe_find(job, 'div[data-automation-id="postedOn"] dd')
            req_id = safe_find(job, 'li.css-h2nt8k')
            
            # Get current timestamp
            now = datetime.now()
            job_data = {
                'scrape_date': now.strftime('%Y-%m-%d'),
                'title': title,
                'url': job_url,
                'source_page': url,
                'department': url.split('/')[-1].replace('_Careers', '').replace('_Staff', ''),
                'location': location,
                'time_type': time_type,
                'posted': posted,
                'requisition_id': req_id,
                'scrape_time': now.strftime('%H:%M:%S'),
                'scrape_day': now.strftime('%a')
            }
            jobs.append(job_data)
            print(f"Job {index + 1} processed successfully.")
            
        except Exception as job_error:
            print(f"Error processing job {index + 1} on {url}: {str(job_error)[:100]}...")
            continue
    
    print(f"Finished processing {len(jobs)} jobs on this page.")
    return jobs

def wait_for_page_change(driver, target_page):
    """Wait for the target page to become active"""
    print(f"Waiting for page {target_page} to load...")
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, f'button[aria-label="page {target_page}"].css-1p1egad')
            )
        )
        print(f"Page {target_page} loaded successfully.")
        return True
    except TimeoutException:
        print(f"Timeout waiting for page {target_page} to load.")
        return False

def scrape_jobs(driver):
    all_jobs = []
    
    for url in CAREER_PAGES:
        try:
            print(f"\nProcessing: {url}")
            driver.get(url)
            print(f"Page loaded: {url}")
            
            # Get total number of pages
            total_pages = get_page_count(driver)
            print(f"Found {total_pages} pages of results")
            
            for page_num in range(1, total_pages + 1):
                print(f"\nProcessing page {page_num} of {total_pages}")
                
                # Wait for page to fully load
                print("Waiting for job listings to load...")
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.css-1q2dra3"))
                )
                print("Job listings loaded.")
                
                # Process current page
                print("Processing jobs on current page...")
                page_jobs = process_page(driver, url)
                all_jobs.extend(page_jobs)
                print(f"Found {len(page_jobs)} jobs on current page")
                
                # If not last page, click next page button
                if page_num < total_pages:
                    try:
                        print("Preparing to navigate to the next page...")
                        # Find the next page button
                        next_button = driver.find_element(
                            By.CSS_SELECTOR, 
                            f'button[aria-label="page {page_num + 1}"][data-uxi-widget-type="paginationPageButton"]'
                        )
                        
                        # Scroll and click using JavaScript
                        print("Scrolling to the next page button...")
                        driver.execute_script("arguments[0].scrollIntoView();", next_button)
                        print("Clicking the next page button...")
                        driver.execute_script("arguments[0].click();", next_button)
                        
                        # Wait for the new page to become active
                        if not wait_for_page_change(driver, page_num + 1):
                            print(f"Failed to load page {page_num + 1}")
                            break
                            
                        # Additional wait for job listings to load
                        print("Waiting for job listings to load on the new page...")
                        time.sleep(1.5)
                        
                    except Exception as e:
                        print(f"Error navigating to page {page_num + 1}: {str(e)[:100]}...")
                        break
                    
        except TimeoutException:
            print(f"Timeout loading {url} - possible empty job list")
            continue
        except Exception as page_error:
            print(f"Critical error with {url}: {str(page_error)[:100]}...")
            continue
            
    return all_jobs

def validate_data(df):
    """Simple validation method to check if the scraped data meets certain criteria"""
    print("Validating scraped data...")
    if df.empty:
        raise ValueError("No data was scraped.")
    
    required_columns = ['title', 'url', 'location', 'time_type', 'posted', 'requisition_id', 'source_page', 'department']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    if df['title'].isnull().all():
        raise ValueError("No job titles were scraped.")
    
    print("Data validation passed.")


def generate_filename(base_name):
    """Generate a unique filename with rerun suffix if necessary."""
    now = datetime.now()
    timestamp = now.strftime("%m%d%y")  # Format as mmddyy
    filename = f"{base_name}_{timestamp}.xlsx"  # Change extension to .xlsx
    
    # Check if the file already exists
    rerun_count = 0
    while os.path.exists(filename):
        rerun_count += 1
        if rerun_count == 1:
            filename = f"{base_name}_{timestamp}_rerun.xlsx"
        else:
            filename = f"{base_name}_{timestamp}_{'re' * rerun_count}run.xlsx"
    
    return filename


def main():
    print("Starting script...")
    driver = setup_driver()
    try:
        print("Scraping jobs...")
        jobs = scrape_jobs(driver)
        df = pd.DataFrame(jobs)
        
        # Clean department names
        print("Cleaning department names...")
        df['department'] = df['department'].replace({
            'TCCS_Careers': 'TCCS',
            'CGU_Careers': 'CGU',
            'HMC_Careers': 'HMC',
            'SCR_Career_Staff': 'SCR',
            'CMC_Staff': 'CMC',
            'PIT_Staff': 'PIT',
            'KGI_Careers': 'KGI',
            'POM_Careers': 'POM'
        })
        
        # Validate the data
        validate_data(df)
        
        # Generate unique filename
        base_name = "ClaremontCollegesJobs"
        filename = generate_filename(base_name)
        
        # Save to Excel
        print("Saving data to Excel...")
        df.to_excel(filename, index=False, engine="openpyxl")  # Save as .xlsx
        print(f"\nSuccess! Saved {len(df)} jobs to '{filename}'. Missing data counts:")
        print(df.isnull().sum())
        
    finally:
        print("Quitting driver...")
        driver.quit()
        print("Script execution complete.")

if __name__ == '__main__':
    main()
