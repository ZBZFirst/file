import pandas as pd
from bs4 import BeautifulSoup

def clean_html_in_columns(output_path):
    # Load the Excel file into a pandas DataFrame
    df = pd.read_excel(output_path)
    
    # Iterate through rows to rebuild HTML from columns L to AE
    for index, row in df.iterrows():
        # Rebuild the HTML content by concatenating columns L to AE (skip NaN values)
        html_content = ''.join([str(row[col]) for col in df.columns[11:32] if pd.notna(row[col])])

        # Use BeautifulSoup to parse and strip HTML
        cleaned_html = BeautifulSoup(html_content, 'lxml').get_text()

        # Reinsert the cleaned HTML back into the corresponding columns (L to AE)
        html_chunks = [cleaned_html[i:i+30000] for i in range(0, len(cleaned_html), 30000)]  # Split into chunks if needed
        for i, chunk in enumerate(html_chunks):
            if i < 20:  # Limit to 20 chunks to fit within the HTML columns
                df.at[index, f'HTML_{i+1}'] = chunk  # Reinsert cleaned HTML chunks into the columns

    # Save the updated DataFrame back to Excel
    df.to_excel(output_path, index=False)
    print(f"HTML cleaned and file saved to: {output_path}")

# Example usage:
clean_html_in_columns(r"C:\Scrape\ScrapeDescriptions\UCSystems\test.xlsx")
