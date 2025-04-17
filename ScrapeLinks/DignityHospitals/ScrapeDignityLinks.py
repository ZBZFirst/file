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

# Add these new functions at the top with other function definitions
def load_existing_data(filename):
    """Load existing jobs to avoid duplicates when restarting"""
    try:
        df = pd.read_excel(filename)
        print(f"Loaded {len(df)} existing jobs from {filename}")
        return df.to_dict('records')
    except FileNotFoundError:
        print("No existing data file found - starting fresh")
        return []
    except Exception as e:
        print(f"Error loading existing data: {e}")
        return []

def get_current_progress():
    """Get current scraping progress including page info"""
    current_page, total_pages = get_pagination()
    return {
        'current_page': current_page,
        'total_pages': total_pages,
        'jobs_collected': len(ALL_JOBS),
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

def print_progress():
    """Print current scraping progress"""
    progress = get_current_progress()
    print(f"\n📊 Progress: Page {progress['current_page']}/{progress['total_pages']} | Jobs: {progress['jobs_collected']} | {progress['timestamp']}")

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

# Modify the save_to_excel function to include progress tracking
def save_to_excel(jobs):
    """Save data to Excel with progress tracking"""
    if not jobs:
        print("No data to save!")
        return

    global FILENAME
    if not FILENAME:
        FILENAME = create_filename()

    try:
        df = pd.DataFrame(jobs)
        
        # Create Excel writer object
        with pd.ExcelWriter(FILENAME, engine='openpyxl') as writer:
            # Save jobs data
            df.to_excel(writer, sheet_name='Jobs', index=False)
            
            # Save progress metadata
            progress = get_current_progress()
            pd.DataFrame([progress]).to_excel(writer, sheet_name='Progress', index=False)
        
        print(f"\n💾 DATA SAVED: {len(jobs)} records (Page {progress['current_page']}/{progress['total_pages']}) -> {FILENAME}")
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
    """
    Handle pagination with adaptive strategy selection
    - Remembers which strategy worked last and reuses it
    - Only falls back to alternatives when the preferred strategy fails
    - Implements robust error recovery
    """
    global CURRENT_PAGE
    
    # Static variables to remember successful strategy between calls
    if not hasattr(paginate, 'preferred_strategy'):
        paginate.preferred_strategy = None  # None, 'view_more', or 'traditional'
        paginate.consecutive_failures = 0
    
    max_retries = 3
    retry_delay = 2  # seconds between retries
    max_consecutive_failures = 2  # Switch strategy after this many failures
    
    strategies = ['view_more', 'traditional']
    
    # If we have a preferred strategy, try it first
    if paginate.preferred_strategy:
        strategies.remove(paginate.preferred_strategy)
        strategies.insert(0, paginate.preferred_strategy)
    
    for attempt in range(max_retries):
        try:
            current_page, total_pages = get_pagination()
            
            # Check if we've reached the end
            if current_page >= total_pages:
                debug_print(f"Already on last page ({current_page}/{total_pages})")
                return False
                
            debug_print(f"Attempting pagination (Attempt {attempt + 1}/{max_retries})")
            debug_print(f"Current progress: Page {current_page} of {total_pages}")
            debug_print(f"Preferred strategy: {paginate.preferred_strategy or 'not set'}")
            
            # Try each strategy in order of preference
            for strategy in strategies:
                try:
                    if strategy == 'view_more':
                        debug_print("Trying 'View More Jobs' button...")
                        view_more_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn-learn-more.pagination-view-more")))
                        
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", view_more_btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", view_more_btn)
                        
                        WebDriverWait(driver, 10).until(
                            lambda d: int(d.find_element(By.ID, "search-results").get_attribute("data-current-page")) > current_page
                        )
                        
                        CURRENT_PAGE = current_page + 1
                        debug_print(f"Success with 'View More' - Now on page {CURRENT_PAGE}")
                        
                        # Update preferred strategy and reset failure count
                        if paginate.preferred_strategy != 'view_more':
                            debug_print("Setting 'view_more' as preferred strategy")
                            paginate.preferred_strategy = 'view_more'
                        paginate.consecutive_failures = 0
                        return True
                        
                    elif strategy == 'traditional':
                        debug_print("Trying traditional pagination...")
                        next_btn = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next:not([disabled])")))
                        
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_btn)
                        time.sleep(0.5)
                        driver.execute_script("arguments[0].click();", next_btn)
                        
                        WebDriverWait(driver, 15).until(
                            lambda d: int(d.find_element(By.ID, "search-results").get_attribute("data-current-page")) > current_page
                        )
                        
                        CURRENT_PAGE = current_page + 1
                        debug_print(f"Success with traditional pagination - Now on page {CURRENT_PAGE}")
                        
                        # Update preferred strategy and reset failure count
                        if paginate.preferred_strategy != 'traditional':
                            debug_print("Setting 'traditional' as preferred strategy")
                            paginate.preferred_strategy = 'traditional'
                        paginate.consecutive_failures = 0
                        return True
                        
                except Exception as strategy_error:
                    debug_print(f"Strategy '{strategy}' failed: {str(strategy_error)[:100]}", False)
                    paginate.consecutive_failures += 1
                    
                    # If preferred strategy is failing consistently, reset it
                    if (paginate.preferred_strategy == strategy and 
                        paginate.consecutive_failures >= max_consecutive_failures):
                        debug_print(f"Preferred strategy failed {paginate.consecutive_failures} times - resetting preference")
                        paginate.preferred_strategy = None
                        paginate.consecutive_failures = 0
                    
                    continue
            
            # If all strategies failed
            debug_print("All pagination strategies failed on this attempt", False)
            
        except Exception as e:
            debug_print(f"Pagination error: {str(e)[:100]}", False)
            
            # Special handling for stale element errors
            if "stale element reference" in str(e):
                debug_print("Encountered stale element - refreshing page state...")
                try:
                    driver.refresh()
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.ID, "search-results")))
                    CURRENT_PAGE = int(driver.find_element(By.ID, "search-results").get_attribute("data-current-page"))
                    debug_print(f"Recovered to page {CURRENT_PAGE}")
                except:
                    debug_print("Failed to recover from stale element", False)
            
        # Wait before retrying
        if attempt < max_retries - 1:
            debug_print(f"Waiting {retry_delay} seconds before retry...")
            time.sleep(retry_delay)
    
    debug_print(f"Failed to paginate after {max_retries} attempts", False)
    return False

