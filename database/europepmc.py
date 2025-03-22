"""
Europe PMC search module for NMN Study Downloader
"""

import time
import requests
import urllib.parse
import re
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import random

def search_europepmc(query, additional_terms, headers, max_results=None):
    """Search Europe PMC for studies related to NMN.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of study metadata
    """
    base_query = query
    
    # Fix for the URL query parameter issue
    if additional_terms:
        # Prepare a simpler set of terms to avoid hitting URL length limits
        simplified_terms = ["NAD", "aging", "longevity", "human"]
        base_query = f"{query} {' '.join(simplified_terms)}"
    
    print(f"Searching Europe PMC for: {base_query}")
    
    # Create a safer query string
    search_query = urllib.parse.quote(base_query)
    
    # Use a fixed numeric value for pageSize
    page_size = 100 if max_results is None or max_results > 100 else max_results
    url = f"https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={search_query}&format=json&resultType=core&pageSize={page_size}"
    
    try:
        # Create a session with retry capabilities
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        if 'resultList' in data and 'result' in data['resultList']:
            for item in data['resultList']['result']:
                # Extract source and ID for URL construction
                source = item.get('source', 'MED')
                item_id = item.get('id', '')
                
                # Construct source URL
                source_url = f"https://europepmc.org/article/{source.lower()}/{item_id}"
                
                # Generate a unique identifier that we'll use for filenames
                unique_id = item.get('pmid', item.get('id', ''))
                if not unique_id and item.get('doi'):
                    # Use DOI if we don't have PMID or ID
                    unique_id = item.get('doi').replace('/', '_')
                
                # Ensure unique_id is not empty
                if not unique_id:
                    unique_id = f"europmc_{len(results)}"
                
                study = {
                    'pmid': item.get('pmid', ''),
                    'pmcid': item.get('pmcid', ''),
                    'doi': item.get('doi', ''),
                    'unique_id': unique_id,  # Add a unique ID field for referencing
                    'title': item.get('title', 'Unknown Title'),
                    'authors': [author.get('fullName', '') for author in item.get('authorList', {}).get('author', [])],
                    'journal': item.get('journalTitle', 'Unknown Journal'),
                    'publication_date': item.get('firstPublicationDate', 'Unknown Date'),
                    'abstract': item.get('abstractText', 'Abstract not available'),
                    'source_url': source_url,
                    'source_type': source.lower(),  # Store the source type (med, ppr, etc.)
                    'database': 'Europe PMC'
                }
                
                # We'll determine PDF links in the processing function
                study['pdf_link'] = None
                
                results.append(study)
                
                if max_results is not None and len(results) >= max_results:
                    break
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching Europe PMC: {e}")
        return []

def find_pdf_link_on_europepmc(url, study, headers):
    """Find PDF download link from Europe PMC article page.
    
    Args:
        url (str): URL of the Europe PMC article
        study (dict): Study metadata dict
        headers (dict): HTTP headers for requests
    
    Returns:
        str: PDF download link or None if not found
    """
    try:
        print(f"Checking Europe PMC article page for PDF links: {url}")
        
        # Create a session with retry capabilities
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Use browser-like headers
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache'
        }
        
        # Follow redirects
        response = session.get(url, headers=browser_headers, timeout=30, allow_redirects=True)
        final_url = response.url  # Get the final URL after any redirects
        
        if response.status_code != 200:
            print(f"Failed to access Europe PMC article page: {response.status_code}")
            return None
            
        # Track if we've been redirected
        if final_url != url:
            print(f"Redirected to: {final_url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 1. Check for PDF links in the full text links section (most common location)
        full_text_section = soup.select_one('#free-full-text-links-list, .full-text-links, .supplementary-materials, .ftl')
        if full_text_section:
            print("Found Full Text Links section")
            pdf_links = full_text_section.select('a')
            for link in pdf_links:
                link_text = link.text.strip().lower()
                href = link.get('href', '')
                if href and ('pdf' in href.lower() or 'fulltext' in href.lower() or 
                           'pdf' in link_text or 'full text' in link_text):
                    full_link = urllib.parse.urljoin(final_url, href)  # Use the final URL as the base
                    print(f"Found PDF link in Full Text Links section: {full_link}")
                    return full_link
        
        # 2. Look for PDF buttons/icons on the page
        pdf_buttons = soup.select('a.icon.pdf, a.icon.download-pdf, a.pdf-link, .article-download-links-list a, a.pdf-button')
        for button in pdf_buttons:
            href = button.get('href', '')
            if href:
                full_link = urllib.parse.urljoin(final_url, href)  # Use the final URL as the base
                print(f"Found PDF button/icon: {full_link}")
                return full_link
        
        # 3. Look for "PDF" text in links
        for link in soup.select('a'):
            link_text = link.text.strip().lower()
            if 'pdf' in link_text:
                href = link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)  # Use the final URL as the base
                    print(f"Found link with PDF text: {full_link}")
                    return full_link
        
        # 4. Check for PMC ID in page and construct direct PDF link
        pmc_id_match = re.search(r'PMC(\d+)', response.text)
        if pmc_id_match:
            pmc_num = pmc_id_match.group(1)
            pmc_pdf = f"https://europepmc.org/articles/PMC{pmc_num}/pdf/main.pdf"
            print(f"Constructed PMC PDF link from page content: {pmc_pdf}")
            return pmc_pdf
        
        print("No PDF links found on Europe PMC page")
        return None
        
    except Exception as e:
        print(f"Error examining Europe PMC page: {e}")
        return None

