import requests
from bs4 import BeautifulSoup
import argparse
import time
from urllib.parse import urlencode, urljoin
from collections import defaultdict
import re
from datetime import datetime, timedelta
import locale # Keep for potential future use, though manual parsing is primary

# python biletinial_scraper.py --category both --city antalya --venue-id 20494 2174 1271 --tiyatro-filmtypeids 490 684 688 689 692 569 --opera-filmtypeids 520; "(Roo/PS Workaround: 31)" > $null; start-sleep -milliseconds 150

# Selectors based on Tiyatro page inspection (May need adjustment for other categories)
DATE_TEXT_SELECTOR = 'li > span' # Contains Month - Day(s)
EVENT_ITEM_SELECTOR = '#kategori__etkinlikler > ul > li'
PLAY_NAME_SELECTOR = 'li h3 a' # Selector for the <a> tag containing the name and link
VENUE_NAME_SELECTOR = 'li address small'

# Base URL - Now constructed dynamically
BASE_URL_FORMAT = 'https://biletinial.com/tr-tr/{category}/'
# Base URL for joining relative links
BASE_DOMAIN = 'https://biletinial.com'

# User Agent
USER_AGENT = 'Mozilla/5.0 (compatible; TheatreScraperBot/1.0; +http://example.com/botinfo)'

# Turkish Month Name to Number Mapping
TURKISH_MONTHS = {
    "Ocak": "01", "Şubat": "02", "Mart": "03", "Nisan": "04",
    "Mayıs": "05", "Haziran": "06", "Temmuz": "07", "Ağustos": "08",
    "Eylül": "09", "Ekim": "10", "Kasım": "11", "Aralık": "12"
}

watched_plays = [
    'Polisler', 'THERESE RAQUIN (BİR CİNAYETİN ANATOMİSİ)', 'Antigone', 'GRAMOFON HALA ÇALIYOR'
]

def build_url(category, city, date_filter='', type_id=0, venue_id=''):
    """Constructs the target URL for biletinial.com listings."""
    base_url = BASE_URL_FORMAT.format(category=category)
    city_url = urljoin(base_url, city.lower())
    params = {}

    if date_filter:
        if date_filter.lower() == 'thisweekend':
            params['thisweekend'] = ''
        else:
            params['date'] = date_filter

    try:
        type_id_int = int(type_id) if type_id else 0
        if type_id_int != 0:
            params['filmtypeid'] = type_id_int
    except ValueError:
        print(f"Warning: Invalid type_id '{type_id}', ignoring.")

    if venue_id:
        params['loc'] = venue_id

    if params:
        query_string = urlencode(params)
        query_string = query_string.replace('=None', '=')
        query_string = query_string.replace('=&', '&')
        if query_string.endswith('='):
             query_string = query_string[:-1]
        query_string = re.sub(r'&?filmtypeid=0&?', '', query_string).strip('&')
        if query_string:
            return f"{city_url}?{query_string}"
        else:
            return city_url
    else:
        return city_url

def fetch_html(url):
    """Fetches HTML content from the given URL."""
    #print(f"Fetching URL: {url}")
    headers = {'User-Agent': USER_AGENT}
    try:
        time.sleep(1)
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        if 'text/html' not in response.headers.get('Content-Type', ''):
             print(f"Warning: Expected HTML content, but got {response.headers.get('Content-Type')} for {url}")
             return None
        return response.text
    except requests.exceptions.Timeout:
        print(f"Error: Request timed out for {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during fetch for {url}: {e}")
        return None


def extract_events(html_content, category):
    """Extracts event data from HTML content, including the category and link."""
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    extracted_events = []
    event_items = soup.select(EVENT_ITEM_SELECTOR)

    if not event_items:
        return []

    for event in event_items:
        play_name_tag = event.select_one(PLAY_NAME_SELECTOR) # Select the <a> tag
        play_name = play_name_tag.text.strip() if play_name_tag else "N/A"
        play_link_relative = play_name_tag['href'] if play_name_tag and play_name_tag.has_attr('href') else None # Get href

        venue_name_tag = event.select_one(VENUE_NAME_SELECTOR)
        venue_name = venue_name_tag.text.strip() if venue_name_tag else "N/A"
        date_tag = event.select_one(DATE_TEXT_SELECTOR)
        date_str = ' '.join(date_tag.text.split()) if date_tag else "N/A"

        if play_name != "N/A" and venue_name != "N/A" and date_str != "N/A" and play_link_relative and play_name not in watched_plays:
            extracted_events.append({
                'date': date_str,
                'play': play_name,
                'venue': venue_name,
                'category': category,
                'link_relative': play_link_relative # Store relative link
            })
        # else: # Reduce noise
        #      print(f"Skipping event due to missing data...")

    return extracted_events

# format_output is not used for grouped output
# def format_output(events_list): ...

