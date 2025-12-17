import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firestore
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

print("✅ Firestore initialized")

async def set_rows_per_page(page):
    try:
        print("🔄 Attempting to set rows per page to 102...")
        # Click the rows per page dropdown
        dropdown = await page.wait_for_selector(
            'div.flex.items-center.justify-between.cursor-pointer.border',
            timeout=5000
        )
        await dropdown.click()
        
        # Wait for dropdown options to appear
        await page.wait_for_selector('div.absolute.top-10.right-0', timeout=3000)
        
        # Click the 102 option
        option = await page.wait_for_selector(
            'p:text-is("102")',
            state='visible',
            timeout=3000
        )
        await option.click()
        
        # Wait for page to reload
        await page.wait_for_load_state('networkidle')
        print("✅ Successfully set rows per page to 102")
        return True
    except Exception as e:
        print(f"⚠️ Couldn't set rows per page: {str(e)}")
        return False

async def scrape_page(page, page_num):
    hackathons = []
    try:
        print(f"📖 Processing page {page_num}...")
        await page.wait_for_selector('div.flex.flex-col.gap-4.bg-white', timeout=15000)
        
        content = await page.content()
        soup = BeautifulSoup(content, 'html.parser')
        cards = soup.find_all('div', class_='flex flex-col gap-4 bg-white')
        
        for card in cards:
            try:
                # Extract hackathon title and link
                title_elem = card.find('p', class_=lambda x: x and 'text-h2sSlate-800' in x)
                title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                
                # Find the link
                link = None
                link_parent = card.find_parent('a')
                if link_parent and link_parent.has_attr('href'):
                    link = link_parent['href']
                    if not link.startswith('http'):
                        link = f"https://vision.hack2skill.com{link}"
                
                img_tag = card.find('img')
                image_url = img_tag['src'] if img_tag and img_tag.has_attr('src') else None
                
                event_type = "Unknown"
                event_mode = "Unknown"
                event_info = card.find('div', class_=lambda x: x and 'bg-h2sPurple-50' in x)
                if event_info:
                    event_details = [p.get_text(strip=True) for p in event_info.find_all('p')]
                    if event_details:
                        event_type = event_details[0]
                        if len(event_details) > 1:
                            event_mode = event_details[1]
                
                end_date = "Unknown"
                date_div = card.find('div', class_=lambda x: x and 'text-h2sSlate-500' in x)
                if date_div:
                    date_p = date_div.find('p', class_=lambda x: x and 'text-subtitle2v1' in x)
                    if date_p:
                        end_date = date_p.get_text(strip=True)
                
                hackathon_data = {
                    'title': title,
                    'link': link if link else "Not available",
                    'image_url': image_url,
                    'event_type': event_type,
                    'event_mode': event_mode,
                    'registration_ends': end_date,
                    'source': 'hack2skill',
                    'page_num': page_num,
                    'timestamp': firestore.SERVER_TIMESTAMP
                }
                
                hackathons.append(hackathon_data)
                print(f"✔️ Found: {title} ({link})")
                
            except Exception as e:
                print(f"❌ Error processing card: {str(e)}")
                continue
                
    except Exception as e:
        print(f"❌ Error processing page {page_num}: {str(e)}")
    
    return hackathons

async def go_to_next_page(page):
    try:
        next_button = await page.query_selector('button[aria-label="Next page"]')
        if next_button:
            is_disabled = await next_button.get_attribute('disabled') or 'disabled' in await next_button.get_attribute('class')
            if not is_disabled:
                await next_button.click()
                await page.wait_for_load_state('networkidle')
                await asyncio.sleep(1)
                return True
        return False
    except Exception as e:
        print(f"❌ Error navigating to next page: {str(e)}")
        return False

async def scrape_hackathons(page):
    all_hackathons = []
    
    # First try to set rows per page to 102
    rows_set = await set_rows_per_page(page)
    
    if rows_set:
        # If successful, scrape both pages (102 rows should show all on 2 pages)
        for page_num in [1, 2]:
            if page_num > 1:
                if not await go_to_next_page(page):
                    break
            
            hackathons = await scrape_page(page, page_num)
            all_hackathons.extend(hackathons)
    else:
        # Fallback: Paginate through each page (up to 13)
        max_pages = 13
        for page_num in range(1, max_pages + 1):
            if page_num > 1:
                if not await go_to_next_page(page):
                    break
            
            hackathons = await scrape_page(page, page_num)
            if not hackathons:  # Stop if no hackathons found on page
                break
                
            all_hackathons.extend(hackathons)
    
    return all_hackathons

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=100)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1280, "height": 1080})

        print("🌐 Navigating to hack2skill hackathons page...")
        try:
            await page.goto('https://vision.hack2skill.com/hackathons-listing', timeout=60000)
            await page.wait_for_selector('div.grid.grid-cols-1', timeout=30000)
            
            # Take screenshot for debugging
            await page.screenshot(path='initial_page.png')
            
            # Scrape all hackathons
            all_hackathons = await scrape_hackathons(page)
            
            # Save to Firestore under hackathons/hack2skill collection
            saved_count = 0
            for hackathon in all_hackathons:
                try:
                    # Create a document reference with an auto-generated ID
                    doc_ref = db.collection('hackathons').document('hack2skill').collection('events').document()
                    doc_ref.set(hackathon)
                    saved_count += 1
                except Exception as e:
                    print(f"❌ Firestore write failed: {str(e)}")
            
            print(f"✅ Scraping complete. Saved {saved_count}/{len(all_hackathons)} hackathons to hackathons/hack2skill/events")
            
        except Exception as e:
            print(f"❌ Fatal error: {str(e)}")
        finally:
            await browser.close()

asyncio.run(run())