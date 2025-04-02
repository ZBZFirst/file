from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import csv
from datetime import datetime
import pandas as pd

# Set up Selenium with Chrome
chrome_options = Options()

# Initialize the WebDriver
driver = webdriver.Chrome()

# URL of the webpage
url = "https://jobs.universityofcalifornia.edu/site/advancedsearch?keywords=&Campus%5Bcampus_id%5D=&multiple_locations=0&search="

# Open the webpage
driver.get(url)

# List to store job data
jobs_data = []

# Get the current date and time
current_datetime = datetime.now()
scrape_date = current_datetime.strftime("%Y-%m-%d")  # Format: YYYY-MM-DD
scrape_time = current_datetime.strftime("%H:%M:%S")  # Format: HH:MM:SS

# Excel file to save all data
excel_filename = f"ucjobs_{current_datetime.strftime('%m%d%Y')}.xlsx"

# Loop through all pages
while True:
    # Wait for the job postings to load
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "jobspot"))
        )
    except TimeoutException:
        print("Timed out waiting for job postings to load.")
        break

    # Find all job postings on the current page
    jobspots = driver.find_elements(By.CLASS_NAME, "jobspot")

    # Iterate through each job posting
    for job in jobspots:
        try:
            # Extract job title and link
            title_element = job.find_element(By.CLASS_NAME, "jtitle")
            job_title = title_element.text.strip()
            job_link = title_element.get_attribute("href")
        except NoSuchElementException:
            job_title = ""
            job_link = ""

        try:
            # Extract location
            location = job.find_element(By.CLASS_NAME, "jloc").text.strip()
        except NoSuchElementException:
            location = ""

        try:
            # Extract category
            category = job.find_element(By.CLASS_NAME, "jfamily").text.strip()
        except NoSuchElementException:
            category = ""

        try:
            # Extract requisition
            requisition = job.find_element(By.CLASS_NAME, "jreq").text.strip()
        except NoSuchElementException:
            requisition = ""

        try:
            # Extract posting date
            posting_date = job.find_element(By.CLASS_NAME, "jclose").text.strip()
        except NoSuchElementException:
            posting_date = ""

        try:
            # Extract job description
            description = job.find_element(By.CLASS_NAME, "jdesc").text.strip()
        except NoSuchElementException:
            description = ""

        # Append the data to the list with scrape date and time
        jobs_data.append([job_title, job_link, location, category, requisition, posting_date, description, scrape_date, scrape_time])

    # Convert the list to a pandas DataFrame
    df = pd.DataFrame(jobs_data, columns=["Job Title", "Job Link", "Location", "Category", "Requisition", "Posting Date", "Description", "Scrape Date", "Scrape Time"])

    # Reorganize the columns (example: move "Scrape Date" and "Scrape Time" to the front)
    df = df[["Scrape Date", "Job Title", "Location", "Category", "Requisition", "Posting Date", "Description", "Job Link", "Scrape Time"]]

    # Save the DataFrame to an Excel file after each page
    df.to_excel(excel_filename, index=False)
    print(f"Data saved to {excel_filename} after processing a page.")

    # Check if the "Next" button exists
    try:
        next_button = driver.find_element(By.LINK_TEXT, "Next")
        next_button.click()
    except NoSuchElementException:
        print("No more pages. Exiting.")
        break

# Close the browser
driver.quit()

print(f"All data saved to {excel_filename}")
