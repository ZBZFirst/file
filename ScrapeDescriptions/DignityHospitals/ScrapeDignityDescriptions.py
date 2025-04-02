from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import os
from pathlib import Path
from datetime import datetime  # Import datetime for timestamp generation

def setup_driver():
    """Initialize and configure the Selenium WebDriver."""
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    
    # Suppress unnecessary browser logs
    options.add_argument("--log-level=3")  # Only show fatal errors
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    driver = webdriver.Chrome(options=options)
    driver.implicitly_wait(2)
    return driver

def has_section16(driver):
    """Check if the page uses section16 format using JavaScript."""
    return driver.execute_script(
        "return !!document.querySelector('div.section16.section-spacing');"
    )

def has_ajd(driver):
    """Check if the page uses AJD format using JavaScript."""
    return driver.execute_script(
        "return !!document.querySelector('div.ajd_overview__info, section.ajd_job-details');"
    )

def scrape_section16(driver):
    """Scrape the section16 format."""
    try:
        section16 = driver.find_element(By.CSS_SELECTOR, "div.section16.section-spacing")
        return {'section16_html': section16.get_attribute("outerHTML").strip()}
    except Exception as e:
        print("Section16 not found: Skipping (expected for AJD pages).")
        return None

def scrape_ajd_sections(driver):
    """Optimized AJD scraping with faster element detection."""
    results = {'overview_html': None, 'job_details_html': None}
    
    # Try to get overview section
    try:
        overview = driver.find_element(By.CSS_SELECTOR, "div.ajd_overview__info")
        results['overview_html'] = overview.get_attribute("outerHTML").strip()
    except Exception as e:
        print(f"AJD overview not found: {str(e)[:200]}")
    
    # Try to get job details section
    try:
        job_container = driver.find_element(By.CSS_SELECTOR, "section.ajd_job-details")
        results['job_details_html'] = job_container.get_attribute('outerHTML').strip()
    except Exception as e:
        print(f"AJD job details not found: {str(e)[:200]}")
    
    return results if any(results.values()) else None

def scrape_job_sections(driver, url):
    """Optimized scraping flow."""
    try:
        driver.get(url)
        
        # Wait for page to load
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState === 'complete'")
        )

        # Check for section16 first
        if has_section16(driver):
            return scrape_section16(driver)
        
        # Check for AJD format
        if has_ajd(driver):
            return scrape_ajd_sections(driver)

        return {'error': 'No matching format found'}

    except Exception as e:
        print(f"Error scraping {url}: {str(e)[:200]}")
        return {'error': str(e)[:200]}

def scrape_pay_range(driver):
    """Scrape the pay range information from the page."""
    try:
        pay_range_element = driver.find_element(By.CSS_SELECTOR, "p.job-info.posted-pay-range")
        return pay_range_element.text.strip()
    except Exception as e:
        print(f"Pay range not found: {str(e)[:200]}")
        return None

# Configure paths
parent_dir = Path(__file__).resolve().parent.parent.parent

# Generate dynamic timestamp for the input filename
timestamp = datetime.now().strftime("%m%d%Y")  # Format: MMDDYYYY
input_filename = f"DignityHospitals_{timestamp}.xlsx"  # Dynamic filename
input_path = parent_dir / "ScrapeLinks" / "DignityHospitals" / input_filename  # Input file path

# Generate output filename by adding "description" to the input filename
output_filename = f"DignityHospitals_{timestamp}_description.xlsx"  # Add "description" to the filename
output_path = parent_dir / "ScrapeDescriptions" / "DignityHospitals" / output_filename  # Output file path

# Initialize driver
driver = setup_driver()

try:
    # Prepare DataFrame
    if os.path.exists(output_path):
        df = pd.read_excel(output_path)  # Updated to read Excel
        for col in ['section16_html', 'overview_html', 'job_details_html', 'job-info posted-pay-range']:
            if col not in df.columns:
                df[col] = None
    else:
        df = pd.read_excel(input_path)  # Updated to read Excel
        df['section16_html'] = None
        df['overview_html'] = None
        df['job_details_html'] = None
        df['job-info posted-pay-range'] = None  # New column for pay range
        output_path.parent.mkdir(parents=True, exist_ok=True)

    # Process rows with individual error handling
    processed = 0
    for index, row in df.iterrows():
        if pd.isna(row['section16_html']) and pd.isna(row['overview_html']):
            url = row['url']
            print(f"Processing {index}: {url}")
            
            try:
                driver.get(url)
                
                # Wait for page to load
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState === 'complete'")
                )

                # Scrape pay range
                pay_range = scrape_pay_range(driver)
                if pay_range:
                    df.at[index, 'job-info posted-pay-range'] = pay_range

                # Scrape job sections
                result = scrape_job_sections(driver, url)
                
                if result:
                    # Handle section16 result
                    if 'section16_html' in result:
                        df.at[index, 'section16_html'] = result['section16_html']
                        processed += 1
                    
                    # Handle AJD sections
                    elif 'overview_html' in result or 'job_details_html' in result:
                        df.at[index, 'overview_html'] = result.get('overview_html')
                        df.at[index, 'job_details_html'] = result.get('job_details_html')
                        processed += 1
                    
                    # Handle errors
                    elif 'error' in result:
                        df.at[index, 'section16_html'] = f"SCRAPE_FAILED: {result['error']}"
                else:
                    df.at[index, 'section16_html'] = "SCRAPE_FAILED: No results"
                
                # Save after each processed row
                df.to_excel(output_path, index=False)  # Updated to write Excel
                time.sleep(0.5)  # Reduced sleep time
                
            except Exception as e:
                print(f"Critical error processing row {index}: {str(e)[:200]}")
                df.at[index, 'section16_html'] = f"CRITICAL_ERROR: {str(e)[:200]}"
                df.to_excel(output_path, index=False)  # Updated to write Excel

    print(f"\nCompleted! Processed {processed} new records")

finally:
    driver.quit()
