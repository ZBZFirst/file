from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime
import signal
import sys
import pandas as pd  # Add pandas for Excel handling

# Initialize WebDriver
driver = webdriver.Chrome()
driver.maximize_window()

# Global variable for data persistence
ALL_JOBS = []
CURRENT_PAGE = 1
FILENAME = ""

def signal_handler(sig, frame):
    """Handle Ctrl+C interrupts and save progress"""
    print("\n\n!!! INTERRUPT RECEIVED - SAVING PROGRESS !!!")
    save_to_excel(ALL_JOBS)  # Updated function name
    driver.quit()
    sys.exit(0)

def create_filename():
    """Generate unique timestamped filename"""
    timestamp = datetime.now().strftime("%m%d%Y")
    return f"DignityHospitals_{timestamp}.xlsx"  # Change extension to .xlsx

def save_to_excel(jobs):
    """Save data to Excel with error handling"""
    if not jobs:
        print("No data to save!")
        return

    global FILENAME
    if not FILENAME:
        FILENAME = create_filename()

    try:
        # Convert the list of dictionaries to a DataFrame
        df = pd.DataFrame(jobs)
        
        # Save the DataFrame to an Excel file
        df.to_excel(FILENAME, index=False, engine="openpyxl")
        print(f"\n💾 DATA SAVED: {len(jobs)} records -> {FILENAME}")
    except Exception as e:
        print(f"Failed to save data: {str(e)}")

def debug_print(message, success=True):
    """Enhanced debugging output"""
    status = "✅" if success else "❌"
    print(f"{status} {datetime.now().strftime('%H:%M:%S')} - {message}")

def setup_scraper():
    """Initial setup and filtering"""
    try:
        # Register interrupt handler
        signal.signal(signal.SIGINT, signal_handler)

        debug_print("Navigating to careers page")
        driver.get("https://www.commonspirit.careers/search-jobs")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "search-results")))
        
        # Get initial job count before filtering
        initial_total_jobs = int(driver.find_element(By.ID, "search-results").get_attribute("data-total-job-results"))
        debug_print(f"Initial unfiltered jobs: {initial_total_jobs}")

        debug_print("Handling state filter")
        state_filter = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((By.ID, "region-toggle")))
        
        if "expandable-child-open" not in state_filter.get_attribute("class"):
            driver.execute_script("arguments[0].click();", state_filter)
        
        debug_print("Applying California filter")
        california_checkbox = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.ID, "region-filter-2")))
        driver.execute_script("arguments[0].click();", california_checkbox)
        
        # Wait for results to change from initial count
        WebDriverWait(driver, 3).until(
            lambda d: int(d.find_element(By.ID, "search-results").get_attribute("data-total-job-results")) < initial_total_jobs
        )
        
        # Verify final filtered count
        filtered_total = int(driver.find_element(By.ID, "search-results").get_attribute("data-total-job-results"))
        if filtered_total >= initial_total_jobs:
            raise Exception("Filter likely failed - filtered count not less than initial count")
        
        debug_print(f"Filtered jobs count: {filtered_total} (was {initial_total_jobs})")

    except Exception as e:
        debug_print(f"Setup failed: {str(e)}", False)
        driver.quit()
        sys.exit(1)

def scrape_page():
    """Scrape current page and return jobs"""
    try:
        WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "#search-results a[data-job-id]")))
        
        jobs = driver.find_elements(By.CSS_SELECTOR, "#search-results a[data-job-id]")
        debug_print(f"Found {len(jobs)} job listings")
        
        return [extract_job_data(job) for job in jobs if extract_job_data(job)]
    except Exception as e:
        debug_print(f"Scraping failed: {str(e)}", False)
        return []

def extract_job_data(job_element):
    """Extract detailed job information"""
    try:
        return {
            'scraped_date': datetime.now().strftime("%Y-%m-%d"),
            'title': job_element.find_element(By.CSS_SELECTOR, "h2.headline__medium").text.strip(),
            'department': job_element.find_element(By.CSS_SELECTOR, "span.job-department").text.strip(),
            'location': job_element.find_element(By.CSS_SELECTOR, "span.job-location").text.strip(),
            'job_id': job_element.get_attribute("data-job-id"),
            'url': job_element.get_attribute("href"),
            'scraped_time': datetime.now().strftime("%H:%M:%S")
        }
    except Exception as e:
        debug_print(f"Failed to extract job: {str(e)}", False)
        return None

def paginate():
    """Handle pagination with retries, including View More Jobs button"""
    global CURRENT_PAGE
    try:
        _, total_pages = get_pagination()
        if CURRENT_PAGE >= total_pages:
            return False
        
        # First try to click the "View More Jobs" button if it exists
        try:
            view_more_btn = WebDriverWait(driver, 2).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-learn-more.pagination-view-more")))
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", view_more_btn)
            driver.execute_script("arguments[0].click();", view_more_btn)
            WebDriverWait(driver, 3).until(
                lambda d: d.find_element(By.ID, "search-results").get_attribute("data-current-page") != str(CURRENT_PAGE)
            )
            CURRENT_PAGE += 1
            debug_print(f"Clicked 'View More Jobs' and moved to page {CURRENT_PAGE}")
            return True
        except:
            # If View More button not found, proceed with normal pagination
            pass
        
        # Normal pagination flow
        next_btn = WebDriverWait(driver, 3).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next:not([disabled])")))
        
        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
        driver.execute_script("arguments[0].click();", next_btn)
        
        WebDriverWait(driver, 20).until(
            lambda d: d.find_element(By.ID, "search-results").get_attribute("data-current-page") != str(CURRENT_PAGE)
        )
        CURRENT_PAGE += 1
        debug_print(f"Moved to page {CURRENT_PAGE}")
        return True
    except Exception as e:
        debug_print(f"Pagination failed: {str(e)}", False)
        return False

def get_pagination():
    """Get current pagination status"""
    try:
        results = driver.find_element(By.ID, "search-results")
        return (
            int(results.get_attribute("data-current-page")),
            int(results.get_attribute("data-total-pages"))
        )
    except:
        return (1, 1)

# Main execution flow
if __name__ == "__main__":
    setup_scraper()
    
    try:
        while True:
            page_jobs = scrape_page()
            if page_jobs:
                ALL_JOBS.extend(page_jobs)
                save_to_excel(ALL_JOBS)  # Updated function name
            
            if not paginate():
                break
            
            time.sleep(1)  # Be polite to the server

    except Exception as e:
        debug_print(f"Unexpected error: {str(e)}", False)
    finally:
        driver.quit()
        if ALL_JOBS:
            print(f"\n🏁 FINAL RESULTS: {len(ALL_JOBS)} jobs saved to {FILENAME}")
        else:
            print("\n⚠️ No jobs collected during this session")
