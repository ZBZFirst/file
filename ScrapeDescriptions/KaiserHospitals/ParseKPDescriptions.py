import pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime

# Get the current date in the required format (e.g., "03182025" for March 18, 2025)
current_date = datetime.now().strftime('%m%d%Y')

# Construct the input filename dynamically
input_filename = f'kpjobs_{current_date}_description.xlsx'

# Load the Excel file
df = pd.read_excel(input_filename)

# Function to extract job details from the HTML
def extract_job_details(html):
    if pd.isna(html):  # Skip NaN values
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    details = {}

    # Extract from <div class="ats-extras">
    ats_extras = soup.find('div', class_='ats-extras')
    if ats_extras:
        for span in ats_extras.find_all('span', class_='job-info'):
            key = span.find('strong').get_text(strip=True).replace(':', '').strip()
            value = span.get_text(strip=True).replace(span.find('strong').get_text(strip=True), '').strip()
            details[key.lower().replace(' ', '_')] = value

    # Extract from <div class="job-description__info-wrap">
    info_wrap = soup.find('div', class_='job-description__info-wrap')
    if info_wrap:
        for span in info_wrap.find_all('span', class_='job-info'):
            key = span.find('b').get_text(strip=True).lower().replace(' ', '_')
            value = span.get_text(strip=True).replace(span.find('b').get_text(strip=True), '').strip()
            details[key] = value

    return details

# Apply the function to each row in the DataFrame
parsed_data = df['scraped_html'].apply(lambda x: extract_job_details(x) if pd.notna(x) else {}).apply(pd.Series)

# Concatenate the original DataFrame with the parsed data
df = pd.concat([df, parsed_data], axis=1)

# Function to parse the "pay_range" column
def parse_pay_range(pay_range):
    if pd.isna(pay_range):
        return None, None, None

    pay_range = pay_range.strip()
    if ' - ' in pay_range:
        pay_parts = pay_range.split(' - ')
        pay_low = pay_parts[0].replace('$', '').replace(',', '').strip()
        pay_high = pay_parts[1].split('/')[0].replace('$', '').replace(',', '').strip()

        try:
            pay_low = float(pay_low)
            pay_high = float(pay_high)
        except ValueError:
            return None, None, None

        if (pay_low > 10000 or pay_high > 10000):
            pay_low = pay_low / 2080
            pay_high = pay_high / 2080

        pay_low = round(pay_low, 2)
        pay_high = round(pay_high, 2)
        pay_spread = round(pay_high - pay_low, 2)

        return pay_low, pay_high, pay_spread
    return None, None, None

# Apply the pay_range parsing function
df[['hourlypay_low', 'hourlypay_high', 'hourlypay_spread']] = df['pay_range'].apply(parse_pay_range).apply(pd.Series)

# Drop the "scraped_html" column
df.drop(columns=['scraped_html'], inplace=True)

# Construct the output filename by appending "_parsed" to the input filename
output_filename = input_filename.replace('.xlsx', '_parsed.xlsx')

# Save the updated DataFrame to the new Excel file
df.to_excel(output_filename, index=False)

print(f"File saved as {output_filename}")
