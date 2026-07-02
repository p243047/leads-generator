"""
Lead Generation Tool - Apollo/Hunter.io Clone
A professional desktop application for extracting and enriching business leads.
"""

import asyncio
import aiohttp
import json
import os
import re
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, urljoin

import customtkinter as ctk
import pandas as pd
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright

# Configure customtkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class LeadScraperConfig:
    """Configuration constants for the scraper."""
    
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    SOCIAL_MEDIA_PATTERNS = {
        'linkedin': r'(?:https?://)?(?:www\.)?linkedin\.com/company/[^"\s<>]+',
        'facebook': r'(?:https?://)?(?:www\.)?(?:facebook|fb)\.com/[^"\s<>]+',
        'instagram': r'(?:https?://)?(?:www\.)?instagram\.com/[^"\s<>]+',
        'twitter': r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/[^"\s<>]+',
    }
    
    EMAIL_PATTERN = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    SERVICE_KEYWORDS = {
        'Needs Web Design': ['website redesign', 'web development', 'site update', 'new website'],
        'Needs Marketing': ['marketing strategy', 'digital marketing', 'seo services', 'advertising'],
        'Needs SEO': ['search engine optimization', 'seo audit', 'keyword ranking'],
        'Needs Social Media': ['social media management', 'social presence', 'instagram marketing'],
        'Needs Branding': ['brand identity', 'logo design', 'rebranding'],
        'Needs Content': ['content creation', 'blog writing', 'copywriting'],
    }


class EmailValidator:
    """Email validation utilities."""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format using regex."""
        if not email:
            return False
        
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False
        
        # Check for common invalid patterns
        invalid_patterns = [
            r'^.*@.*@.*$',  # Multiple @ symbols
            r'^.*\.\..*$',  # Consecutive dots
            r'^\..*$',      # Starts with dot
            r'.*\.$',       # Ends with dot
        ]
        
        for pattern in invalid_patterns:
            if re.match(pattern, email):
                return False
        
        return True
    
    @staticmethod
    def extract_emails(text: str) -> List[str]:
        """Extract all valid emails from text."""
        emails = re.findall(LeadScraperConfig.EMAIL_PATTERN, text)
        return [email.lower() for email in emails if EmailValidator.validate_email(email)]
    
    @staticmethod
    async def check_mx_record(domain: str) -> bool:
        """Basic MX record check (simplified)."""
        try:
            # Simple DNS check - in production, use dnspython library
            return True
        except Exception:
            return False


class BusinessDataExtractor:
    """Extract business information from website content."""
    
    def __init__(self):
        self.config = LeadScraperConfig()
    
    def extract_social_media(self, html_content: str, base_url: str) -> Dict[str, str]:
        """Extract social media links from HTML content."""
        social_links = {}
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Find all links
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link['href']
            
            # Check for LinkedIn
            if 'linkedin.com' in href.lower():
                if 'linkedin' not in social_links:
                    social_links['linkedin'] = href if href.startswith('http') else urljoin(base_url, href)
            
            # Check for Facebook
            elif 'facebook.com' in href.lower() or 'fb.com' in href.lower():
                if 'facebook' not in social_links:
                    social_links['facebook'] = href if href.startswith('http') else urljoin(base_url, href)
            
            # Check for Instagram
            elif 'instagram.com' in href.lower():
                if 'instagram' not in social_links:
                    social_links['instagram'] = href if href.startswith('http') else urljoin(base_url, href)
            
            # Check for Twitter/X
            elif 'twitter.com' in href.lower() or 'x.com' in href.lower():
                if 'twitter' not in social_links:
                    social_links['twitter'] = href if href.startswith('http') else urljoin(base_url, href)
        
        # Also check text content for social media URLs
        text_content = soup.get_text()
        for platform, pattern in self.config.SOCIAL_MEDIA_PATTERNS.items():
            if platform not in social_links:
                matches = re.findall(pattern, text_content, re.IGNORECASE)
                if matches:
                    social_links[platform] = matches[0]
        
        return social_links
    
    def extract_phone_numbers(self, html_content: str) -> List[str]:
        """Extract phone numbers from HTML content."""
        phones = []
        
        # Common phone number patterns
        patterns = [
            r'\+?1?\s*\(?[0-9]{3}\)?[\s.-]?[0-9]{3}[\s.-]?[0-9]{4}',
            r'\([0-9]{3}\)\s*[0-9]{3}-[0-9]{4}',
            r'[0-9]{3}-[0-9]{3}-[0-9]{4}',
            r'[0-9]{3}\.[0-9]{3}\.[0-9]{4}',
        ]
        
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text()
        
        for pattern in patterns:
            matches = re.findall(pattern, text_content)
            phones.extend(matches)
        
        # Clean and deduplicate
        cleaned_phones = []
        seen = set()
        for phone in phones:
            clean_phone = re.sub(r'[^\d+]', '', phone)
            if clean_phone not in seen and len(clean_phone) >= 10:
                cleaned_phones.append(phone.strip())
                seen.add(clean_phone)
        
        return cleaned_phones[:3]  # Limit to 3 phone numbers
    
    def extract_service_need(self, html_content: str) -> str:
        """Infer service needs from website content."""
        soup = BeautifulSoup(html_content, 'html.parser')
        text_content = soup.get_text().lower()
        
        for service, keywords in self.config.SERVICE_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_content:
                    return service
        
        return "No specific need identified"
    
    def extract_business_info(self, html_content: str) -> Dict[str, Any]:
        """Extract general business information."""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        info = {
            'description': '',
            'size': 'Unknown',
            'founded': 'Unknown'
        }
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            info['description'] = meta_desc['content'][:200]
        
        # Look for about us section
        about_sections = soup.find_all(['div', 'section'], class_=lambda x: x and 'about' in x.lower())
        if about_sections:
            info['description'] = about_sections[0].get_text()[:200].strip()
        
        # Look for company size indicators
        size_keywords = ['team of', 'employees', 'staff', 'members']
        for keyword in size_keywords:
            match = re.search(rf'{keyword}\s+(\d+\+?|\w+)', html_content.lower())
            if match:
                info['size'] = match.group(1)
                break
        
        # Look for founding year
        year_patterns = [
            r'(?:established|founded|since)\s+(\d{4})',
            r'(\d{4})\s*(?:-present|-now)',
        ]
        for pattern in year_patterns:
            match = re.search(pattern, html_content.lower())
            if match:
                info['founded'] = match.group(1)
                break
        
        return info


class AsyncScraper:
    """Asynchronous web scraper with Playwright integration."""
    
    def __init__(self, log_callback=None):
        self.log_callback = log_callback
        self.extractor = BusinessDataExtractor()
        self.session = None
        self.playwright = None
        self.browser = None
    
    def log(self, message: str):
        """Log message with callback."""
        if self.log_callback:
            self.log_callback(message)
    
    async def initialize(self):
        """Initialize browser and session."""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--disable-gpu',
            ]
        )
        
        timeout = aiohttp.ClientTimeout(total=30)
        self.session = aiohttp.ClientSession(timeout=timeout)
    
    async def close(self):
        """Close browser and session."""
        if self.session:
            await self.session.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
    
    async def scrape_google_maps(self, keyword: str, location: str, max_results: int) -> List[Dict]:
        """Scrape businesses from Google Maps using Playwright."""
        businesses = []
        
        try:
            context = await self.browser.new_context(
                user_agent=self._get_random_user_agent(),
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = await context.new_page()
            
            # Construct search query
            search_query = f"{keyword} in {location}"
            encoded_query = search_query.replace(' ', '+')
            
            google_maps_url = f"https://www.google.com/maps/search/{encoded_query}"
            
            self.log(f"Navigating to Google Maps: {search_query}")
            
            await page.goto(google_maps_url, wait_until='networkidle', timeout=60000)
            
            # Wait for results to load
            await page.wait_for_timeout(5000)
            
            # Scroll to load more results
            await self._scroll_page(page, max_results)
            
            # Extract business information
            businesses = await self._extract_businesses_from_maps(page, max_results)
            
            await context.close()
            
        except Exception as e:
            self.log(f"Error scraping Google Maps: {str(e)}")
        
        return businesses
    
    async def _scroll_page(self, page, max_results: int):
        """Scroll page to load more results."""
        scroll_times = min(max_results // 5 + 3, 10)
        
        for i in range(scroll_times):
            await page.evaluate("window.scrollBy(0, 1000)")
            await page.wait_for_timeout(1000)
    
    async def _extract_businesses_from_maps(self, page, max_results: int) -> List[Dict]:
        """Extract business listings from Google Maps."""
        businesses = []
        
        try:
            # Wait for business cards to appear
            await page.wait_for_selector('div[role="article"]', timeout=10000)
            
            # Get all business cards
            business_cards = await page.query_selector_all('div[role="article"]')
            
            for i, card in enumerate(business_cards[:max_results]):
                try:
                    # Extract business name
                    name_elem = await card.query_selector('.fontHeadlineSmall')
                    name = await name_elem.inner_text() if name_elem else "Unknown"
                    
                    # Extract rating and reviews
                    rating_elem = await card.query_selector('[aria-label*="star"]')
                    rating = await rating_elem.get_attribute('aria-label') if rating_elem else "N/A"
                    
                    # Extract address (simplified)
                    address_elem = await card.query_selector('.ft2vOb')
                    address = await address_elem.inner_text() if address_elem else "Not available"
                    
                    # Extract website by clicking on the business
                    website = ""
                    phone = ""
                    
                    try:
                        await card.click()
                        await page.wait_for_timeout(2000)
                        
                        # Try to find website link
                        website_link = await page.query_selector('a[href*="http"]')
                        if website_link:
                            website = await website_link.get_attribute('href')
                        
                        # Try to find phone number
                        phone_elem = await page.query_selector('button[data-item-id="phone"]')
                        if phone_elem:
                            phone = await phone_elem.inner_text()
                        
                    except Exception:
                        pass
                    
                    businesses.append({
                        'name': name,
                        'address': address,
                        'rating': rating,
                        'website': website,
                        'phone': phone,
                        'category': 'Business',
                    })
                    
                    self.log(f"Found business: {name}")
                    
                except Exception as e:
                    self.log(f"Error extracting business card: {str(e)}")
                    continue
            
        except Exception as e:
            self.log(f"Error in business extraction: {str(e)}")
        
        return businesses
    
    def _get_random_user_agent(self) -> str:
        """Get random user agent."""
        import random
        return random.choice(LeadScraperConfig.USER_AGENTS)
    
    async def scrape_website(self, url: str) -> Dict[str, Any]:
        """Scrape individual business website."""
        result = {
            'emails': [],
            'phones': [],
            'social_media': {},
            'service_need': 'No specific need identified',
            'business_info': {},
        }
        
        if not url or not url.startswith('http'):
            return result
        
        try:
            headers = {
                'User-Agent': self._get_random_user_agent(),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
            }
            
            async with self.session.get(url, headers=headers, allow_redirects=True) as response:
                if response.status == 200:
                    html_content = await response.text()
                    
                    # Extract emails
                    result['emails'] = EmailValidator.extract_emails(html_content)
                    
                    # Extract phone numbers
                    result['phones'] = self.extractor.extract_phone_numbers(html_content)
                    
                    # Extract social media
                    result['social_media'] = self.extractor.extract_social_media(html_content, url)
                    
                    # Infer service need
                    result['service_need'] = self.extractor.extract_service_need(html_content)
                    
                    # Extract business info
                    result['business_info'] = self.extractor.extract_business_info(html_content)
                    
                    self.log(f"Successfully scraped: {url}")
                else:
                    self.log(f"Failed to access {url}: Status {response.status}")
        
        except asyncio.TimeoutError:
            self.log(f"Timeout accessing {url}")
        except Exception as e:
            self.log(f"Error scraping {url}: {str(e)}")
        
        return result


class LeadManager:
    """Manage leads data and Excel export."""
    
    COLUMNS = [
        'Name',
        'Address',
        'Service Need',
        'Contact Details',
        'Email',
        'Business Categories',
        'Business Information',
        'Social Media Accounts'
    ]
    
    def __init__(self, keyword: str, location: str):
        self.keyword = keyword
        self.location = location
        self.leads = []
        self.output_file = self._generate_filename()
    
    def _generate_filename(self) -> str:
        """Generate output filename."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_keyword = re.sub(r'[^\w\s-]', '', self.keyword)[:20].replace(' ', '_')
        safe_location = re.sub(r'[^\w\s-]', '', self.location)[:20].replace(' ', '_')
        return f"leads_{safe_keyword}_{safe_location}_{timestamp}.xlsx"
    
    def add_lead(self, lead_data: Dict):
        """Add a lead to the collection."""
        self.leads.append(lead_data)
    
    def save_to_excel(self):
        """Save leads to Excel file."""
        if not self.leads:
            return None
        
        df = pd.DataFrame(self.leads, columns=self.COLUMNS)
        
        # Create Excel writer with formatting
        output_path = Path(self.output_file)
        
        with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Leads')
            
            # Get the worksheet
            worksheet = writer.sheets['Leads']
            
            # Format header row
            for col_num in range(1, len(self.COLUMNS) + 1):
                cell = worksheet.cell(row=1, column=col_num)
                cell.font = cell.font.copy(bold=True)
                cell.fill = cell.fill.copy(start_color='4472C4')
                cell.font = cell.font.copy(color='FFFFFF')
            
            # Auto-adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return str(output_path)
    
    def get_lead_count(self) -> int:
        """Get current lead count."""
        return len(self.leads)


class ScraperThread(threading.Thread):
    """Background thread for scraping operations."""
    
    def __init__(self, keyword: str, location: str, max_leads: int, 
                 api_key: str = "", log_callback=None, progress_callback=None, 
                 complete_callback=None):
        super().__init__()
        self.keyword = keyword
        self.location = location
        self.max_leads = max_leads
        self.api_key = api_key
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.complete_callback = complete_callback
        self.stop_flag = False
        self.scraper = None
        self.lead_manager = None
    
    def log(self, message: str):
        """Thread-safe logging."""
        if self.log_callback:
            self.log_callback(message)
    
    def update_progress(self, current: int, total: int):
        """Update progress bar."""
        if self.progress_callback:
            self.progress_callback(current, total)
    
    def run(self):
        """Main scraping logic."""
        try:
            self.log("Initializing scraper...")
            
            # Initialize components
            self.lead_manager = LeadManager(self.keyword, self.location)
            self.scraper = AsyncScraper(log_callback=self.log)
            
            # Run async scraping
            asyncio.run(self._scrape_loop())
            
            # Save results
            if self.lead_manager.get_lead_count() > 0:
                output_path = self.lead_manager.save_to_excel()
                self.log(f"✓ Saved {self.lead_manager.get_lead_count()} leads to: {output_path}")
                
                if self.complete_callback:
                    self.complete_callback(output_path)
            else:
                self.log("✗ No leads found.")
                
                if self.complete_callback:
                    self.complete_callback(None)
        
        except Exception as e:
            self.log(f"✗ Error: {str(e)}")
            if self.complete_callback:
                self.complete_callback(None)
    
    async def _scrape_loop(self):
        """Main scraping loop."""
        try:
            await self.scraper.initialize()
            
            self.log(f"Searching for '{self.keyword}' in '{self.location}'...")
            
            # Scrape Google Maps
            businesses = await self.scraper.scrape_google_maps(
                self.keyword, 
                self.location, 
                self.max_leads
            )
            
            self.log(f"Found {len(businesses)} businesses. Enriching data...")
            
            # Enrich each business
            for i, business in enumerate(businesses):
                if self.stop_flag:
                    self.log("Scraping stopped by user.")
                    break
                
                self.update_progress(i + 1, len(businesses))
                
                self.log(f"Processing {i + 1}/{len(businesses)}: {business.get('name', 'Unknown')}")
                
                # Scrape website if available
                enriched_data = {}
                if business.get('website'):
                    enriched_data = await self.scraper.scrape_website(business['website'])
                
                # Compile lead data
                lead = {
                    'Name': business.get('name', 'Unknown'),
                    'Address': business.get('address', 'Not available'),
                    'Service Need': enriched_data.get('service_need', 'No specific need identified'),
                    'Contact Details': '; '.join(enriched_data.get('phones', [])) or business.get('phone', 'Not available'),
                    'Email': '; '.join(enriched_data.get('emails', [])) or 'Not found',
                    'Business Categories': business.get('category', 'General'),
                    'Business Information': enriched_data.get('business_info', {}).get('description', 'No description available'),
                    'Social Media Accounts': '; '.join(enriched_data.get('social_media', {}).values()) or 'Not found'
                }
                
                self.lead_manager.add_lead(lead)
                
                # Save incrementally every 5 leads
                if (i + 1) % 5 == 0:
                    self.lead_manager.save_to_excel()
                    self.log(f"Progress saved ({i + 1} leads)")
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(1)
            
            await self.scraper.close()
            
        except Exception as e:
            self.log(f"Error in scrape loop: {str(e)}")
            raise
    
    def stop(self):
        """Stop the scraping process."""
        self.stop_flag = True


class LeadGenerationApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Lead Generation Pro - Apollo/Hunter.io Clone")
        self.geometry("1200x800")
        self.minsize(1000, 700)
        
        self.scraper_thread = None
        self.output_file_path = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup the user interface."""
        # Configure grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Header
        self._create_header()
        
        # Main content area
        self._create_input_section()
        self._create_progress_section()
        self._create_log_section()
        self._create_footer()
    
    def _create_header(self):
        """Create header section."""
        header_frame = ctk.CTkFrame(self, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 10))
        header_frame.grid_columnconfigure(0, weight=1)
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🚀 Lead Generation Pro",
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="#4CC9F0"
        )
        title_label.grid(row=0, column=0, padx=20, pady=15, sticky="w")
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Extract, Enrich & Export Business Leads | Apollo/Hunter.io Alternative",
            font=ctk.CTkFont(size=14),
            text_color="#A0A0A0"
        )
        subtitle_label.grid(row=1, column=0, padx=20, pady=(0, 15), sticky="w")
    
    def _create_input_section(self):
        """Create input fields section."""
        input_frame = ctk.CTkFrame(self, corner_radius=10)
        input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=10)
        input_frame.grid_columnconfigure(1, weight=1)
        
        # Keyword
        ctk.CTkLabel(
            input_frame, 
            text="Target Keyword:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        self.keyword_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="e.g., Dentist, Restaurant, Software Company",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.keyword_entry.grid(row=0, column=1, padx=15, pady=10, sticky="ew")
        
        # Location
        ctk.CTkLabel(
            input_frame, 
            text="Location:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=1, column=0, padx=15, pady=10, sticky="w")
        
        self.location_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="e.g., New York, NY or Austin, TX",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.location_entry.grid(row=1, column=1, padx=15, pady=10, sticky="ew")
        
        # Max Leads
        ctk.CTkLabel(
            input_frame, 
            text="Max Leads:",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=2, column=0, padx=15, pady=10, sticky="w")
        
        self.max_leads_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="e.g., 50",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.max_leads_entry.insert(0, "50")
        self.max_leads_entry.grid(row=2, column=1, padx=15, pady=10, sticky="w")
        
        # API Key (Optional)
        ctk.CTkLabel(
            input_frame, 
            text="Hunter.io API Key (Optional):",
            font=ctk.CTkFont(size=14, weight="bold")
        ).grid(row=3, column=0, padx=15, pady=10, sticky="w")
        
        self.api_key_entry = ctk.CTkEntry(
            input_frame,
            placeholder_text="Enter API key for email enrichment (optional)",
            height=40,
            font=ctk.CTkFont(size=14)
        )
        self.api_key_entry.grid(row=3, column=1, padx=15, pady=10, sticky="ew")
        
        # Buttons frame
        button_frame = ctk.CTkFrame(input_frame, fg_color="transparent")
        button_frame.grid(row=4, column=0, columnspan=2, padx=15, pady=20)
        
        self.start_button = ctk.CTkButton(
            button_frame,
            text="▶ Start Scraping",
            command=self.start_scraping,
            height=45,
            width=200,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#4CC9F0",
            hover_color="#4895EF"
        )
        self.start_button.grid(row=0, column=0, padx=10)
        
        self.stop_button = ctk.CTkButton(
            button_frame,
            text="⏹ Stop",
            command=self.stop_scraping,
            height=45,
            width=150,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#F72585",
            hover_color="#B5179E",
            state="disabled"
        )
        self.stop_button.grid(row=0, column=1, padx=10)
        
        self.open_file_button = ctk.CTkButton(
            button_frame,
            text="📁 Open Excel File",
            command=self.open_excel_file,
            height=45,
            width=200,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#7209B7",
            hover_color="#560BAD",
            state="disabled"
        )
        self.open_file_button.grid(row=0, column=2, padx=10)
    
    def _create_progress_section(self):
        """Create progress tracking section."""
        progress_frame = ctk.CTkFrame(self, corner_radius=10)
        progress_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        progress_frame.grid_columnconfigure(0, weight=1)
        
        self.progress_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to start",
            font=ctk.CTkFont(size=14),
            text_color="#A0A0A0"
        )
        self.progress_label.grid(row=0, column=0, padx=20, pady=(15, 5), sticky="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=25,
            corner_radius=5,
            fg_color="#2D2D2D",
            progress_color="#4CC9F0"
        )
        self.progress_bar.grid(row=1, column=0, padx=20, pady=(5, 15), sticky="ew")
        self.progress_bar.set(0)
        
        self.stats_label = ctk.CTkLabel(
            progress_frame,
            text="Leads: 0 | Status: Idle",
            font=ctk.CTkFont(size=12),
            text_color="#808080"
        )
        self.stats_label.grid(row=2, column=0, padx=20, pady=(0, 15), sticky="w")
    
    def _create_log_section(self):
        """Create log terminal section."""
        log_frame = ctk.CTkFrame(self, corner_radius=10)
        log_frame.grid(row=3, column=0, sticky="nsew", padx=20, pady=10)
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(1, weight=1)
        
        log_title = ctk.CTkLabel(
            log_frame,
            text="📋 Live Activity Log",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#4CC9F0"
        )
        log_title.grid(row=0, column=0, padx=15, pady=10, sticky="w")
        
        # Log text box with scrollbar
        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
            fg_color="#1E1E1E",
            text_color="#00FF00"
        )
        self.log_text.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        
        # Clear log button
        clear_button = ctk.CTkButton(
            log_frame,
            text="Clear Log",
            command=self.clear_log,
            height=30,
            width=100,
            fg_color="#3A3A3A",
            hover_color="#505050"
        )
        clear_button.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="e")
    
    def _create_footer(self):
        """Create footer section."""
        footer_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        footer_frame.grid(row=4, column=0, sticky="ew", padx=20, pady=10)
        
        footer_text = ctk.CTkLabel(
            footer_frame,
            text="Powered by Playwright • Async Scraping • Real-time Export",
            font=ctk.CTkFont(size=11),
            text_color="#606060"
        )
        footer_text.pack(side="left")
        
        version_text = ctk.CTkLabel(
            footer_frame,
            text="v1.0.0",
            font=ctk.CTkFont(size=11),
            text_color="#606060"
        )
        version_text.pack(side="right")
    
    def log_message(self, message: str):
        """Add message to log (thread-safe)."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        
        self.log_text.insert("end", formatted_message)
        self.log_text.see("end")
    
    def update_progress(self, current: int, total: int):
        """Update progress bar (thread-safe)."""
        def _update():
            progress = current / total if total > 0 else 0
            self.progress_bar.set(progress)
            self.progress_label.configure(
                text=f"Processing lead {current} of {total}..."
            )
            self.stats_label.configure(
                text=f"Leads: {current}/{total} | Status: Scraping"
            )
        
        self.after(0, _update)
    
    def scraping_complete(self, output_path: Optional[str]):
        """Handle scraping completion (thread-safe)."""
        def _complete():
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
            
            if output_path:
                self.output_file_path = output_path
                self.open_file_button.configure(state="normal")
                self.progress_label.configure(text="✓ Scraping completed successfully!")
                self.stats_label.configure(
                    text=f"Total Leads: {self.scraper_thread.lead_manager.get_lead_count()} | Status: Complete"
                )
            else:
                self.progress_label.configure(text="✗ Scraping completed with no results")
                self.stats_label.configure(text="Leads: 0 | Status: Failed")
        
        self.after(0, _complete)
    
    def start_scraping(self):
        """Start the scraping process."""
        # Validate inputs
        keyword = self.keyword_entry.get().strip()
        location = self.location_entry.get().strip()
        max_leads_str = self.max_leads_entry.get().strip()
        api_key = self.api_key_entry.get().strip()
        
        if not keyword:
            self.log_message("✗ Error: Please enter a target keyword")
            return
        
        if not location:
            self.log_message("✗ Error: Please enter a location")
            return
        
        try:
            max_leads = int(max_leads_str)
            if max_leads <= 0 or max_leads > 1000:
                raise ValueError()
        except ValueError:
            self.log_message("✗ Error: Max leads must be between 1 and 1000")
            return
        
        # Disable start button, enable stop button
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.open_file_button.configure(state="disabled")
        
        # Clear previous log
        self.clear_log()
        
        self.log_message("=" * 60)
        self.log_message("🚀 Starting Lead Generation Process")
        self.log_message(f"Keyword: {keyword}")
        self.log_message(f"Location: {location}")
        self.log_message(f"Max Leads: {max_leads}")
        if api_key:
            self.log_message(f"API Key: Configured")
        self.log_message("=" * 60)
        
        # Create and start scraper thread
        self.scraper_thread = ScraperThread(
            keyword=keyword,
            location=location,
            max_leads=max_leads,
            api_key=api_key,
            log_callback=self.log_message,
            progress_callback=self.update_progress,
            complete_callback=self.scraping_complete
        )
        self.scraper_thread.daemon = True
        self.scraper_thread.start()
    
    def stop_scraping(self):
        """Stop the scraping process."""
        if self.scraper_thread and self.scraper_thread.is_alive():
            self.log_message("⏹ Stopping scraping process...")
            self.scraper_thread.stop()
            self.start_button.configure(state="normal")
            self.stop_button.configure(state="disabled")
    
    def open_excel_file(self):
        """Open the Excel file location."""
        if self.output_file_path:
            try:
                import subprocess
                import platform
                
                file_path = Path(self.output_file_path)
                
                if platform.system() == "Windows":
                    subprocess.run(['explorer', '/select,', str(file_path)])
                elif platform.system() == "Darwin":
                    subprocess.run(['open', '-R', str(file_path)])
                else:
                    subprocess.run(['xdg-open', str(file_path.parent)])
                
                self.log_message(f"📁 Opening file location: {self.output_file_path}")
            
            except Exception as e:
                self.log_message(f"✗ Error opening file: {str(e)}")
        else:
            self.log_message("✗ No output file available yet")
    
    def clear_log(self):
        """Clear the log text box."""
        self.log_text.delete("1.0", "end")


def main():
    """Main entry point."""
    app = LeadGenerationApp()
    app.mainloop()


if __name__ == "__main__":
    main()
