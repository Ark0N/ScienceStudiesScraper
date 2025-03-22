"""
Google Scholar search module for NMN Study Downloader
"""

import re
import time
import random
import urllib.parse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def search_google_scholar(query, additional_terms, headers, max_results=None):
    """Search Google Scholar for studies related to NMN.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of study metadata
    """
    base_query = query
    if additional_terms:
        # Use at most 3 additional terms to avoid query complexity
        selected_terms = random.sample(additional_terms, min(3, len(additional_terms)))
        base_query += " " + " ".join(selected_terms)
    
    print(f"Searching Google Scholar for: {base_query}")
    
    # Encode the query for URL
    search_query = urllib.parse.quote(base_query)
    url = f"https://scholar.google.com/scholar?q={search_query}&hl=en&as_sdt=0,5&as_vis=1"
    
    # Results to collect
    results = []
    page = 0
    results_per_page = 10
    
    try:
        # Create a session with retry logic for GET only
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Enhanced browser-like headers to avoid being detected as a bot
        scholar_headers = {
            'User-Agent': random.choice([
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0'
            ]),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://scholar.google.com/',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
            'TE': 'Trailers'
        }
        
        while True:
            # Stop if we've reached the maximum number of results
            if max_results and len(results) >= max_results:
                break
                
            # Add page offset for pagination
            page_url = url
            if page > 0:
                page_url = f"{url}&start={page * results_per_page}"
            
            print(f"Fetching page {page+1} from Google Scholar")
            
            # Randomize delay to avoid detection (between 3-7 seconds)
            time.sleep(random.uniform(3, 7))
            
            response = session.get(page_url, headers=scholar_headers, timeout=30, allow_redirects=True)
            
            # Check if we've been blocked or rate-limited
            if "Please show you're not a robot" in response.text or "robot" in response.url:
                print("Google Scholar has detected scraping activity. Please try again later or use a different IP.")
                break
                
            # Parse the HTML response
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract article data from the search results
            articles = soup.select('.gs_r.gs_or.gs_scl')
            if not articles:
                print("No more results found or format changed.")
                break
                
            for article in articles:
                try:
                    # Extract title and link
                    title_elem = article.select_one('.gs_rt a')
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    article_url = title_elem.get('href', '')
                    
                    # Skip if URL is empty or not http/https
                    if not article_url or not (article_url.startswith('http://') or article_url.startswith('https://')):
                        continue
                    
                    # Extract authors, venue, year
                    authors_venue = article.select_one('.gs_a')
                    authors_text = authors_venue.text.strip() if authors_venue else ""
                    
                    # Parse authors
                    authors = []
                    if authors_text:
                        authors_part = authors_text.split(' - ')[0] if ' - ' in authors_text else authors_text
                        authors = [a.strip() for a in authors_part.split(',')]
                    
                    # Extract year
                    year_match = re.search(r'\b(19|20)\d{2}\b', authors_text)
                    publication_date = year_match.group(0) if year_match else "Unknown"
                    
                    # Extract journal/venue
                    journal = "Unknown Journal"
                    venue_match = re.search(r' - (.*?), \d{4}', authors_text)
                    if venue_match:
                        journal = venue_match.group(1).strip()
                    
                    # Extract snippet/abstract
                    snippet = article.select_one('.gs_rs')
                    abstract = snippet.text.strip() if snippet else "Abstract not available"
                    
                    # Extract citation info for DOI
                    doi = None
                    citation_links = article.select('.gs_fl a')
                    for link in citation_links:
                        if 'citations' in link.get('href', ''):
                            citation_id = re.search(r'cites=(\d+)', link.get('href', ''))
                            if citation_id:
                                citation_id = citation_id.group(1)
                                # We'll use citation ID as a unique identifier
                                break
                    
                    # Look for PDF link
                    pdf_link = None
                    
                    # Check bottom links for PDF
                    for link in article.select('.gs_or_ggsm a, .gs_or_btn a'):
                        if '[PDF]' in link.text or 'PDF' in link.text:
                            pdf_link = link.get('href', '')
                            if pdf_link:
                                print(f"Found PDF link: {pdf_link}")
                                break
                    
                    # Generate a unique ID
                    unique_id = f"gs_{len(results)}"
                    parsed_url = urlparse(article_url)
                    if parsed_url.netloc:
                        domain = parsed_url.netloc.split('.')
                        if len(domain) > 1:
                            unique_id = f"gs_{domain[-2]}_{len(results)}"
                    
                    # Create study data
                    study = {
                        'title': title,
                        'authors': authors,
                        'journal': journal,
                        'publication_date': publication_date,
                        'abstract': abstract,
                        'source_url': article_url,
                        'pdf_link': pdf_link,
                        'doi': doi,
                        'unique_id': unique_id,
                        'database': 'Google Scholar'
                    }
                    
                    results.append(study)
                    
                    # Check if we've reached the maximum number of results
                    if max_results and len(results) >= max_results:
                        break
                        
                except Exception as e:
                    print(f"Error processing article: {e}")
                    continue
            
            # Check if there's a next page
            next_page = soup.select_one('a.gs_ico_nav_next')
            if not next_page or 'disabled' in next_page.get('class', []):
                print("No more pages available.")
                break
                
            # Move to next page
            page += 1
            
            # Add a longer delay between pages (5-10 seconds)
            time.sleep(random.uniform(5, 10))
        
        return results
        
    except requests.exceptions.RequestException as e:
        print(f"Error searching Google Scholar: {e}")
        return results

