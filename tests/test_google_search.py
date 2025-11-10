import time


def test_google_search(google_search):
    time.sleep(5)
    google_search.search_query("Dermatologist in Palm Beach Florida")

    google_search.click_more_places()

    # Extract name, address, phone for first few places
    results = google_search.click_each_place_and_get_details()

    # Print or return results
    print("\n📋 Extracted Places:")
    for r in results:
        print(f"{r['name']} | {r['address']} | {r['phone']}")


