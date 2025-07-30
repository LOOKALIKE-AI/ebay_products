import os
import csv
import base64
import requests
from dotenv import load_dotenv

load_dotenv()


class GetEbayproducts:

    # -------------------------------
    # Get access_token
    # -------------------------------    
    def get_access_token(self) -> str:
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
    def category_tree_details(self, access_token: str, marketplace_id: str = "EBAY_IT") -> int:
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
    def get_childs_ids(self, access_token: str, category_tree_id: int, parent_category_id: str) -> list:
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
    def get_items_for_category(self, access_token: str, category_id: str, limit: int = 200) -> dict:
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
    def get_exact_information(self, item:dict) -> dict:
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
            "description": item.get("title", ""),
            "availability": item.get("availability", 1)
        }

    # -------------------------------
    # Write results to CSV
    # -------------------------------

    def write_to_csv(self, csv_name: str) -> int:
        access_token = self.get_access_token()
        category_tree_id = self.category_tree_details(access_token)

        parent_ids = ['220', '281', '888', '2984', '11450', '11700', '15032', '26395', '159912']

        all_child_ids = []
        for parent_id in parent_ids:
            try:
                children = self.get_childs_ids(access_token, category_tree_id, parent_id)
                all_child_ids.extend([c["categoryId"] for c in children])
            except Exception as e:
                print(f"Error fetching children for {parent_id}: {e}")

        all_ids_to_fetch = list(set(parent_ids + all_child_ids))

        total_rows_written = 0
        writer = None

        with open(csv_name, mode='w', encoding='utf-8', newline='') as f:
            for cat_id in all_ids_to_fetch:
                try:
                    items_data = self.get_items_for_category(access_token, cat_id, limit=200)
                    summaries = items_data.get("itemSummaries", [])
                    if not summaries:
                        print(f"No items found for category {cat_id}")
                        continue

                    for item in summaries:
                        info = self.get_exact_information(item)

                        if writer is None:
                            writer = csv.DictWriter(f, fieldnames=info.keys())
                            writer.writeheader()

                        writer.writerow(info)
                        total_rows_written += 1

                    print(f"Fetched {len(summaries)} items for category {cat_id}")

                except requests.exceptions.HTTPError as http_err:
                    if http_err.response.status_code == 429:
                        print("Rate limit reached, stopping early.")
                        break
                    elif http_err.response.status_code == 500:
                        print(f"Internal server error (500) for category {cat_id}, skipping.")
                        continue  # skip and continue with the next category
                    else:
                        print(f"HTTP error {http_err.response.status_code} for category {cat_id}, skipping.")
                        continue
                except Exception as e:
                    print(f"Error fetching items for category {cat_id}: {e}")
                    continue

        print(f"✅ Saved final file: {csv_name} with {total_rows_written} rows")
        return total_rows_written

