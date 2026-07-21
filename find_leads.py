"""
Hittar frisörer/salonger i en angiven stad, hämtar telefonnummer och
flaggar vilka som saknar hemsida (automatisk 5:a i din ranking).

Kräver: Google Cloud API-nyckel med "Places API" aktiverat.
Sätt nyckeln som miljövariabel: GOOGLE_PLACES_API_KEY

Kör: python find_leads.py "frisör Örebro"
"""

import sys
import os
import time
import requests
import csv

API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")
if not API_KEY:
    print("Sätt miljövariabeln GOOGLE_PLACES_API_KEY först.")
    sys.exit(1)

SEARCH_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
DETAILS_URL = "https://maps.googleapis.com/maps/api/place/details/json"


def search_places(query, next_page_token=None):
    params = {"query": query, "key": API_KEY}
    if next_page_token:
        params["pagetoken"] = next_page_token
    resp = requests.get(SEARCH_URL, params=params)
    return resp.json()


def get_details(place_id):
    params = {
        "place_id": place_id,
        "fields": "name,formatted_phone_number,international_phone_number,website,formatted_address,rating,user_ratings_total",
        "key": API_KEY,
    }
    resp = requests.get(DETAILS_URL, params=params)
    return resp.json().get("result", {})


def main():
    if len(sys.argv) < 2:
        print('Användning: python find_leads.py "frisör Örebro"')
        sys.exit(1)

    query = sys.argv[1]
    all_results = []
    next_page_token = None

    while True:
        data = search_places(query, next_page_token)
        results = data.get("results", [])
        all_results.extend(results)

        next_page_token = data.get("next_page_token")
        if not next_page_token:
            break
        # Google kräver kort fördröjning innan nästa sida blir giltig
        time.sleep(2)

    leads = []
    for place in all_results:
        place_id = place["place_id"]
        details = get_details(place_id)

        name = details.get("name", place.get("name", ""))
        phone = details.get("formatted_phone_number", "SAKNAS")
        website = details.get("website", "")
        address = details.get("formatted_address", "")
        rating = details.get("rating", "")
        reviews = details.get("user_ratings_total", "")

        # Grov auto-ranking: ingen hemsida = trolig 5:a, annars behöver
        # manuell koll för att avgöra 4 vs 3
        auto_rank = "5 (ingen hemsida - manuell koll krävs för telefonsvarare)" if not website else "4/3 (har hemsida - kolla kvalitet manuellt)"

        leads.append({
            "Namn": name,
            "Telefon": phone,
            "Hemsida": website or "SAKNAS",
            "Adress": address,
            "Betyg": rating,
            "Antal recensioner": reviews,
            "Auto-ranking": auto_rank,
        })

        time.sleep(0.1)  # var snäll mot API:et

    # Skriv till CSV
    filename = f"leads_{query.replace(' ', '_')}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=leads[0].keys())
        writer.writeheader()
        writer.writerows(leads)

    print(f"\nKlart! {len(leads)} företag sparade i {filename}")
    utan_hemsida = sum(1 for l in leads if l["Hemsida"] == "SAKNAS")
    print(f"Varav {utan_hemsida} saknar hemsida helt (troliga 5:or).")


if __name__ == "__main__":
    main()
