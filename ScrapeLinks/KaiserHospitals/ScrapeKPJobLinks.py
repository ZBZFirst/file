from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException, ElementClickInterceptedException  
import time
from datetime import datetime
import os
import pandas as pd

# Function to load the last scraped page from a checkpoint file
def load_checkpoint():
    if os.path.exists("checkpoint.txt"):
        with open("checkpoint.txt", "r") as file:
            return int(file.read().strip())
    return 1  # Start from page 1 if no checkpoint exists

# Function to save the current page to a checkpoint file
def save_checkpoint(page):
    with open("checkpoint.txt", "w") as file:
        file.write(str(page))

def handle_not_now_button(driver):
    try:
        # Wait a short time for the button to potentially appear
        not_now_button = WebDriverWait(driver, 3).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "button.btn-not-now"))
        )
        
        # Make sure button is visible and clickable
        if not_now_button.is_displayed() and not_now_button.is_enabled():
            # Scroll into view and click using JavaScript for reliability
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", not_now_button)
            driver.execute_script("arguments[0].click();", not_now_button)
            print("Clicked 'Not Now' button")
            time.sleep(1)  # Give time for any modal to close
            return True
    except TimeoutException:
        # Button didn't appear, which is fine
        return False
    except Exception as e:
        print(f"Error handling 'Not Now' button: {e}")
        return False

# Initialize the WebDriver
driver = webdriver.Chrome()
driver.get("https://www.kaiserpermanentejobs.org/search-jobs/")

