import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import firebase_admin
from firebase_admin import credentials, firestore

# --------------------------
# 1. Initialize Firestore
# --------------------------
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("✅ Firestore initialized")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()

        print("🔐 Logging into Devpost...")
        await page.goto('https://secure.devpost.com/users/login?ref=top-nav-login')

        # Fill login details
        await page.fill('input[name="user[email]"]', 'erroreditz823@gmail.com')
        await page.fill('input[name="user[password]"]', '@Godwin1603')

        # Click login
        await page.click('#submit-form')

        # Wait for login to complete
        await page.wait_for_selector('a[href="/hackathons"]', timeout=10000)

        print("✅ Login successful! Navigating to hackathons page...")

        # Click "View all hackathons"
        await page.click('a[href="/hackathons"]')
        await page.wait_for_selector('a.flex-row.tile-anchor', timeout=10000)

        # Improved scrolling logic with mouse wheel
        print("🔄 Loading all hackathons (this may take a while)...")
        previous_card_count = 0
        attempts = 0
        max_attempts = 5
        
        while attempts < max_attempts:
            # Mouse wheel scroll
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1)  # 1-second wait between scrolls
            
            cards = await page.query_selector_all('a.flex-row.tile-anchor')
            current_card_count = len(cards)
            
            if current_card_count == previous_card_count:
                attempts += 1
                print(f"⚠️ No new cards loaded (attempt {attempts}/{max_attempts})")
            else:
                attempts = 0
                print(f"📜 Loaded {current_card_count} hackathons...")
            
            if attempts >= max_attempts:
                print("✅ Reached end of hackathon list.")
                break
                
            previous_card_count = current_card_count

        # Parse final page content
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        cards = soup.find_all('a', class_='flex-row tile-anchor')
        print(f"✅ Found {len(cards)} hackathons total")

        saved_count = 0

        for card in cards:
            # Extract all fields
            href = card.get('href')
            link = href if href.startswith('http') else f"https://devpost.com{href}"

            title = card.find('h3', class_='mb-4').get_text(strip=True) if card.find('h3', class_='mb-4') else "Unknown"
            
            days_left = card.select_one('div.hackathon-status div.round.label.status-label').get_text(strip=True) if card.select_one('div.hackathon-status div.round.label.status-label') else "Unknown"
            
            prize = card.find('span', class_='prize-amount').get_text(strip=True) if card.find('span', class_='prize-amount') else "Unknown"
            
            participants_tag = card.find('div', class_='participants')
            participants = participants_tag.find('strong').get_text(strip=True) if participants_tag and participants_tag.find('strong') else "Unknown"
            
            host = card.find('span', class_='label round host-label').get_text(strip=True) if card.find('span', class_='label round host-label') else "Unknown"
            
            submission_period = card.find('div', class_='submission-period').get_text(strip=True) if card.find('div', class_='submission-period') else "Unknown"

            theme_spans = card.select('span.label.theme-label.mr-2.mb-2')
            themes = [span['title'] for span in theme_spans if span.has_attr('title')]
            print(themes)

            # Prepare data for Firestore
            hackathon_data = {
                'title': title,
                'link': link,
                'days_left': days_left,
                'prize': prize,
                'participants': participants,
                'host': host,
                'submission_period': submission_period,
                'themes': themes
            }

            print("---------------")
            print(f"Title: {title}")
            print(f"Link: {link}")
            print(f"Days Left: {days_left}")
            print(f"Prize: {prize}")
            print(f"Participants: {participants}")
            print(f"Host: {host}")
            print(f"Submission Period: {submission_period}")
            print(f"Themes: {themes}")

            try:
                doc_ref = db.collection('hackathons').document()
                doc_ref.set(hackathon_data)
                print(f"✅ Saved to Firestore: {title}")
                saved_count += 1
            except Exception as e:
                print(f"❌ Firestore write failed for {title}: {e}")

        print("---------------")
        print(f"✅ Scraping complete. Saved {saved_count}/{len(cards)} hackathons to Firestore")
        
        await browser.close()

asyncio.run(run())