import csv
import json
from datetime import datetime, date, timedelta
from os.path import exists
import requests

prices_folder = "prices_cache/{filename}"
database_filename = "casemove.csv"

# TODO: Parse https://steamcommunity.com/id/viagoogler/inventoryhistory/

def open_inventory_database(filename: str) -> dict:
    with open(filename, encoding="utf-8") as file:
        data = {}
        reader = csv.reader(file)
        next(reader)  # skip header
        for item in reader:
            item_name = item[0]
            item_data = data.get(item_name, {})
            item_data["amount"] = item_data.get("amount", 0) + int(item[8])
            data[item_name] = item_data
        return data


def read_json_from_file(filename: str) -> dict:
    with open(filename, encoding="utf-8") as file:
        return json.load(file)


def format_date_numer(number: int) -> str:
    return str(number).zfill(2)


def get_path_for_date(year: int, month: int, day: int, format: str = "json") -> str:
    return prices_folder.format(filename=f"{year}_{format_date_numer(month)}_{format_date_numer(day)}.{format}")

def create_url_for(year: int, month: int, day: int, version: int = 6) -> str:
    csgotrader_url_pattern = "https://prices.csgotrader.app/{year}/{month}/{day}/prices_v{version}.json"
    return csgotrader_url_pattern.format(year=year, month=format_date_numer(month), day=format_date_numer(day), version=version)


def get_json_for_date(year: int, month: int, day: int) -> dict:
    target_url = create_url_for(year, month, day)
    resp = requests.get(url=target_url)
    return resp.json()


def download_price_data_for(year: int, month: int, day: int) -> {bool, str}:
    price_data_filepath = get_path_for_date(year, month, day)
    if exists(price_data_filepath):
        return False, price_data_filepath

    json_data = get_json_for_date(year, month, day)
    with open(price_data_filepath, 'w', encoding="utf-8") as outfile:
        json.dump(json_data, outfile)
        return True, price_data_filepath


def get_pricing_data(year: int, month: int, day: int) -> dict:
    did_download, file_path = download_price_data_for(year, month, day)
    return read_json_from_file(file_path)


def get_current_pricing_data():
    today = date.today()
    yesterday = today - timedelta(days=2)
    return get_pricing_data(yesterday.year, yesterday.month, yesterday.day)


def calculate_price_for(item_name: str, prices: dict) -> float:
    item_value = prices.get(item_name, None)

    if item_value is None:
        return 0.0

    steam_data = item_value.get('steam', {})
    steam_price = steam_data.get('last_24h', -1.0)
    if steam_price is not None and steam_price != "null" and steam_price > 0.0:
        return steam_price

    csmoney_price = float(steam_data.get('csmoney', -1.0))
    if csmoney_price is not None and csmoney_price != "null"  and csmoney_price > 0.0:
        return csmoney_price

    csgotm_price = float(steam_data.get('csgotm', -1.0))
    if csgotm_price is not None and csgotm_price != "null" and csgotm_price > 0.0:
        return csgotm_price

    return 0.0


def calculate_profit_from_data(year: int, month: int, day: int):
    inventory = open_inventory_database(database_filename)

    old_price_data = get_pricing_data(year, month, day)
    current_price_data = get_current_pricing_data()

    results = {}
    for item_name, item_data in inventory.items():
        item_amount = item_data["amount"]

        old_price = calculate_price_for(item_name, old_price_data)
        current_price = calculate_price_for(item_name, current_price_data)
        diff_price = current_price - old_price

        if old_price == 0.0:
            print(f"Skipping {item_name} because no price")
            continue

        if current_price == 0.0:
            continue

        if current_price == old_price:
            continue

        profit_percent = (current_price / old_price) - 1
#
        results[item_name] = {}
        results[item_name]["amount"] = item_amount
        results[item_name]["old_price"] = old_price
        results[item_name]["new_price"] = current_price
        results[item_name]["profit_percent"] = profit_percent * 100.0
        results[item_name]["profit_value"] = (current_price - old_price) * item_amount

    # results = dict(sorted(results.items(), key=lambda item: item[1]["profit_percent"]))
    results = dict(sorted(results.items(), key=lambda item: item[1]["profit_value"]))

    for item_name, item_data in results.items():

        print(f'{item_name}')
        print(f'>Amount: {item_data["amount"]}')
        print(f'>Old price: {item_data["old_price"]}')
        print(f'>Current price: {item_data["new_price"]}')
        print(f'>Profit in %: {"{:.2f}".format(item_data["profit_percent"])}')
        print(f'>Profit in $$$: {"{:.2f}".format(item_data["profit_value"])}')



def main():
    calculate_profit_from_data(2023, 3, 16)

if __name__ == "__main__":
    main()
