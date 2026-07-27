"""
scrape.py — Pak'nSave + New World price scraper
Save this file, then run:  python scrape.py
Requires:  pip install requests beautifulsoup4 pandas
"""

# =====================================================================
# Imports
# =====================================================================
import requests
import datetime as dt
import pandas as pd
from bs4 import BeautifulSoup


# =====================================================================
# Define target URLs
# List of tuples containing (URL, Store Name, Category) to scrape
# =====================================================================
SCRAPE_TARGETS = [
    # PakNSave
    ('https://www.paknsave.co.nz/shop/category/fridge-deli-and-eggs/milk?pg=1',     'PakNSave', 'Dairy'),
    ('https://www.paknsave.co.nz/shop/category/bakery/sliced--packaged-bread?pg=1', 'PakNSave', 'Bakery'),
    ('https://www.paknsave.co.nz/shop/category/fruit-and-vegetables/fruit?pg=1',    'PakNSave', 'Fresh Produce'),
    ('https://www.paknsave.co.nz/shop/category/meat-poultry-and-seafood?pg=1',      'PakNSave', 'Meat'),
    # New World NZ
    ('https://www.newworld.co.nz/shop/category/fridge-deli-and-eggs/milk?pg=1',     'NewWorld', 'Dairy'),
    ('https://www.newworld.co.nz/shop/category/bakery/sliced--packaged-bread?pg=1', 'NewWorld', 'Bakery'),
    ('https://www.newworld.co.nz/shop/category/fruit-and-vegetables/fruit?pg=1',    'NewWorld', 'Fresh Produce'),
    ('https://www.newworld.co.nz/shop/category/meat-poultry-and-seafood?pg=1',      'NewWorld', 'Meat'),
    # Woolworths NZ - Angular SPA, server returns an empty shell.
    # requests cannot see the products; handled separately with Playwright.
    # ('https://www.woolworths.co.nz/shop/browse/fridge-deli/milk', 'Woolworths', 'Dairy'),
    # ('https://www.woolworths.co.nz/shop/browse/bakery',           'Woolworths', 'Bakery'),
    # ('https://www.woolworths.co.nz/shop/browse/fruit-veg/fruit',  'Woolworths', 'Fresh Produce'),
    # ('https://www.woolworths.co.nz/shop/browse/meat-seafood',     'Woolworths', 'Meat'),
]


def scrape_supermarket_page(url, store_name, category):

# STEP 1 GET -> STEP 2 PARSE -> STEP 3 SEARCH.
# Extracts: product name, price_nzd, unit for each product card.
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        )
    }

    # # STEP 1: GET - Send HTTP request to the URL with a 15-second timeout
    response = requests.get(url, headers=headers, timeout=15)
    # If the website returns an error code (not 200), stop and return empty list
    if response.status_code != 200:
        print(f"Error: Received status code {response.status_code}")
        return []

    # STEP 2: PARSE - Convert raw HTML into a searchable BeautifulSoup object.
    # 'html.parser' is built into Python, so nothing extra to install.
    scraping = BeautifulSoup(response.content, 'html.parser')

    # STEP 3: SEARCH - Find all product container elements.
    # Foodstuffs marks each product with schema.org microdata; this attribute is
    # hand-written by the developers so it survives site redeploys, unlike the
    # generated CSS classes (owfhtz0, _10e5eu870 ...) which change every release.
    cards = scraping.find_all('div', attrs={'itemtype': 'https://schema.org/Product'})
    # Fallback: if no cards found, match on the container's data-testid instead
    if not cards:
        cards = scraping.select("div[data-testid^='product-']")

    records = []                 # Temporary list to hold dictionaries of found products
    for card in cards:
        # Find element by custom attribute (product name)
        name_tag = card.find('p', attrs={'data-testid': 'product-title'})
        # Find element by custom attribute (unit / volume, e.g. "2l")
        unit_tag = card.find('p', attrs={'data-testid': 'product-subtitle'})

        # Price is rendered as TWO separate elements - the large dollars and the
        # small superscript cents ($4 84 means 4.84) - so collect every pure-digit
        # text node inside this card and join the first two.
        price_digits = [s for s in card.stripped_strings if s.isdigit()]

        # Check if elements exist
        if not name_tag or len(price_digits) < 2:
            continue

        # Get text content and clean
        price_text = f"{price_digits[0]}.{price_digits[1]}"

        # Check price_text is not empty before converting
        if price_text == '':
            continue

        price = float(price_text)
        # Build a structured dictionary for the product and add it to the records list
        records.append({
            'store'       : store_name,
            'category'    : category,
            'product'     : name_tag.text.strip(),
            'price_nzd'   : price,
            'unit'        : unit_tag.text.strip() if unit_tag else 'each',
            'date_scraped': dt.date.today().isoformat(),
        })

    return records


#  Run live scraping
all_scraped = []    # Master list to store all items from all stores
for url, store, cat in SCRAPE_TARGETS:          # Loop through each target configuration
    print(f'Scraping {store} - {cat} ...')      # Print progress message to console
    results = scrape_supermarket_page(url, store, cat)   # Run the scraping function for this target
    all_scraped.extend(results)                 # Add the new products to the master list
    print(f'  -> {len(results)} products collected')     # Print how many items were found on this page

print(f'\nTotal live scraped records: {len(all_scraped)}')   # Print final message showing total

# Convert list of structured dicts into a Pandas DataFrame and save
df_scraped = pd.DataFrame(all_scraped)
if not df_scraped.empty:
    print(df_scraped.head(20).to_string())
    df_scraped.to_csv('nz_scraped_prices.csv', index=False)
    print(f'Saved nz_scraped_prices.csv - {df_scraped.shape[0]} rows')
