import os
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv() 

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TARGET_URL = os.getenv("TARGET_URL", "https://qsamruk.kz/company/too-pgu-turkestan")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 600))

KNOWN_VACANCIES_FILE = "known_vacancies.txt"


def load_known_vacancies(filename):
    """
    Load known vacancy IDs or titles from a local file.
    Returns a set of known vacancy identifiers.
    """
    if not os.path.exists(filename):
        return set()
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()
        return set(lines)

def save_known_vacancies(filename, vacancies):
    """
    Save known vacancy identifiers to a local file (one per line).
    """
    with open(filename, "w", encoding="utf-8") as f:
        for vacancy_id in vacancies:
            f.write(vacancy_id + "\n")

def fetch_vacancy_ids(url):
    """
    Fetch the webpage, parse HTML, and extract a list of vacancy identifiers.
    We'll parse the <a href="/vacancy/XXXX" ...> or a 'div' with class "vacancy-item".
    Adjust parsing logic based on actual structure.
    """
    response = requests.get(url)
    response.raise_for_status()  

    soup = BeautifulSoup(response.text, "html.parser")

    vacancy_divs = soup.find_all("div", class_="vacancy-item")
    found_ids = []

    for div in vacancy_divs:
        link_tag = div.find("a", href=True)
        if link_tag:
            href = link_tag["href"]  
            if "/vacancy/" in href:
                vacancy_id = href.split("/vacancy/")[-1].strip("/")
                found_ids.append(vacancy_id)
    
    return found_ids

def send_telegram_alert(new_vacancies):
    """
    Sends a Telegram message with the new vacancies.
    """
    if not new_vacancies:
        return

    message = "🆕 New Vacancies Found:\n\n"
    for vacancy in new_vacancies:
        message += f"🔹 Vacancy ID: {vacancy}\n"
        message += f"🔗 [View Vacancy](https://qsamruk.kz/vacancy/{vacancy})\n\n"

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("[INFO] Telegram message sent successfully!")
    else:
        print(f"[ERROR] Failed to send Telegram message: {response.text}")

def main():
    known_vacancies = load_known_vacancies(KNOWN_VACANCIES_FILE)

    while True:
        print("[INFO] Checking for new vacancies...")

        try:
            current_ids = fetch_vacancy_ids(TARGET_URL)
            print(f"[DEBUG] Found {len(current_ids)} vacancy IDs on the page.")

            new_vacancies = [vid for vid in current_ids if vid not in known_vacancies]

            if new_vacancies:
                print(f"[INFO] Found {len(new_vacancies)} NEW vacancies!")
                send_telegram_alert(new_vacancies)

                for v in new_vacancies:
                    known_vacancies.add(v)
                save_known_vacancies(KNOWN_VACANCIES_FILE, known_vacancies)
            else:
                print("[INFO] No new vacancies found.")

        except Exception as e:
            print(f"[ERROR] Something went wrong: {e}")

        print(f"[INFO] Sleeping for {CHECK_INTERVAL} seconds...")
        time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    main()
