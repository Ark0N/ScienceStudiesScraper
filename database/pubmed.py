"""
PubMed search module for NMN Study Downloader
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def search_pubmed(query, additional_terms, headers, max_results=None):
    """Search PubMed for studies related to NMN.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of PubMed IDs
    """
    base_query = query
    if additional_terms:
        base_query += " AND (" + " OR ".join(additional_terms) + ")"
    
    print(f"Searching PubMed for: {base_query}")
    
    # Encode the query for URL
    search_query = base_query.replace(' ', '+')
    url = f"https://pubmed.ncbi.nlm.nih.gov/?term={search_query}&size=100"
    
    try:
        # Create a session with retry logic for GET only
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Use GET only, no HEAD requests
        response = session.get(url, headers=headers, allow_redirects=True)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract study IDs
        study_ids = []
        for article in soup.select('.docsum-content'):
            pmid = article.find('span', class_='docsum-pmid')
            if pmid:
                study_ids.append(pmid.text.strip())
        
        return study_ids[:max_results] if max_results else study_ids
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching PubMed: {e}")
        return []

def get_study_details(pmid, headers):
    """Get details for a specific study by its PubMed ID.
    
    Args:
        pmid (str): PubMed ID of the study
        headers (dict): HTTP headers for requests
    
    Returns:
        dict: Study details
    """
    url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    
    try:
        # Create a session with retry logic for GET only
        session = requests.Session()
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
        session.mount('http://', HTTPAdapter(max_retries=retries))
        session.mount('https://', HTTPAdapter(max_retries=retries))
        
        # Use browser-like headers
        browser_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        # Use GET only, no HEAD requests
        response = session.get(url, headers=browser_headers, allow_redirects=True)
        response.raise_for_status()
        
        # Get the final URL after any redirects
        final_url = response.url
        if final_url != url:
            print(f"Redirected to: {final_url}")
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract basic information
        title = soup.select_one('.heading-title')
        title = title.text.strip() if title else "Unknown Title"
        
        authors_elem = soup.select('.authors-list .full-name')
        authors = [author.text.strip() for author in authors_elem] if authors_elem else []
        
        journal_elem = soup.select_one('.journal-actions .journal-title')
        journal = journal_elem.text.strip() if journal_elem else "Unknown Journal"
        
        date_elem = soup.select_one('.publish-date')
        pub_date = date_elem.text.strip() if date_elem else "Unknown Date"
        
        abstract_elem = soup.select_one('#abstract .abstract-content')
        abstract = abstract_elem.text.strip() if abstract_elem else "Abstract not available"
        
        # Check for PMC ID (for potential direct PDF access)
        pmc_id = None
        for id_elem in soup.select('.identifier'):
            if 'PMC' in id_elem.text:
                # Extract just the PMC ID number, removing any "PMCID:" prefix and whitespace
                pmc_match = re.search(r'PMC\s*(\d+)', id_elem.text)
                if pmc_match:
                    pmc_id = f"PMC{pmc_match.group(1)}"
                    break
                
        # Find DOI
        doi = None
        doi_elem = soup.select_one('.identifier.doi')
        if doi_elem:
            doi = doi_elem.text.strip().replace('doi: ', '')
        
        # Find PDF link using multiple approaches
        pdf_link = None
        
        # 1. If PMC ID is available, use direct PDF link construction
        if pmc_id:
            pmc_num = pmc_id.replace('PMC', '')
            pdf_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_num}/pdf/main.pdf"
            print(f"Using PMC link for PDF: {pdf_link}")
        
        # 2. Look for direct PDF links on the page if we don't have a PMC link yet
        if not pdf_link:
            for link in soup.select('a'):
                href = link.get('href', '')
                # Check for PDF links from various common sources
                if (href.endswith('.pdf') or '/pdf/' in href or 'pdf.pdf' in href or 'fulltext/pdf' in href) and (
                    '.gov' in href or '.org' in href or '.edu' in href or 'doi.org' in href or 
                    'nih.gov' in href or 'europepmc.org' in href or 'ncbi.nlm.nih.gov' in href):
                    pdf_link = urljoin(final_url, href)  # Use final URL as base
                    print(f"Found direct PDF link: {pdf_link}")
                    break
        
        # 3. Try to construct a PDF link from DOI for common repositories
        if not pdf_link and doi:
            # Try to check if this is a Nature, Science, Cell or Elsevier paper
            if any(publisher in journal.lower() for publisher in ['nature', 'science', 'cell']):
                pdf_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/{pmid}/pdf/"
                print(f"Created PDF link from journal publisher: {pdf_link}")
        
        # 4. Last resort: Try to find a free PMC version if available
        if not pdf_link:
            pmc_link_elem = soup.select_one('a.pmc-free-article')
            if pmc_link_elem:
                pmc_href = pmc_link_elem.get('href', '')
                if pmc_href:
                    # Extract PMC ID from the link
                    pmc_match = re.search(r'PMC(\d+)', pmc_href)
                    if pmc_match:
                        pmc_num = pmc_match.group(1)
                        pdf_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_num}/pdf/main.pdf"
                        print(f"Found PMC free article link: {pdf_link}")
        
        # 5. Check EuropePMC as a last resort
        if not pdf_link:
            try:
                # Check Europe PMC which often has PDFs for open access articles
                europe_pmc_url = f"https://europepmc.org/article/med/{pmid}"
                
                print(f"Checking Europe PMC for PDF: {europe_pmc_url}")
                europe_response = session.get(europe_pmc_url, headers=browser_headers, timeout=15, allow_redirects=True)
                
                if europe_response.status_code == 200:
                    europe_soup = BeautifulSoup(europe_response.text, 'html.parser')
                    
                    # First check for PDF link button
                    pdf_button = europe_soup.select_one('a.pdfLink, a.pdf-link, a[title*="PDF"]')
                    if pdf_button:
                        href = pdf_button.get('href', '')
                        if href:
                            pdf_link = urljoin(europe_response.url, href)  # Use final URL as base
                            print(f"Found PDF link from Europe PMC: {pdf_link}")
                    
                    # Also check the full text links section
                    if not pdf_link:
                        full_text_section = europe_soup.select_one('#free-full-text-links-list, .full-text-links')
                        if full_text_section:
                            for link in full_text_section.select('a'):
                                href = link.get('href', '')
                                link_text = link.text.strip().lower()
                                if href and ('pdf' in href.lower() or 'pdf' in link_text):
                                    pdf_link = urljoin(europe_response.url, href)
                                    print(f"Found PDF link in Europe PMC full text section: {pdf_link}")
                                    break
            except Exception as e:
                print(f"Error checking Europe PMC for PDF: {e}")
        
        # 6. Try DOI-based PDFs for well-known publishers
        if not pdf_link and doi:
            print(f"Checking DOI for direct PDF access: {doi}")
            try:
                doi_url = f"https://doi.org/{doi}"
                # Get the final URL from the DOI (after redirection)
                doi_response = session.get(doi_url, headers=browser_headers, allow_redirects=True, timeout=20)
                if doi_response.status_code == 200:
                    publisher_url = doi_response.url
                    print(f"DOI redirected to: {publisher_url}")
                    
                    # Try common publisher PDF patterns
                    if 'nature.com' in publisher_url:
                        pdf_link = f"{publisher_url}.pdf"
                    elif 'science.org' in publisher_url or 'sciencemag.org' in publisher_url:
                        pdf_link = f"{publisher_url}/pdf"
                    elif 'cell.com' in publisher_url or 'sciencedirect.com' in publisher_url:
                        pdf_link = f"{publisher_url}/pdfft"
                    elif any(x in publisher_url for x in ['wiley.com', 'springer.com', 'mdpi.com', 'frontiersin.org']):
                        pdf_link = f"{publisher_url}/pdf"
                        
                    if pdf_link:
                        print(f"Created PDF link from publisher URL: {pdf_link}")
            except Exception as e:
                print(f"Error checking DOI for PDF: {e}")
        
        return {
            'pmid': pmid,
            'title': title,
            'authors': authors,
            'journal': journal,
            'publication_date': pub_date,
            'abstract': abstract,
            'pdf_link': pdf_link,
            'doi': doi,
            'pmc_id': pmc_id,
            'source_url': final_url,  # Use final URL after redirects
            'database': 'PubMed'
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error getting details for study {pmid}: {e}")
        return None

def process_pubmed_results(pmids, download_func, output_dir, headers, delay):
    """Process PubMed search results.
    
    Args:
        pmids (list): List of PubMed IDs
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for i, pmid in enumerate(pmids):
        print(f"Processing PubMed study {pmid}... ({i+1}/{len(pmids)})")
        study_data = get_study_details(pmid, headers)
        
        if study_data:
            # Try to download PDF if available
            if study_data.get('pdf_link'):
                # Create a browser-like headers with referer
                browser_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': study_data.get('source_url', 'https://pubmed.ncbi.nlm.nih.gov/'),
                }
                
                pdf_path = download_func(study_data['pdf_link'], f"pubmed_{pmid}", overwrite=True)
                study_data['local_pdf_path'] = pdf_path
            
            processed_studies.append(study_data)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
