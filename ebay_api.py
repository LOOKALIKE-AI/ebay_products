import os
import csv
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

# -------------------------------
# Get OAuth access token
# -------------------------------
def get_access_token():
    key = os.environ.get("EBAY_CLIENT_ID")
    secret = os.environ.get("EBAY_CLIENT_SECRET")
    if not key or not secret:
        raise EnvironmentError("EBAY_CLIENT_ID or EBAY_CLIENT_SECRET not set in environment variables.")

    creds = f"{key}:{secret}"
    encoded_creds = base64.b64encode(creds.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {encoded_creds}"
    }
    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope"
    }

    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    response = requests.post(token_url, headers=headers, data=data)
    response.raise_for_status()
    return response.json().get("access_token")

# -------------------------------
# Get category tree ID
# -------------------------------
def category_tree_details(access_token: str, marketplace_id: str = "EBAY_IT"):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": marketplace_id
    }

    url_tree_id = f"https://api.ebay.com/commerce/taxonomy/v1/get_default_category_tree_id?marketplace_id={marketplace_id}"
    response = requests.get(url=url_tree_id, headers=headers)
    response.raise_for_status()
    category_tree_id = response.json().get("categoryTreeId")

    return category_tree_id

# -------------------------------
# Recursively get child categories
# -------------------------------
def get_childs_ids(access_token: str, category_tree_id: str, parent_category_id: str):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    url = (
        f"https://api.ebay.com/commerce/taxonomy/v1/category_tree/"
        f"{category_tree_id}/get_category_subtree?category_id={parent_category_id}"
    )

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    data = response.json()

    all_children = []

    def recurse(node):
        if "childCategoryTreeNodes" in node:
            for child in node["childCategoryTreeNodes"]:
                cat = child["category"]
                all_children.append({
                    "categoryId": cat["categoryId"],
                    "categoryName": cat["categoryName"]
                })
                recurse(child)

    recurse(data.get("categorySubtreeNode", {}))
    return all_children
    
# -------------------------------
# Fetch items for a category
# -------------------------------
def get_items_for_category(access_token: str, category_id: str, limit: int = 200):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_IT"
    }
    params = {
        "category_ids": category_id,
        "limit": limit
    }
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()

# -------------------------------
# Extract specific item info
# -------------------------------
def get_exact_information(item):
    campid = 5338967990  # affiliate ID
    categories = item.get("categories", "")
    categories = categories[0] if categories else None

    return {
        "product_id": item.get("itemId", ""),
        "image_url": item.get("image", {}).get("imageUrl", ""),
        "price": item.get("price", {}).get("value", ""),
        "currency": item.get("price", {}).get("currency", ""),
        "categories": categories.get("categoryName", "") if categories else "",
        "product_link": f"{item.get('itemWebUrl', '')}&campid={campid}",
        "description": item.get("title", "")
    }

# -------------------------------
# Write results to CSV
# -------------------------------
def write_to_csv(csv_name: str):
    access_token = get_access_token()
    category_tree_id = category_tree_details(access_token)

    parent_ids = ['220', '281', '888', '2984', '11450', '11700', '15032', '26395', '159912']

    # gather children
    all_child_ids = []
    for parent_id in parent_ids:
        try:
            children = get_childs_ids(access_token, category_tree_id, parent_id)
            # print(f"Parent {parent_id} → {len(children)} children")
            for c in children:
                all_child_ids.append(c["categoryId"])
        except Exception as e:
            print(f"Error fetching children for {parent_id}: {e}")

    # merge and deduplicate
    all_ids_to_fetch = list(set(parent_ids + all_child_ids))
    # print(f"Total categories to fetch: {len(all_ids_to_fetch)}")

    with open(csv_name, mode='w', encoding='utf-8', newline='') as f:
        writer = None
        for cat_id in all_ids_to_fetch:
            try:
                items_data = get_items_for_category(access_token, cat_id, limit=200)
                summaries = items_data.get("itemSummaries", [])
                if not summaries:
                    print(f"No items found for category {cat_id}")
                    continue
                for item in summaries:
                    info = get_exact_information(item)
                    if writer is None:
                        writer = csv.DictWriter(f, fieldnames=info.keys())
                        writer.writeheader()
                    writer.writerow(info)
                print(f"Fetched {len(summaries)} items for category {cat_id}")
            except Exception as e:
                print(f"Error fetching items for category {cat_id}: {e}")


def main():
    write_to_csv("ebay_products.csv")
    print("All the products data have been saved to CSV file.")

    