def get_pdf_from_doi_site(doi, headers):
    """Get PDF link by following the DOI to the source website.
    
    Args:
        doi (str): DOI of the article
        headers (dict): HTTP headers for requests
    
    Returns:
        str: PDF download link or None if not found
    """
    if not doi:
        return None
    
    # Special handling for preprints.org DOIs
    if 'preprints' in doi:
        print(f"Special direct handling for preprints.org DOI: {doi}")
        
        # Extract manuscript info from DOI
        match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
        if match:
            year_month = match.group(1)
            number = match.group(2)
            version = match.group(3) if match.group(3) else "1"
            
            # Construct direct URL
            manuscript_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}"
            download_url = f"{manuscript_url}/download"
            
            print(f"Constructed direct preprints.org download URL: {download_url}")
            return download_url
    
    doi_url = f"https://doi.org/{doi}"
    print(f"Following DOI link: {doi_url}")
    
    try:
        # Create a session with retry capabilities and cookies support
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Use a browser-like user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        ]
        
        browser_headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1'
        }
        
        # First request - follow the DOI with redirects enabled
        # Use a longer timeout for DOI redirects as they can be slow
        print(f"Sending request to DOI URL with redirect handling...")
        
        # Standard DOI handling for non-preprints.org DOIs
        response = session.get(doi_url, headers=browser_headers, allow_redirects=True, timeout=30)
        
        if response.status_code != 200:
            print(f"Failed to follow DOI link: {response.status_code}")
            # For preprints.org DOIs, still try our constructed URL
            if 'preprints' in doi:
                match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
                if match:
                    year_month = match.group(1)
                    number = match.group(2)
                    version = match.group(3) if match.group(3) else "1"
                    preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                    print(f"Using direct preprints.org URL despite DOI failure: {preprint_url}")
                    return preprint_url
            return None
            
        # Now we're on the actual publication site
        final_url = response.url
        print(f"DOI redirected to final URL: {final_url}")
        
        # Parse the page content
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Site-specific handlers for common publishers
        # Preprints.org
        if 'preprints.org' in final_url:
            print("Detected preprints.org site")
            download_links = soup.select('a.btn-download, a.downloadButton, a[data-target="#downloadPDFModal"], a[title="Download"]')
            for link in download_links:
                if 'Download' in link.text or 'PDF' in link.text:
                    href = link.get('href', '')
                    if href:
                        full_link = urllib.parse.urljoin(final_url, href)
                        print(f"Found preprints.org download link: {full_link}")
                        return full_link
            
            # Try to construct the download URL for preprints.org
            if '/manuscript/' in final_url:
                pattern = r'/manuscript/(\d+\.\d+)/v(\d+)'
                match = re.search(pattern, final_url)
                if match:
                    id_part = match.group(1)
                    version = match.group(2)
                    preprint_url = f"https://www.preprints.org/manuscript/{id_part}/v{version}/download"
                    print(f"Constructed preprints.org download URL: {preprint_url}")
                    return preprint_url
        
        # BioRxiv/MedRxiv
        elif 'biorxiv.org' in final_url or 'medrxiv.org' in final_url:
            print("Detected bioRxiv/medRxiv site")
            pdf_link = soup.select_one('a.article-dl-pdf-link, a[title="Download PDF"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found bioRxiv/medRxiv download link: {full_link}")
                    return full_link
        
        # Nature
        elif 'nature.com' in final_url:
            print("Detected Nature site")
            pdf_link = soup.select_one('a.c-pdf-download__link, a[data-track-action="download pdf"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found Nature download link: {full_link}")
                    return full_link
        
        # Science
        elif 'science.org' in final_url or 'sciencemag.org' in final_url:
            print("Detected Science site")
            pdf_link = soup.select_one('a.article-dl-pdf-link, a[data-toggle="tooltip"][title="Download PDF"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found Science download link: {full_link}")
                    return full_link
        
        # Cell/Elsevier
        elif 'cell.com' in final_url or 'sciencedirect.com' in final_url:
            print("Detected Cell/Elsevier site")
            pdf_link = soup.select_one('a.pdf-download-btn-link, a.download-link[href*="pdf"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found Cell/Elsevier download link: {full_link}")
                    return full_link
        
        # MDPI
        elif 'mdpi.com' in final_url:
            print("Detected MDPI site")
            pdf_link = soup.select_one('a.download-files-pdf, a[href*="pdf"][title="Download PDF"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found MDPI download link: {full_link}")
                    return full_link
        
        # Frontiers
        elif 'frontiersin.org' in final_url:
            print("Detected Frontiers site")
            pdf_link = soup.select_one('a.download-files-pdf, a.pdf-link')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found Frontiers download link: {full_link}")
                    return full_link
        
        # PLoS
        elif 'plos' in final_url:
            print("Detected PLOS site")
            pdf_link = soup.select_one('a.pdfDownload, a[data-doi][href*="pdf"]')
            if pdf_link:
                href = pdf_link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found PLOS download link: {full_link}")
                    return full_link
        
        print("Using generic PDF detection for publisher site")
        
        # Generic approach - look for common PDF download patterns
        # 1. Look for buttons with "PDF" or "Download" text
        print("Looking for download buttons with PDF text...")
        download_links = soup.select('a.btn, a.button, a.download, button.download, a.pdf-button, a.download-button, a[title*="PDF"], a[title*="Download"]')
        for link in download_links:
            link_text = link.text.strip().lower()
            if ('pdf' in link_text and 'download' in link_text) or 'download pdf' in link_text or 'pdf' in link_text:
                href = link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found generic download button: {full_link}")
                    return full_link
        
        # 2. Look for any link with "PDF" in href
        print("Looking for links with PDF in the URL...")
        pdf_links = soup.select('a[href*="pdf"], a[href*=".pdf"]')
        for link in pdf_links:
            href = link.get('href', '')
            link_text = link.text.strip().lower()
            if href and ('download' in link_text or 'full text' in link_text or 'pdf' in link_text):
                full_link = urllib.parse.urljoin(final_url, href)
                print(f"Found link with PDF in href: {full_link}")
                return full_link
        
        # 3. Look for any link with "PDF" in the text
        print("Looking for links with PDF in the text...")
        for link in soup.select('a'):
            link_text = link.text.strip().lower()
            if ('pdf' in link_text and 'download' in link_text) or 'full text pdf' in link_text:
                href = link.get('href', '')
                if href:
                    full_link = urllib.parse.urljoin(final_url, href)
                    print(f"Found link with PDF text: {full_link}")
                    return full_link
        
        print(f"No PDF download link found on {final_url}")
        
        # For preprints.org, always return a direct download URL as last resort
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else "1"
                preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Using preprints.org download URL as last resort: {preprint_url}")
                return preprint_url
                
        return None
    
    except requests.exceptions.Timeout as e:
        print(f"Timeout following DOI link: {e}")
        # For preprints.org, return direct URL even on timeout
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else "1"
                preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Using preprints.org URL after timeout: {preprint_url}")
                return preprint_url
        return None
    except requests.exceptions.TooManyRedirects as e:
        print(f"Too many redirects following DOI link: {e}")
        # Return direct URL for preprints
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else "1"
                preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Using preprints.org URL after redirect problem: {preprint_url}")
                return preprint_url
        return None
    except requests.exceptions.RequestException as e:
        print(f"Request error following DOI link: {e}")
        # Return direct URL for preprints
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else "1"
                preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Using preprints.org URL after request error: {preprint_url}")
                return preprint_url
        return None
    except Exception as e:
        print(f"Unexpected error following DOI link: {e}")
        # Return direct URL for preprints
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else "1"
                preprint_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Using preprints.org URL after unexpected error: {preprint_url}")
                return preprint_url
        return None

def find_pdf_from_original_source(study, headers):
    """Try to find PDF from the original source using available IDs.
    
    Args:
        study (dict): Study metadata
        headers (dict): HTTP headers for requests
    
    Returns:
        str: PDF download link or None if not found
    """
    # 1. Try DOI-based approach (most reliable for finding original source)
    if study.get('doi'):
        print(f"Looking for PDF on original source via DOI: {study.get('doi')}")
        pdf_link = get_pdf_from_doi_site(study.get('doi'), headers)
        if pdf_link:
            return pdf_link
    
    # 2. Try PMC-based approach (for open access articles)
    if study.get('pmcid'):
        pmc_id = study.get('pmcid')
        pmc_match = re.search(r'(?:PMC)?(\d+)', pmc_id)
        if pmc_match:
            pmc_num = pmc_match.group(1)
            pmc_pdf = f"https://europepmc.org/articles/PMC{pmc_num}/pdf/main.pdf"
            print(f"Created PDF link from PMCID: {pmc_pdf}")
            return pmc_pdf
    
    # 3. Try PMID-based approach (fallback to PubMed Central)
    if study.get('pmid'):
        pmid = study.get('pmid')
        pmid_pdf = f"https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/{pmid}/pdf/"
        print(f"Created PDF link from PMID (PMC fallback): {pmid_pdf}")
        return pmid_pdf
    
    # 4. For preprints, try known repositories
    if study.get('source_type') == 'ppr' and study.get('doi'):
        doi = study.get('doi')
        
        # Handle preprints.org
        if 'preprints' in doi:
            match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
            if match:
                year_month = match.group(1)
                number = match.group(2)
                version = match.group(3) if match.group(3) else '1'
                preprint_pdf = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}/download"
                print(f"Created preprints.org PDF link: {preprint_pdf}")
                return preprint_pdf
                
        # Handle bioRxiv/medRxiv
        elif 'biorxiv' in doi or 'medrxiv' in doi:
            match = re.search(r'10\.1101/(\d+\.\d+\.\d+\.\d+)', doi)
            if match:
                paper_id = match.group(1)
                biorxiv_pdf = f"https://www.biorxiv.org/content/10.1101/{paper_id}.full.pdf"
                print(f"Created bioRxiv/medRxiv PDF link: {biorxiv_pdf}")
                return biorxiv_pdf
    
    return None

def process_europepmc_results(results, download_func, output_dir, headers, delay):
    """Process Europe PMC search results.
    
    Args:
        results (list): List of Europe PMC study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5'
    }
    
    for i, study in enumerate(results):
        # Use the unique_id for display and file naming
        identifier = study.get('unique_id', f"europmc_{i}")
        print(f"Processing Europe PMC study: {identifier}... ({i+1}/{len(results)})")
        
        # Store original identifier for debugging
        pmid_text = f"europmc_{identifier}" if isinstance(identifier, str) else f"europmc_{i}"
        study['processed_id'] = pmid_text  # Save this for PDF creation
        
        # Use a multi-strategy approach to find PDFs
        pdf_link = None
        
        # Special handling for preprints
        if study.get('source_type') == 'ppr' and study.get('doi'):
            print(f"Special handling for preprint with DOI: {study.get('doi')}")
            # For preprints, go directly to original source via DOI
            pdf_link = get_pdf_from_doi_site(study.get('doi'), browser_headers)
            if pdf_link:
                print(f"Found preprint PDF link from DOI: {pdf_link}")
                study['pdf_link'] = pdf_link
                
                # Sanitize identifier for filename
                safe_identifier = re.sub(r'[^\w\-.]', '_', identifier)
                
                # Try to download with special handling (downloader.py will handle preprints.org differently)
                print(f"Attempting to download preprint PDF")
                pdf_path = download_func(pdf_link, pmid_text, overwrite=True)
                
                if pdf_path:
                    study['local_pdf_path'] = pdf_path
                    print(f"Successfully downloaded preprint PDF to {pdf_path}")
                else:
                    print(f"Failed to download preprint PDF - will create one from article content")
                
                processed_studies.append(study)
                time.sleep(delay)
                continue
        
        # Regular handling for non-preprints
        # Strategy 1: Check Europe PMC page first
        if study.get('source_url'):
            pdf_link = find_pdf_link_on_europepmc(study['source_url'], study, browser_headers)
            if pdf_link:
                print(f"Found PDF link on Europe PMC page: {pdf_link}")
        
        # Strategy 2: If no PDF found on EuropePMC, try original source
        if not pdf_link:
            pdf_link = find_pdf_from_original_source(study, browser_headers)
            if pdf_link:
                print(f"Found PDF link from original source: {pdf_link}")
        
        # Set the PDF link in the study data
        study['pdf_link'] = pdf_link
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            # Sanitize identifier for filename
            safe_identifier = re.sub(r'[^\w\-.]', '_', identifier)
            
            print(f"Attempting to download PDF from: {study['pdf_link']}")
            pdf_path = download_func(study['pdf_link'], pmid_text, overwrite=True)
            
            if pdf_path:
                study['local_pdf_path'] = pdf_path
                print(f"Successfully downloaded PDF to {pdf_path}")
            else:
                print(f"Failed to download PDF - will create one from article content")
        else:
            print(f"No PDF link found - will create one from article content")
        
        processed_studies.append(study)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
