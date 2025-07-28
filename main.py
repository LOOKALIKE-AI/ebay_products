from ebay_api import GetEbayproducts

def main():
    try:
        ebay = GetEbayproducts()
        rows_written = ebay.write_to_csv("ebay_products.csv")
        print(f"{rows_written} products saved to CSV.")
    except Exception as e:
        print(f"Script failed: {e}")

if __name__ == "__main__":
    main()
