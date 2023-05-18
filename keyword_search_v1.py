import pandas as pd
from pytrends.request import TrendReq
import time
import argparse
import contextlib
import os.path
import datetime

def scrape_google(term):
    # Scrape Google Trends data for a given term
    pytrends = TrendReq()
    time.sleep(5)
    
    # Define the date range for the data
    first_date = (
        datetime.datetime.now() - datetime.timedelta(days=30)
    ).strftime('%Y-%m-%d')
    second_date = (
        datetime.datetime.now() - datetime.timedelta(days=395)
    ).strftime('%Y-%m-%d')
    
    with contextlib.suppress(Exception):
        # Build the payload for the specified term and date range
        pytrends.build_payload(term, cat=0, timeframe=f'{second_date} {first_date}', geo='PR', gprop='')
        
        # Get the interest over time data
        trends = pytrends.interest_over_time()
        
        with contextlib.suppress(Exception):
            # Drop unnecessary columns
            trends = trends.drop(columns=['isPartial'])
            trends = trends.drop(columns=['Caguas'])
        
        # Reset the index of the data frame
        trends = trends.reset_index()
        trends.date = trends.date.astype(str)
        return trends

def get_trends(terms, trends, output_file):
    # Get trends data for multiple terms
    for i in range(4, len(terms), 4):
        time.sleep(5)
        terms_grouped = terms[i:i+4]
        terms_grouped.append('Caguas')
        
        # Merge the trends data for the current group of terms
        trends = pd.merge(trends, scrape_google(terms_grouped), on='date', how='right')
        
        print(f'columns: {len(list(trends))}, rows: {len(trends)}')
        
        # Save the merged trends data to the output file
        trends.to_csv(output_file, index=False, encoding='utf-8-sig')
    return trends

def main():
    # Parse command-line arguments
    argv = get_args()
    
    # Read the terms from the input CSV file
    terms_table = pd.read_csv(argv.csv)
    
    # Remove rows with empty values in the specified column
    terms_table = terms_table[terms_table[argv.col_name].notna()]
    
    # Extract the terms from the table
    terms = list(terms_table[argv.col_name])
    
    if os.path.isfile(argv.output_file):
        # If the output file already exists, read the trends data from it
        trends = pd.read_csv(argv.output_file)
    else:
        trends = pd.DataFrame([], columns=['date'])
    
    keywords_already_collected = list(trends)
    
    # Filter out terms that have already been collected
    terms = [x for x in terms if x not in set(keywords_already_collected)]
    
    # Get trends data for the remaining terms
    trends_data = get_trends(terms, trends, argv.output_file)

def get_args():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Get Google Trends Data")
    
    parser.add_argument("-C", "--csv", type=str, required=True, help="CSV Table")
    parser.add_argument("-N", "--col_name", type=str, required=True, help="Column with keyword name")
    parser.add_argument("-O", "--output_file", type=str, required=True, help="Name of output file")
    
    return parser.parse_args()

if __name__ == "__main__":
    main()
    print("Done")