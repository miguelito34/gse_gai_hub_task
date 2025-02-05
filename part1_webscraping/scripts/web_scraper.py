################################################################################
## Author: Michael Spencer
## Project: GSE GENAI Research Repo Web Scraper
## Script Purpose: Scrape article data from the Generative AI for Education 
##                 Research Repository website.
## Notes: Uses Path, requests, BeautifulSoup, and pandas libraries
################################################################################

### LIBRARIES ###
# Environment libraries
from pathlib import Path

# Analysis libraries
import requests
from bs4 import BeautifulSoup
import pandas as pd

### VARIABLES ###
project_root = str(Path.cwd().resolve())
data_dir = project_root + "/data"
data_out = data_dir + "/clean/gse_genai_articles.csv"

# Define search urls for the HTML requests
repo_base_url = "https://scale.stanford.edu"
teaching_k12_search_url = repo_base_url + "/genai/repository?search_api_fulltext=&application%5B42%5D=42&benefits%5B34%5D=34&benefits%5B36%5D=36&benefits%5B35%5D=35"
impact_secondary_search_url = repo_base_url + "/genai/repository?search_api_fulltext=&benefits%5B36%5D=36&benefits%5B35%5D=35&study_design%5B55%5D=55"
search_urls = [teaching_k12_search_url, impact_secondary_search_url]

### FUNCTIONS ###
def main(search_urls):
    page_urls = identify_pages_to_scrape(search_urls)
    article_urls = identify_articles_to_scrape(page_urls)
    article_data = extract_article_data(article_urls)
    write_data_to_csv(article_data)


# Scrapes the search results for every "Teaching - Instructional Materials in K12" and
# "Impact - Randomized Controlled Trials in secondary education" page,
# and adds them to the set of pages in which to look for articles
def identify_pages_to_scrape(search_urls):
    pages_to_scrape = set()

    for search_url in search_urls:
        response = requests.get(search_url)

        if response.status_code != 200:
            print(f"Warning: Failed to retrieve {search_url} (status: {response.status_code}).")
            continue
        
        parsed_response = BeautifulSoup(response.text, 'html.parser')
        pagination_data = parsed_response.select("ul.pagination li a.page-link")

        # Catches the case where there is no pagination data, and we only have one page to scrape
        if not pagination_data:
            pages_to_scrape.add(search_url)
            continue
        
        for page in pagination_data:
            page_url = repo_base_url + "/genai/repository" + page['href']
            pages_to_scrape.add(page_url)

    return pages_to_scrape


# Scrapes each previously identified page for the article urls and
# adds them to the set of articles to scrape
def identify_articles_to_scrape(page_urls):
    articles_to_scrape = set()
    article_titles = set()

    for page_url in page_urls:
        response = requests.get(page_url)

        if response.status_code != 200:
            print(f"Warning: Failed to retrieve {page_url} (status: {response.status_code}).")
            continue
        
        parsed_response = BeautifulSoup(response.text, 'html.parser')
        articles_to_parse = parsed_response.select("ul.list-papers li.col")
        
        # Extracts the individual article URLs from the page HTML
        for article in articles_to_parse:

            # Checks if the article title is already in the set of article titles to avoid duplicates
            article_title = article.select_one("div.card a[hreflang='en']").get_text(strip = True)
            if article_title not in article_titles:
                article_titles.add(article_title)
                article_sub_url = article.select_one("div.card a[href]")
                article_url = repo_base_url + article_sub_url['href']
                articles_to_scrape.add(article_url)

    print(f"Identified {len(articles_to_scrape)} distinct articles to scrape.")

    return articles_to_scrape


# Parses metadata for analysis from each article
def extract_article_data(articles_to_scrape):
    article_data = []

    print(f"Attempting to scrape data from {len(articles_to_scrape)} articles...")

    for article in articles_to_scrape:
        response = requests.get(article)

        if response.status_code != 200:
            print(f"Warning: Failed to retrieve {article} (status: {response.status_code}).")
            continue

        parsed_article = BeautifulSoup(response.text, 'html.parser')

        # Gathers metadata from the article
        article_metadata = {}
        title = parsed_article.select_one("h1").get_text(strip = True)
        article_metadata["Title"] = title

        # Identifies all the metadata fields within the article HTML node
        node_content = parsed_article.select_one("div.node__content").select("div.field")

        for field in node_content:
            article_metadata = extract_metadata_field(field, article_metadata)

        article_data.append(article_metadata)

    print(f"Successfully scraped data from {len(article_data)} distinct articles.")

    return article_data


# Parses each field of the article and returns an updated dictionary of the relevant metadata
def extract_metadata_field(metadata_field, article_metadata):
    field_name_html = metadata_field.select_one("div.field__label")
        
    # If the field name is not found, I assume the field is the "Abstract" based on the site structure
    if not field_name_html:
        field_name = "Abstract"
        field_value = metadata_field.select_one("div.field__item, p").get_text(strip = True)
        article_metadata[field_name] = field_value
        return article_metadata
    
    # If the field name is found, I use the label given and extract the relevant items, however many there may be
    field_name = field_name_html.get_text(strip = True)
    field_items = metadata_field.select("div.field__item")

    item_values = ""
    # If the field name is "Link", extract the href attribute
    if field_name == "Link":
        publishing_link = metadata_field.select_one("a[href]")
        item_values = publishing_link["href"]
    else:
        for item in field_items:
            # Some fields have multiple items, so I concatenate them together and strip unneccessary linebreaks
            item_value = item.get_text().strip("\n")
            item_values = item_values + item_value

    # Add the field to the dictionary
    article_metadata[field_name] = item_values

    return article_metadata


# Write the scraped data to a CSV
def write_data_to_csv(data):
    data_gse_genai_articles = pd.DataFrame(data)

    # Rename the "Who Age?" column to "What Age?" and save to a CSV file
    (data_gse_genai_articles.rename(columns = {"Who age?": "What age?"})
                            .sort_values(by = "Title")
                            .to_csv(data_out, index=False))
    
    print(f"Wrote data to CSV at data {data_out}.")

# Run scraper
main(search_urls)