def fetch_and_group_events(categories_to_process, city, venue_ids, tiyatro_filmtypeids, opera_filmtypeids, date_filter=''):
    """
    Fetches events for specified categories, venues, and film types,
    aggregates the results, and structures them by date.
    """
    all_events = []
    venues_to_check = venue_ids if venue_ids else [''] # Use [''] to fetch without venue filter if none provided

    for category in categories_to_process:
        filmtypeids_for_category = []
        if category == 'tiyatro':
            filmtypeids_for_category = tiyatro_filmtypeids if tiyatro_filmtypeids else [0]
        elif category == 'opera-bale':
            filmtypeids_for_category = opera_filmtypeids if opera_filmtypeids else [0]
        else:
             filmtypeids_for_category = [0]

        for type_id in filmtypeids_for_category:
            for venue_id in venues_to_check:
                target_url = build_url(category, city, date_filter, type_id, venue_id)
                html = fetch_html(target_url)
                if html:
                    events = extract_events(html, category)
                    all_events.extend(events)

    # --- Grouping and Date Range Logic ---
    events_by_date = defaultdict(list)
    all_parsed_dates = set()

    for event in all_events:
        date_string = event['date']
        dates_str_list = extract_dates_from_string(date_string)
        for date_str in dates_str_list:
            parsed_date = parse_turkish_date(date_str)
            if parsed_date:
                all_parsed_dates.add(parsed_date)
                # Append the whole event dict
                events_by_date[date_str].append(event)

    if not all_parsed_dates:
        return dict(events_by_date)

    start_date = min(all_parsed_dates)
    end_date = max(all_parsed_dates)

    current_date = start_date
    while current_date <= end_date:
        month_num_str = current_date.strftime("%m")
        month_name = [name for name, num in TURKISH_MONTHS.items() if num == month_num_str][0]
        day_str = current_date.strftime("%d")
        date_key = f"{month_name} - {day_str}"

        if date_key not in events_by_date:
            events_by_date[date_key] = [] # Ensure empty dates exist
        current_date += timedelta(days=1)

    return dict(events_by_date)

def extract_dates_from_string(date_string):
    """
    Extracts individual date strings (Month - DD) from the raw date string.
    """
    parts = date_string.split(" - ")
    month = parts[0]
    dates = []
    if month not in TURKISH_MONTHS:
        return dates

    for part in parts[1:]:
        day_part = part.split(" ")[0]
        if day_part.isdigit():
             dates.append(f"{month} - {day_part.zfill(2)}")
    return dates

def parse_turkish_date(date_str):
    """
    Parses a Turkish date string "Month - DD" into a datetime object.
    Returns None if parsing fails.
    """
    try:
        parts = date_str.split(" - ")
        month_name = parts[0]
        day = int(parts[1])
        month_num = TURKISH_MONTHS.get(month_name)
        if not month_num:
            return None
        current_year = datetime.now().year
        return datetime(current_year, int(month_num), day)
    except (ValueError, IndexError):
        return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape events from biletinial.com.")
    parser.add_argument("--category", required=True, choices=['tiyatro', 'opera-bale', 'both'], help="Event category ('tiyatro', 'opera-bale', or 'both')")
    parser.add_argument("--city", required=True, help="City slug (e.g., 'antalya')")
    parser.add_argument("--date", default="", help="Date filter (e.g., 'YYYY-MM-DD', 'thisweekend', or empty for all)")
    parser.add_argument("--tiyatro-filmtypeids", nargs='+', default=[], help="List of Theatre Film Type IDs (optional)")
    parser.add_argument("--opera-filmtypeids", nargs='+', default=[], help="List of Opera/Ballet Film Type IDs (optional)")
    parser.add_argument("--venue-id", nargs='+', default=[], help="List of Venue IDs (optional, fetches all if omitted)")

    args = parser.parse_args()

    categories_to_process = []
    if args.category == 'both':
        categories_to_process = ['tiyatro', 'opera-bale']
    else:
        categories_to_process = [args.category]

    grouped_events = fetch_and_group_events(
        categories_to_process,
        args.city,
        args.venue_id,
        args.tiyatro_filmtypeids,
        args.opera_filmtypeids,
        args.date
    )

    # Write output to file instead of console
    output_filename = "biletinial_scraper_output.txt"
    with open(output_filename, 'w', encoding='utf-8') as output_file:
        output_file.write("--- Grouped Events by Date ---\n") # Removed leading newline for cleaner file start

        if grouped_events:
            def sort_key(date_str):
                parsed = parse_turkish_date(date_str)
                return parsed if parsed else datetime.min

            try:
                sorted_dates = sorted(grouped_events.keys(), key=sort_key)
                for date in sorted_dates:
                    events = grouped_events[date]
                    # Only write the date header if there are events for that date
                    if events:
                        output_file.write(f"\n{date}:\n")
                        events.sort(key=lambda x: (x['category'], x['play']))
                        for event in events:
                            # Construct full URL
                            full_url = urljoin(BASE_DOMAIN, event['link_relative'])
                            # Write event details with link
                            output_file.write(f"  - [{event['category'].upper()}] {event['play']} – {event['venue']} -> {full_url}\n")
                    # Removed the 'else' block that printed "No events scheduled."
            except Exception as e:
                # Write error message to the file as well
                output_file.write(f"\nError during output generation: {e}. Printing unsorted.\n")
                # Fallback to unsorted printing (without "No events scheduled")
                for date, events in grouped_events.items():
                     if events: # Only write if there are events
                        output_file.write(f"\n{date}:\n")
                        events.sort(key=lambda x: (x['category'], x['play']))
                        for event in events:
                            full_url = urljoin(BASE_DOMAIN, event['link_relative'])
                            output_file.write(f"  - [{event['category'].upper()}] {event['play']} – {event['venue']} -> {full_url}\n")
        else:
             output_file.write("\nNo events found or could be grouped for the specified criteria.\n") # Added leading newline
        output_file.write("------------------------------\n")

        output_file.write("\nScript finished.\n")
    # Print a confirmation to the console that the file has been written
    print(f"Output successfully written to {output_filename}")