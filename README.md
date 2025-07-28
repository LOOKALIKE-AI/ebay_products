# eBay Category Fetcher

This Python script fetches product data from the eBay APIs based on specified parent categories (and their subcategories) for a given marketplace.  
It retrieves product details (title, price, image, category, link, etc.) and writes them to a CSV file for further processing.

---

## ✨ Features

- **OAuth2 Authentication**: Securely retrieves an access token from eBay using your `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`.
- **Dynamic Category Tree Retrieval**: Uses the Taxonomy API to get the default category tree ID and fetch all child categories recursively.
- **Product Search**: Queries the Browse API (`item_summary/search`) for each category.
- **CSV Export**: Saves the results in a structured CSV with headers like product ID, image URL, price, currency, category name, affiliate link, and description.
- **Error Handling**: Gracefully handles missing data, empty categories, or network errors.

---

## 📦 Requirements

- Python 3.11
- An eBay Developer account with `EBAY_CLIENT_ID` and `EBAY_CLIENT_SECRET`
- Environment variables set (via `.env` file or system):

```env
EBAY_CLIENT_ID=your_client_id
EBAY_CLIENT_SECRET=your_client_secret
