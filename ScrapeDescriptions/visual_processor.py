import pandas as pd
import sys
import matplotlib.pyplot as plt
from pathlib import Path

def process_file(filepath):
    print(f"Processing {filepath}...")
    
    # Load and standardize data
    df = pd.read_excel(filepath) if str(filepath).endswith('.xlsx') else pd.read_csv(filepath)
    
    # Generate trending dashboard
    output_html = f"dashboard_{Path(filepath).stem}.html"
    
    # Example visualization
    plt.figure(figsize=(10,6))
    if 'pay_range' in df.columns:
        df['pay_range'].value_counts().plot(kind='bar')
        plt.title("Pay Range Distribution")
        plt.savefig("pay_trend.png")
    
    # Create HTML dashboard
    with open(output_html, 'w') as f:
        f.write(f"""
        <html>
        <body>
            <h1>{Path(filepath).name} Trends</h1>
            <img src="pay_trend.png" width="800">
            <div id="debug">
                <h3>Metadata</h3>
                <pre>{df.describe().to_html()}</pre>
            </div>
        </body>
        </html>
        """)
    
    print(f"Dashboard saved to {output_html}")

if __name__ == "__main__":
    process_file(sys.argv[1])