def get_pagination():
    try:
        results = driver.find_element(By.ID, "search-results")
        return (
            int(results.get_attribute("data-current-page")),
            int(results.get_attribute("data-total-pages"))
        )
    except:
        return (1, 1)

# Modify the main execution flow
if __name__ == "__main__":
    # Initialize with restart capability
    FILENAME = create_filename()
    ALL_JOBS = load_existing_data(FILENAME)
    
    # Get starting page from existing data if available
    if ALL_JOBS:
        try:
            progress_df = pd.read_excel(FILENAME, sheet_name='Progress')
            CURRENT_PAGE = progress_df['current_page'].iloc[0]
            print(f"Resuming from page {CURRENT_PAGE}")
        except:
            CURRENT_PAGE = 1
            print("No progress data found - starting from page 1")
    
    setup_scraper()
    
    try:
        while True:
            print_progress()  # Show progress before each page
            
            page_jobs = scrape_page()
            if page_jobs:
                ALL_JOBS.extend(page_jobs)
                # Save every page (or adjust to save every N pages)
                save_to_excel(ALL_JOBS)
            
            if not paginate():
                break
            
            time.sleep(1)  # Be polite to the server

    except Exception as e:
        debug_print(f"Unexpected error: {str(e)}", False)
        # Save progress when crashing
        save_to_excel(ALL_JOBS)
    finally:
        driver.quit()
        if ALL_JOBS:
            print(f"\n🏁 FINAL RESULTS: {len(ALL_JOBS)} jobs saved to {FILENAME}")
            print(f"📋 Pages processed: {get_current_progress()['current_page']}/{get_current_progress()['total_pages']}")
        else:
            print("\n⚠️ No jobs collected during this session")
