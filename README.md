# 🚀 Lead Generation Pro

A professional desktop application for extracting and enriching business leads - an Apollo/Hunter.io alternative built with Python and CustomTkinter.

## Features

### Core Capabilities
- **Multi-Source Scraping**: Google Maps integration via Playwright for finding local businesses
- **Website Enrichment**: Automatic extraction of emails, phone numbers, and social media links from business websites
- **Service Need Detection**: AI-powered inference of business needs based on website content analysis
- **Email Validation**: Regex-based email validation with format checking
- **Async Processing**: High-speed concurrent scraping using asyncio and aiohttp
- **Anti-Bot Protection**: Random user-agents and request delays to prevent blocking

### Output Data (Excel Columns)
1. **Name** - Business/Founder name
2. **Address** - Physical location from Google Maps
3. **Service Need** - Inferred needs (Web Design, Marketing, SEO, etc.)
4. **Contact Details** - Phone numbers
5. **Email** - Validated business emails
6. **Business Categories** - Industry classification
7. **Business Information** - Company description, size, founding year
8. **Social Media Accounts** - LinkedIn, Facebook, Instagram, Twitter/X URLs

### UI Features
- Modern dark-themed interface with CustomTkinter
- Real-time progress tracking with visual progress bar
- Live activity log terminal
- Start/Stop controls
- One-click Excel file location opening
- Incremental saving (no data loss if stopped mid-way)

## Installation

### Prerequisites
- Python 3.10 or higher
- pip package manager

### Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Install Playwright Browsers
```bash
playwright install chromium
```

### Step 3: Run the Application
```bash
python main.py
```

## Usage

1. **Launch the Application**
   - Run `python main.py` to open the GUI

2. **Enter Search Parameters**
   - **Target Keyword**: Business type (e.g., "Dentist", "Restaurant", "Software Company")
   - **Location**: Geographic area (e.g., "New York, NY", "Austin, TX")
   - **Max Leads**: Number of leads to extract (1-1000)
   - **API Key** (Optional): Hunter.io API key for enhanced email enrichment

3. **Start Scraping**
   - Click "▶ Start Scraping" to begin
   - Monitor progress in real-time via the progress bar and activity log

4. **Export Results**
   - When complete, click "📁 Open Excel File" to view results
   - Files are saved as `leads_[keyword]_[location]_[timestamp].xlsx`

5. **Stop Early** (Optional)
   - Click "⏹ Stop" to halt scraping
   - Progress is saved automatically every 5 leads

## Technical Architecture

### Components

#### `LeadScraperConfig`
Configuration constants including user agents, social media patterns, and service keywords.

#### `EmailValidator`
Email extraction and validation utilities with regex pattern matching.

#### `BusinessDataExtractor`
Extracts structured data from HTML:
- Social media links
- Phone numbers
- Service needs (keyword-based inference)
- Business information (description, size, founding year)

#### `AsyncScraper`
Core scraping engine using Playwright and aiohttp:
- Google Maps business discovery
- Website content extraction
- Async HTTP requests with timeout handling
- Browser automation with anti-detection measures

#### `LeadManager`
Data management and Excel export:
- Lead collection and storage
- Formatted Excel generation with pandas/openpyxl
- Auto-adjusted column widths
- Styled header rows

#### `ScraperThread`
Background threading for non-blocking UI:
- Runs scraping operations separately from GUI
- Thread-safe callbacks for logging and progress updates
- Graceful stop capability

#### `LeadGenerationApp`
Main GUI application window:
- CustomTkinter-based modern interface
- Input validation
- Real-time progress visualization
- Cross-platform file opening

## Project Structure

```
/workspace/
├── main.py              # Main application code
├── requirements.txt     # Python dependencies
└── README.md           # This file
```

## Output Example

The generated Excel file includes professionally formatted data:

| Name | Address | Service Need | Contact Details | Email | Business Categories | Business Information | Social Media Accounts |
|------|---------|--------------|-----------------|-------|---------------------|---------------------|----------------------|
| ABC Dental | 123 Main St, NYC | Needs Web Design | (555) 123-4567 | info@abcdental.com | Healthcare | Family dentistry serving NYC since 2010 | linkedin.com/company/abc-dental |

## Advanced Configuration

### Service Need Keywords
Modify `SERVICE_KEYWORDS` in `LeadScraperConfig` to customize service detection:

```python
SERVICE_KEYWORDS = {
    'Needs Web Design': ['website redesign', 'web development'],
    'Needs Marketing': ['marketing strategy', 'digital marketing'],
    # Add custom services here
}
```

### User Agents
Add custom user agents to `USER_AGENTS` list for improved stealth.

### Timeout Settings
Adjust `ClientTimeout` in `AsyncScraper.initialize()` for slower/faster connections.

## Troubleshooting

### Common Issues

**Playwright browser not found:**
```bash
playwright install chromium
```

**No leads found:**
- Try different keyword/location combinations
- Increase wait times in `_scroll_page()` method
- Check internet connection

**Application freezes:**
- Ensure scraping runs in background thread (already implemented)
- Reduce max leads for testing

**Excel file not saving:**
- Check write permissions in current directory
- Ensure no other process has the file open

## Legal & Ethical Considerations

⚠️ **Important**: This tool is for educational and legitimate business purposes only.

- Respect website terms of service
- Follow robots.txt guidelines
- Don't overwhelm target servers (built-in delays help)
- Use responsibly and comply with data protection regulations (GDPR, CCPA, etc.)
- Only scrape publicly available information

## Performance Tips

1. **Start Small**: Test with 10-20 leads before scaling
2. **Use Specific Keywords**: "Italian Restaurant" vs just "Restaurant"
3. **Schedule Runs**: Run during off-peak hours for better performance
4. **Monitor Logs**: Watch for rate limiting warnings
5. **Save Frequently**: Incremental saves protect your data

## Future Enhancements

Potential improvements for production use:

- [ ] Integration with Hunter.io/Tomba APIs for email verification
- [ ] Multi-threaded website scraping for faster processing
- [ ] Proxy rotation support
- [ ] CAPTCHA solving integration
- [ ] Database storage option (SQLite/PostgreSQL)
- [ ] CSV export alongside Excel
- [ ] Lead scoring system
- [ ] Duplicate detection
- [ ] Scheduled scraping jobs
- [ ] Email campaign integration

## Support

For issues or questions:
1. Check the activity log for error messages
2. Verify all dependencies are installed
3. Ensure Playwright browsers are installed
4. Test with small lead counts first

## License

MIT License - Free for personal and commercial use with attribution.

---

**Built with ❤️ using Python, CustomTkinter, Playwright, and AsyncIO**

Version: 1.0.0
