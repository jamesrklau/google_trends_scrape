# from pyvirtualdisplay import Display
# import undetected_chromedriver as webdriver
# from webdriver_manager.chrome import ChromeDriverManager
# from selenium.webdriver.common.by import By
# from selenium.webdriver.chrome.options import Options as ChromeOptions
# from selenium.webdriver.chrome.service import Service as ChromeService
# from selenium.webdriver.support.ui import WebDriverWait
# from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from pytrends.request import TrendReq
import time
import argparse
import contextlib
import os.path
import datetime


def scrape_google(term):
    
    pytrends = TrendReq()
    time.sleep(5)
    first_date = (
        datetime.datetime.now() - datetime.timedelta(days=30)
    ).strftime('%Y-%m-%d')
    second_date = (
        datetime.datetime.now() - datetime.timedelta(days=395)
    ).strftime('%Y-%m-%d')
    with contextlib.suppress(Exception):
        pytrends.build_payload(term, cat=0, timeframe = f'{second_date} {first_date}', geo='PR', gprop ='')
        trends = pytrends.interest_over_time()
        with contextlib.suppress(Exception):
            trends = trends.drop(columns=['isPartial'])
            trends = trends.drop(columns=['Caguas'])
        trends = trends.reset_index()
        trends.date = trends.date.astype(str)
        return trends

def get_trends(terms, trends, output_file):
    #trends = scrape_google(terms[0:5])
    for i in range(4,len(terms),4):
        time.sleep(5)
        terms_grouped = terms[i:i+4]
        terms_grouped.append ('Caguas')
        trends = pd.merge(trends, scrape_google(terms_grouped), on= 'date', how= 'right')
        print (f'columns: {len(list(trends))}, rows: {len(trends)}')
        trends.to_csv(output_file, index = False, encoding='utf-8-sig')
    return trends

def main():
    argv = get_args()
    terms_table = pd.read_csv(argv.csv)
    terms_table = terms_table[terms_table[argv.col_name].notna()]
    terms = list(terms_table[argv.col_name])
    if os.path.isfile( argv.output_file):
        trends = pd.read_csv(argv.output_file) 
    else:
        trends = pd.DataFrame([], columns = ['date'])
    keywords_already_collected = list(trends)
    terms = [x for x in terms if x not in set(keywords_already_collected)]
    trends_data = get_trends(terms, trends, argv.output_file)


def get_args():
    parser = argparse.ArgumentParser(
        description="Get Google Trends Data"
        )

    parser.add_argument(
        "-C", "--csv", type=str, required=True, help="CSV Table"
        )

    parser.add_argument(
        "-N", "--col_name", type=str, required=True, help="Column with keyword name"
        )

    parser.add_argument(
        "-O", "--output_file", type=str, required=True, help="Name of output file"
        )
    return parser.parse_args()

if __name__ == "__main__":
    main()
    print ("Done")