try:
    # New Step: Handle cookie consent popup
    print("Step 1: Handling cookie consent...")
    try:
        # Wait for the GDPR banner and click Accept using the correct ID
        cookie_accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "igdpr-button"))
        )
        # Use JavaScript click to avoid potential overlay issues
        driver.execute_script("arguments[0].click();", cookie_accept_button)
        print("Cookie consent accepted.")
        
        # Wait for banner to disappear (optional but recommended)
        WebDriverWait(driver, 1).until(
            EC.invisibility_of_element_located((By.ID, "igdpr-alert"))
        )
        time.sleep(0.5)  # Small pause for any final UI updates
    except (NoSuchElementException, TimeoutException):
        print("No cookie consent popup found or already dismissed.")

    print("Step 2: Page loaded successfully.")
    # 1. Extract initial data from the page (before filtering)
    print("Step 2: Extracting initial data from the page...")
    results_section = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "search-results"))
    )

    # Initialize variables
    total_results = results_section.get_attribute("data-total-results")
    total_job_results = results_section.get_attribute("data-total-job-results")
    total_pages = int(results_section.get_attribute("data-total-pages"))
    records_per_page = results_section.get_attribute("data-records-per-page")

    print(f"Initial Data:")
    print(f"Total Results: {total_results}")
    print(f"Total Job Results: {total_job_results}")
    print(f"Total Pages: {total_pages}")
    print(f"Records Per Page: {records_per_page}")

    # 2. Scroll to the "State" filter button and click it
    print("Step 3: Attempting to find and click the 'State' filter button...")
    state_toggle = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "region-toggle"))
    )
    # Scroll into view using JavaScript
    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", state_toggle)
    time.sleep(1)  # Allow time for scrolling to finish
    state_toggle.click()
    print("Step 3: 'State' filter button clicked successfully.")

    # 3. Click the California filter checkbox
    print("Step 4: Attempting to find and click the California filter checkbox...")
    california_filter = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.ID, "region-filter-0"))
    )
    driver.execute_script("arguments[0].click();", california_filter)  # Click via JavaScript to bypass overlays
    print("Step 4: California filter checkbox clicked successfully.")

    # 4. Wait for the results to fully update after filtering
    print("Step 5: Waiting for results to update after filtering...")

    # Function to wait for the results to stabilize
    def wait_for_results_to_stabilize(driver, timeout=30):
        start_time = time.time()
        previous_total_jobs = None

        while time.time() - start_time < timeout:
            results_section = driver.find_element(By.ID, "search-results")
            current_total_jobs = results_section.get_attribute("data-total-job-results")

            if current_total_jobs == previous_total_jobs:
                print("Results have stabilized.")
                return True

            previous_total_jobs = current_total_jobs
            time.sleep(1)  # Wait before checking again

        print("Timed out waiting for results to stabilize.")
        return False

    # Wait for results to stabilize
    if wait_for_results_to_stabilize(driver):
        print("Step 5: Results updated successfully. Filter applied!")
    else:
        raise TimeoutException("Results did not stabilize within the timeout period.")

    def wait_for_pagination_ready(driver, timeout=30):
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script(
                "return document.readyState === 'complete' && "
                "typeof jQuery !== 'undefined' && "
                "jQuery('.pagination-controls:visible').length > 0 && "
                "!jQuery('#search-results').hasClass('loading')"
            )
        )    

    # 5. Extract updated data after filtering
    print("Step 6: Extracting updated data after filtering...")
    results_section = driver.find_element(By.ID, "search-results")
    total_results = results_section.get_attribute("data-total-results")
    total_job_results = results_section.get_attribute("data-total-job-results")
    total_pages = int(results_section.get_attribute("data-total-pages"))
    records_per_page = results_section.get_attribute("data-records-per-page")

    print(f"Updated Data:")
    print(f"Total Results: {total_results}")
    print(f"Total Job Results: {total_job_results}")
    print(f"Total Pages: {total_pages}")
    print(f"Records Per Page: {records_per_page}")

    # 6. Load the last scraped page from the checkpoint
    current_page = load_checkpoint()
    print(f"Resuming from page {current_page}...")

    # 7. Navigate to the desired page (e.g., page 34)
    if current_page > 1:
        print(f"Navigating to page {current_page}...")
        retries = 3
        for attempt in range(retries):
            try:
                # Re-locate elements after potential DOM changes
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located((By.ID, "pagination-current-bottom"))
                )
                
                # Scroll to pagination input and set value using JavaScript
                pagination_input = driver.find_element(By.ID, "pagination-current-bottom")
                driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", pagination_input)
                driver.execute_script(f"arguments[0].value = '{current_page}';", pagination_input)
                
                # Trigger any required events (e.g., input, change)
                driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));", pagination_input)
                driver.execute_script("arguments[0].dispatchEvent(new Event('change', { bubbles: true }));", pagination_input)
                time.sleep(1)  # Allow time for UI update
                
                # Click the Go button using JavaScript
                go_button = driver.find_element(By.CSS_SELECTOR, "button.pagination-page-jump")
                driver.execute_script("arguments[0].click();", go_button)
                
                # Wait for page load verification
                WebDriverWait(driver, 10).until(
                    lambda d: d.find_element(By.ID, "search-results").get_attribute("data-current-page") == str(current_page)
                )
                print(f"Successfully navigated to page {current_page}.")
                break
            except Exception as e:
                print(f"Navigation attempt {attempt + 1} failed: {str(e)[:100]}...")
                if attempt == retries - 1:
                    raise
                print("Refreshing page and retrying...")
                driver.refresh()
                time.sleep(1)
                
                # Re-apply filters properly after refresh
                try:
                    # Re-open State filter panel
                    state_toggle = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "region-toggle"))
                    )
                    driver.execute_script("arguments[0].click();", state_toggle)
                    # Re-check California filter
                    california_filter = WebDriverWait(driver, 10).until(
                        EC.element_to_be_clickable((By.ID, "region-filter-0"))
                    )
                    driver.execute_script("arguments[0].click();", california_filter)
                    wait_for_results_to_stabilize(driver)
                except Exception as filter_error:
                    print(f"Failed to re-apply filters: {filter_error}")

    # 8. Scrape all pages of job listings
    print("Step 7: Scraping job listings from all pages...")
    all_jobs = []

    while current_page <= total_pages:
        print(f"Scraping page {current_page} of {total_pages}...")

        # Function to scrape job listings from the current page
        def scrape_jobs():
            job_listings = driver.find_elements(By.CSS_SELECTOR, "#search-results li")
            for job in job_listings:
                try:
                    # Extract job title
                    title = job.find_element(By.TAG_NAME, "h2").text
                except NoSuchElementException:
                    title = "N/A"

                try:
                    # Extract job URL
                    url = job.find_element(By.TAG_NAME, "a").get_attribute("href")
                except NoSuchElementException:
                    url = "N/A"

                try:
                    # Extract job locations
                    locations = job.find_elements(By.CLASS_NAME, "job-location")
                    primary_location = locations[0].text if len(locations) > 0 else "N/A"
                    secondary_location = locations[1].text if len(locations) > 1 else "N/A"
                except NoSuchElementException:
                    primary_location = "N/A"
                    secondary_location = "N/A"

                try:
                    # Extract job posted date
                    date_posted = job.find_element(By.CLASS_NAME, "job-date-posted").text
                except NoSuchElementException:
                    date_posted = "N/A"

                # Get current timestamp and format it
                scrape_timestamp = datetime.now().strftime("%H:%M:%S")
                scrape_date = datetime.now().strftime("%m-%d-%Y")  # MM-DD-YYYY format
                scrape_day = datetime.now().strftime("%a")  # Abbreviated day (e.g., Mon, Tue)

                # Add job details to the list only if not all values are "N/A"
                if not all(value == "N/A" for value in [title, url, primary_location, secondary_location, date_posted]):
                    all_jobs.append([
                        scrape_timestamp, title, url, primary_location, secondary_location,
                        date_posted, scrape_date, scrape_day
                    ])

        # Retry scraping if stale elements are encountered
        retries = 5  # Increased number of retries
        for attempt in range(retries):
            try:
                # Wait for job listings to load
                WebDriverWait(driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "#search-results li"))
                )
                scrape_jobs()
                break  # Exit retry loop if successful
            except StaleElementReferenceException:
                print(f"Stale element detected. Retrying... ({attempt + 1}/{retries})")
                time.sleep(1)  # Wait 5 seconds before retrying
            except Exception as e:
                print(f"Unexpected error during job listing extraction: {e}")
                time.sleep(1)  # Wait 5 seconds before retrying

        # Save the current page to the checkpoint file
        save_checkpoint(current_page)

        # Go to the next page if not on the last page
        if current_page < total_pages:
            retries = 5  # Number of retries for navigation
            for attempt in range(retries):
                try:
                    # Handle the "Not Now" button if it appears
                    handle_not_now_button(driver)

                    # Wait for the "Next" button to be clickable
                    next_button = WebDriverWait(driver, 20).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.next"))
                    )
                    # Scroll the "Next" button into view and click it
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", next_button)
                    driver.execute_script("arguments[0].click();", next_button)

                    # Wait for the next page to load by checking the updated page number
                    WebDriverWait(driver, 20).until(
                        lambda d: d.find_element(By.ID, "search-results").get_attribute("data-current-page") == str(current_page + 1)
                    )
                    current_page += 1
                    break  # Exit the retry loop if successful
                except StaleElementReferenceException:
                    print(f"Stale element detected while navigating to the next page. Retrying... ({attempt + 1}/{retries})")
                    time.sleep(1)  # Wait 5 seconds before retrying
                except Exception as e:
                    print(f"Error navigating to the next page: {e}")
                    time.sleep(1)  # Wait 5 seconds before retrying
            else:
                print("Failed to navigate to the next page after multiple retries. Exiting pagination loop.")
                break  # Exit the loop if navigation fails after all retries
        else:
            break  # Exit the loop if on the last page

    # 9. Save the scraped jobs to an Excel file
    print("Step 8: Saving scraped jobs to an Excel file...")

    # Define the filename with the current date in MM-DD-YYYY format
    scrape_date = datetime.now().strftime("%m%d%Y")
    filename = f"kpjobs_{scrape_date}.xlsx"  # Change extension to .xlsx

    # Convert the list of jobs to a DataFrame
    df = pd.DataFrame(all_jobs, columns=[
        "Timestamp", "Title", "URL", "Location", "Setting",
        "Date Posted", "Scrape Date", "Scrape Day"
    ])

    # Save the DataFrame to an Excel file
    df.to_excel(filename, index=False, engine="openpyxl")
    print(f"Scraped jobs saved to {filename}")

except Exception as e:
    print(f"Error: {e}")
finally:
    # Keep the browser open for inspection
    input("Press Enter to close the browser...")
    driver.quit()
