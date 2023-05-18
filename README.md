# Google Trends Scraper
This Python script allows you to scrape Google Trends data for a list of keywords and store it in a CSV file. The script uses the pytrends library to interact with the Google Trends API and retrieve the data.

Prerequisites
Before running the script, make sure you have the following dependencies installed:

Python 3.x
pandas
pytrends
You can install the required dependencies using pip:

```
bash
Copy code
pip install pandas pytrends
```

# Usage
Prepare a CSV file containing the list of keywords you want to scrape Google Trends data for. The CSV file should have a column containing the keywords. Make sure there are no empty values in the keyword column.

Run the script google_trends_scraper.py with the following command:

```
bash
Copy code
python google_trends_scraper.py -C <csv_file> -N <keyword_column> -O <output_file>
```

Replace <csv_file> with the path to your CSV file, <keyword_column> with the name of the column containing the keywords, and <output_file> with the desired name for the output CSV file.

For example:

```
bash
Copy code
python google_trends_scraper.py -C keywords.csv -N Keyword -O trends_data.csv
```

The script will start scraping Google Trends data for the keywords in batches. It will pause for 5 seconds between each batch to avoid overwhelming the API. The progress will be displayed in the console, showing the number of columns and rows in the merged trends data after each batch.

Once the script finishes running, it will save the merged trends data to the specified output CSV file (<output_file>).

# Notes
The script automatically filters out keywords that have already been collected in previous runs. This allows you to resume the scraping process and avoid duplicating data.

The date range for the scraped data is set to the past 30 days by default. You can modify the scrape_google function in the script to change the date range if needed.

The script uses a 395-day interval between batches to avoid reaching the Google Trends API rate limits. If you have a large number of keywords, the script may take some time to complete.

It is recommended to run the script during off-peak hours to minimize the impact on the Google Trends API and ensure smoother data retrieval.

# License
This project is licensed under the MIT License. See the LICENSE file for details.