def check_pdf_availability(url, headers):
    """Check if a URL is accessible and potentially a PDF.
    
    Args:
        url (str): URL to check
        headers (dict): HTTP headers for requests
    
    Returns:
        bool, str: Success flag and potentially modified URL
    """
    try:
        # Create a fresh session
        session = requests.Session()
        retries = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Use enhanced browser-like headers
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Send request with short timeout
        response = session.get(url, headers=browser_headers, timeout=15, stream=True, allow_redirects=True)
        
        # If redirected, update the URL
        if response.url != url:
            url = response.url
            print(f"Redirected to: {url}")
        
        # Check status code
        if response.status_code != 200:
            print(f"URL returned status code: {response.status_code}")
            return False, url
        
        # Check content type for PDF
        content_type = response.headers.get('Content-Type', '').lower()
        if 'application/pdf' in content_type or 'pdf' in content_type:
            print(f"URL confirmed as PDF (Content-Type: {content_type})")
            return True, url
        
        # Check for PDF magic bytes
        try:
            first_bytes = next(response.iter_content(256), b'')[:4]
            if first_bytes == b'%PDF':
                print("URL content starts with PDF signature")
                return True, url
        except:
            pass
        
        # If it's an HTML page, check if it contains a PDF link
        if 'text/html' in content_type:
            try:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for meta refresh
                meta_refresh = soup.select_one('meta[http-equiv="refresh"]')
                if meta_refresh and meta_refresh.get('content'):
                    content = meta_refresh.get('content')
                    url_match = re.search(r'URL=([^"\'>\s]+)', content, re.IGNORECASE)
                    if url_match:
                        new_url = url_match.group(1)
                        if 'pdf' in new_url.lower():
                            full_url = urljoin(url, new_url)
                            print(f"Found meta refresh PDF link: {full_url}")
                            return check_pdf_availability(full_url, headers)
                
                # Look for PDF links
                for link in soup.select('a[href*=".pdf"], a[href*="/pdf/"]'):
                    href = link.get('href', '')
                    if href and ('pdf' in href.lower() or link.text.lower().startswith('pdf')):
                        full_url = urljoin(url, href)
                        print(f"Found potential PDF link in HTML: {full_url}")
                        return check_pdf_availability(full_url, headers)
            except Exception as e:
                print(f"Error parsing HTML for PDF links: {e}")
        
        # No PDF found
        return False, url
        
    except Exception as e:
        print(f"Error checking PDF availability: {e}")
        return False, url

def process_google_scholar_results(results, download_func, output_dir, headers, delay):
    """Process Google Scholar search results.
    
    Args:
        results (list): List of Google Scholar study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for i, study in enumerate(results):
        print(f"Processing Google Scholar study {i+1}/{len(results)}: {study.get('title')[:50]}...")
        
        # Add processed ID for PDF generation fallback
        study['processed_id'] = f"googlescholar_{study.get('unique_id')}"
        
        # First, try to use the PDF link if available
        if study.get('pdf_link'):
            print(f"Checking direct PDF link: {study.get('pdf_link')}")
            is_pdf, updated_url = check_pdf_availability(study.get('pdf_link'), headers)
            
            if is_pdf:
                study['pdf_link'] = updated_url
                print(f"Confirmed PDF link: {updated_url}")
            else:
                print(f"Direct PDF link unavailable or not a PDF")
                study['pdf_link'] = None
        
        # If no PDF link or it's invalid, try to find one from the source URL
        if not study.get('pdf_link') and study.get('source_url'):
            print(f"Looking for PDF at source URL: {study.get('source_url')}")
            is_source_pdf, updated_source_url = check_pdf_availability(study.get('source_url'), headers)
            
            if is_source_pdf:
                study['pdf_link'] = updated_source_url
                print(f"Source URL is or contains a PDF: {updated_source_url}")
            else:
                # For specific repositories, try to construct PDF URLs
                source_url = study.get('source_url')
                if 'nature.com' in source_url:
                    pdf_url = f"{source_url}.pdf"
                    print(f"Trying Nature PDF URL: {pdf_url}")
                    is_pdf, _ = check_pdf_availability(pdf_url, headers)
                    if is_pdf:
                        study['pdf_link'] = pdf_url
                elif 'ncbi.nlm.nih.gov/pmc/articles/PMC' in source_url:
                    pmc_match = re.search(r'PMC(\d+)', source_url)
                    if pmc_match:
                        pmc_id = pmc_match.group(1)
                        pdf_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/pdf/main.pdf"
                        print(f"Trying PMC PDF URL: {pdf_url}")
                        is_pdf, _ = check_pdf_availability(pdf_url, headers)
                        if is_pdf:
                            study['pdf_link'] = pdf_url
                elif any(domain in source_url for domain in ['sciencedirect.com', 'elsevier.com']):
                    pdf_url = f"{source_url}/pdfft"
                    print(f"Trying Elsevier PDF URL: {pdf_url}")
                    is_pdf, _ = check_pdf_availability(pdf_url, headers)
                    if is_pdf:
                        study['pdf_link'] = pdf_url
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            # Create a valid filename
            identifier = study.get('unique_id')
            
            pdf_path = download_func(study['pdf_link'], f"googlescholar_{identifier}", overwrite=True)
            if pdf_path:
                study['local_pdf_path'] = pdf_path
                print(f"Successfully downloaded PDF to {pdf_path}")
            else:
                print(f"Failed to download PDF - will try to create one from article content")
        else:
            print(f"No PDF link found - will try to create one from article content")
        
        processed_studies.append(study)
        
        # Add a delay to avoid overwhelming the server
        wait_time = delay * 2  # Double the normal delay for Google Scholar to avoid detection
        print(f"Waiting {wait_time} seconds before next request...")
        time.sleep(wait_time)
    
    return processed_studies
