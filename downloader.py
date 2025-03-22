#!/usr/bin/env python3
"""
Core downloader class for Science Study Scraper.
"""

import os
import time
import json
import pandas as pd
from datetime import datetime
import requests
import importlib
import random
import urllib.parse
import re
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter

from utils.pdf_generator import extract_article_content, generate_pdf_from_content
from utils.html_report import generate_html_report


class ScienceStudyScraper:
    def __init__(self, output_dir="studies", max_results=None, delay=1):
        """Initialize the Science Study Scraper.
        
        Args:
            output_dir (str): Directory to save downloaded studies
            max_results (int): Maximum number of results to retrieve (None for unlimited)
            delay (int): Delay between requests to avoid rate limiting
        """
        self.output_dir = output_dir
        self.max_results = max_results  # None means unlimited
        self.delay = delay
        self.studies_data = []
        
        # Create output directory if it doesn't exist
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        
        pdf_dir = os.path.join(output_dir, "pdfs")
        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir)
        
        # Path for saved queries
        self.query_file = os.path.join(output_dir, "saved_query.json")
        
        # Headers to mimic a browser - use a randomized modern user agent
        user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:95.0) Gecko/20100101 Firefox/95.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.1 Safari/605.1.15',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36'
        ]
        
        self.headers = {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'DNT': '1',  # Do Not Track request header
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Create a session with retries for better download reliability
        # IMPORTANT: ONLY ALLOW GET REQUESTS, NO HEAD REQUESTS
        self.session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504, 429],
            allowed_methods=["GET"]  # ONLY GET, NO HEAD
        )
        self.session.mount('http://', HTTPAdapter(max_retries=retries))
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
    
        # Monkey patch requests to only use GET and never HEAD
        original_request = requests.Session.request
        def patched_request(session_self, method, url, **kwargs):
            if method.upper() == 'HEAD':
                print(f"HEAD request to {url} intercepted and converted to GET")
                method = 'GET'
                if 'allow_redirects' not in kwargs:
                    kwargs['allow_redirects'] = True
            return original_request(session_self, method, url, **kwargs)
        
        requests.Session.request = patched_request
        
        # Track where each study came from
        self.sources = {
            'pubmed': 0,
            'pmc': 0,
            'europepmc': 0,
            'biorxiv': 0,
            'doaj': 0,
            'sciencedirect': 0,
            'semanticscholar': 0,
            'googlescholar': 0
        }
    
    def save_query(self, query, terms=None):
        """Save the current query for future use.
        
        Args:
            query (str): The main search query
            terms (list): Additional search terms
        """
        query_data = {
            'query': query,
            'terms': terms if terms else []
        }
        
        with open(self.query_file, 'w', encoding='utf-8') as f:
            json.dump(query_data, f, ensure_ascii=False, indent=4)
    
    def load_saved_query(self):
        """Load the saved query if available.
        
        Returns:
            dict: The saved query and terms, or None if not found
        """
        if os.path.exists(self.query_file):
            with open(self.query_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def download_pdf(self, url, pmid, overwrite=True):
        """Download PDF for a study if available.
        
        Args:
            url (str): URL of the PDF
            pmid (str): PubMed ID to use for filename
            overwrite (bool): Whether to overwrite existing files
        
        Returns:
            str: Path to downloaded file or None if failed
        """
        if not url:
            return None
        
        try:
            filename = os.path.join(self.output_dir, "pdfs", f"{pmid}.pdf")
            
            # Check if file exists and we're not overwriting
            if os.path.exists(filename) and not overwrite:
                print(f"File already exists for study {pmid} (skipping download)")
                return filename
            
            print(f"Attempting to download PDF from: {url}")
            
            # Special handling for preprints.org and preprints DOIs
            if 'preprints.org' in url or 'preprints' in url:
                print("Detected preprints.org URL - using special handler")
                return self._download_from_preprints(url, pmid, filename)
            
            # Try different headers variations for better compatibility with various repositories
            headers_variations = [
                self.headers,
                {**self.headers, 'Accept': 'application/pdf'},
                {**self.headers, 'Accept': '*/*'},
                # More browser-like headers for academic sites
                {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'Accept': 'application/pdf,application/x-pdf,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.5',
                    'Referer': urllib.parse.urljoin(url, '/'),  # Set referer to the base domain
                    'Connection': 'keep-alive'
                }
            ]
            
            # Initialize response to None
            response = None
            
            # DIRECT GET REQUESTS ONLY
            for headers in headers_variations:
                try:
                    # ONLY USE GET WITH REDIRECTS - NO HEAD REQUESTS
                    response = requests.get(
                        url, 
                        headers=headers, 
                        stream=True, 
                        timeout=30,
                        allow_redirects=True
                    )
                    
                    if response.status_code == 200:
                        print(f"Successfully connected to PDF URL (status: 200)")
                        break
                    else:
                        print(f"GET request failed with status {response.status_code}, trying another header variation")
                except Exception as e:
                    print(f"Error with header variation: {e}")
                    continue
            
            if not response or response.status_code != 200:
                print(f"Failed to download PDF from {url} (status code: {response.status_code if response else 'None'})")
                return self._try_create_pdf_from_article(pmid)
            
            # Check if it's actually a PDF
            content_type = response.headers.get('Content-Type', '').lower()
            
            # We need to read a small chunk to check the content
            try:
                if response.raw.chunked:
                    # For chunked responses, read the first chunk
                    first_chunk = next(response.iter_content(chunk_size=256), b'')
                    first_bytes = first_chunk[:10]
                    # Reset the stream for later download
                    response = requests.get(
                        url, 
                        headers=headers, 
                        stream=True, 
                        timeout=30,
                        allow_redirects=True
                    )
                else:
                    # For non-chunked, we can peek at the content
                    first_bytes = response.content[:10] if hasattr(response, 'content') else b''
            except Exception as e:
                print(f"Error checking content: {e}")
                first_bytes = b''
            
            is_pdf = False
            
            # Check content-type header
            if 'application/pdf' in content_type or 'pdf' in content_type:
                is_pdf = True
                print(f"Content-Type indicates PDF: {content_type}")
            # Check first bytes for PDF signature
            elif first_bytes and first_bytes.startswith(b'%PDF'):
                is_pdf = True
                print(f"Content starts with %PDF signature")
            # If streaming and we can't check first bytes yet
            elif response.raw.chunked or not first_bytes:
                # Just accept it based on URL ending with .pdf
                if url.lower().endswith('.pdf') or '/pdf/' in url.lower():
                    is_pdf = True
                    print(f"Assuming PDF based on URL pattern")
            
            if not is_pdf:
                print(f"Warning: Content at {url} does not appear to be a PDF (content-type: {content_type})")
                
                # Try fallback to PMC if this is a PubMed ID
                if 'pubmed' in pmid.lower() and not 'pmc' in url.lower():
                    # Extract the numeric PMID
                    numeric_pmid = ''.join(filter(str.isdigit, pmid))
                    if numeric_pmid:
                        fallback_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/pmid/{numeric_pmid}/pdf/"
                        print(f"Trying PMC fallback URL: {fallback_url}")
                        return self.download_pdf(fallback_url, pmid, overwrite)
                
                # If it's an HTML page, try to extract PDF link from it
                if 'text/html' in content_type:
                    from bs4 import BeautifulSoup
                    try:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        # Look for PDF links - common patterns
                        pdf_link = None
                        for a in soup.find_all('a'):
                            href = a.get('href', '')
                            if href.lower().endswith('.pdf') or '/pdf/' in href.lower():
                                pdf_link = urllib.parse.urljoin(url, href)
                                print(f"Found PDF link in HTML page: {pdf_link}")
                                return self.download_pdf(pdf_link, pmid, overwrite)
                    except Exception as e:
                        print(f"Error parsing HTML for PDF links: {e}")
                
                return self._try_create_pdf_from_article(pmid)
            
            # Download the PDF
            with open(filename, 'wb') as f:
                chunk_size = 8192
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # Filter out keep-alive new chunks
                        f.write(chunk)
            
            # Verify the file is a valid PDF
            if os.path.exists(filename):
                file_size = os.path.getsize(filename)
                
                if file_size < 1000:  # If the file is too small, it might not be a valid PDF
                    with open(filename, 'rb') as f:
                        first_bytes = f.read(10)
                        if not first_bytes.startswith(b'%PDF'):
                            print(f"Warning: Downloaded file does not appear to be a valid PDF (size: {file_size} bytes)")
                            os.remove(filename)  # Delete the invalid file
                            return self._try_create_pdf_from_article(pmid)
                        else:
                            print(f"Downloaded small but valid PDF ({file_size} bytes)")
                
                print(f"Successfully downloaded PDF for study {pmid}")
                return filename
            else:
                print(f"Error: PDF file {filename} not created despite successful download")
                return self._try_create_pdf_from_article(pmid)
        
        except requests.exceptions.RequestException as e:
            print(f"Request error downloading PDF for study {pmid}: {e}")
            return self._try_create_pdf_from_article(pmid)
        except Exception as e:
            print(f"Unexpected error downloading PDF for study {pmid}: {e}")
            return self._try_create_pdf_from_article(pmid)

    def _download_from_preprints(self, url, pmid, filename):
        """Special handling for downloading from preprints.org which has stricter bot detection.
        
        Args:
            url (str): URL of the PDF on preprints.org
            pmid (str): ID to use for the filename
            filename (str): Path to save the PDF
            
        Returns:
            str: Path to downloaded file or None if failed
        """
        print(f"Using special handling for preprints.org")
        
        try:
            # Handle both URL formats and DOI formats
            manuscript_id = None
            version = None
            
            # Extract manuscript ID and version from URL
            match = re.search(r'/manuscript/(\d+\.\d+)/v(\d+)/?', url)
            if match:
                manuscript_id = match.group(1)
                version = match.group(2)
            else:
                # Try DOI format
                match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', url)
                if match:
                    manuscript_id = f"{match.group(1)}.{match.group(2)}"
                    version = match.group(3) if match.group(3) else "1"
                    
            if not manuscript_id:
                print(f"Could not parse preprints.org URL format: {url}")
                return None
                    
            # Construct the manuscript page URL
            manuscript_url = f"https://www.preprints.org/manuscript/{manuscript_id}/v{version}"
            print(f"Using manuscript URL: {manuscript_url}")
            
            # Create a completely fresh session for this
            session = requests.Session()
            
            # Use full browser-like headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Cache-Control': 'max-age=0'
            }
            
            # First visit the manuscript page to get cookies
            response = session.get(manuscript_url, headers=headers, timeout=30)
            if response.status_code != 200:
                print(f"Failed to access manuscript page: {response.status_code}")
                return None
                    
            print(f"Successfully visited manuscript page, looking for download button")
            
            # Parse the page to find the actual download button
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for download button
            download_button = None
            for button in soup.select('a.btn, a.button, a.download-button, a[data-target="#downloadPDFModal"]'):
                if 'download' in button.text.lower() or 'pdf' in button.text.lower():
                    download_button = button
                    break
                        
            # If we found a download button with a different URL, use that
            download_url = None
            if download_button and download_button.get('href'):
                href = download_button.get('href', '')
                if href and href != '#':
                    download_url = urllib.parse.urljoin(manuscript_url, href)
                    print(f"Found actual download button URL: {download_url}")
            
            # If no button found, use standard download URL
            if not download_url:
                download_url = f"{manuscript_url}/download"
                print(f"Using standard download URL: {download_url}")
            
            # Now try the download with the same session
            # Update headers for PDF download
            headers.update({
                'Accept': 'application/pdf,application/x-pdf',
                'Referer': manuscript_url
            })
            
            print(f"Sending request to download PDF: {download_url}")
            pdf_response = session.get(download_url, headers=headers, stream=True, timeout=30)
            
            if pdf_response.status_code != 200:
                print(f"Failed to download PDF: {pdf_response.status_code}")
                # Try alternative URL format
                alt_url = f"{manuscript_url}/download/file"
                print(f"Trying alternative URL: {alt_url}")
                pdf_response = session.get(alt_url, headers=headers, stream=True, timeout=30)
                
                if pdf_response.status_code != 200:
                    print(f"Failed to download PDF with alternative URL: {pdf_response.status_code}")
                    return None
            
            # Save the PDF
            with open(filename, 'wb') as f:
                for chunk in pdf_response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            if os.path.exists(filename) and os.path.getsize(filename) > 1000:
                print(f"Successfully downloaded PDF from preprints.org")
                return filename
            else:
                print(f"Downloaded file is too small or invalid")
                if os.path.exists(filename):
                    os.remove(filename)
                return None
                    
        except Exception as e:
            print(f"Error downloading from preprints.org: {e}")
            return None
    
    def _try_create_pdf_from_article(self, pmid):
        """Try to create a PDF from article content.
        
        Args:
            pmid (str): PubMed ID or identifier
        
        Returns:
            str: Path to generated PDF or None if failed
        """
        print(f"Attempting to create PDF from article content for {pmid}")
        
        try:
            # First, find the study data - more robust matching
            study_data = None
            pmid_str = str(pmid)
            
            # Look for exact matches first
            for study in self.studies_data:
                if (str(study.get('pmid', '')) == pmid_str or 
                    str(study.get('unique_id', '')) == pmid_str or
                    str(study.get('processed_id', '')) == pmid_str):
                    study_data = study
                    print(f"Found study data using exact match for {pmid}")
                    break
            
            # If no match found, try partial match - important for file path IDs
            if not study_data:
                for study in self.studies_data:
                    if (pmid_str in str(study.get('processed_id', '')) or
                        pmid_str in str(study.get('unique_id', '')) or 
                        pmid_str in str(study.get('pmid', '')) or
                        (study.get('source_type') == 'ppr' and pmid_str.endswith(study.get('unique_id', '')))):
                        study_data = study
                        print(f"Found study data using partial match for {pmid}")
                        break
            
            # Try extracting unique identifier from filename
            if not study_data and pmid_str.startswith("europmc_"):
                base_id = pmid_str.replace("europmc_", "")
                for study in self.studies_data:
                    if str(study.get('unique_id', '')) == base_id or base_id in str(study.get('unique_id', '')):
                        study_data = study
                        print(f"Found study data by extracted base ID: {base_id}")
                        break
                    elif study.get('source_type') == 'ppr' and base_id in str(study.get('unique_id', '')):
                        study_data = study
                        print(f"Found preprint study data by ID: {base_id}")
                        break
            
            if not study_data:
                print(f"Could not find study data for {pmid}")
                # Print available IDs for debugging
                print("Available study IDs:")
                for study in self.studies_data:
                    print(f"  - PMID: {study.get('pmid', 'None')}, Unique ID: {study.get('unique_id', 'None')}, Processed ID: {study.get('processed_id', 'None')}")
                return None
            
            # Determine the best URL to extract content from
            extraction_url = study_data.get('source_url')
            
            # Check if we have a PMC ID - PMC is better for full text
            if study_data.get('pmc_id'):
                pmc_id = study_data['pmc_id'].replace('PMC', '')
                extraction_url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmc_id}/"
            
            # Also try Europe PMC if we have a PMID
            europe_pmc_url = None
            if 'pmid' in study_data:
                numeric_pmid = ''.join(filter(str.isdigit, str(study_data.get('pmid', ''))))
                if numeric_pmid:
                    europe_pmc_url = f"https://europepmc.org/article/med/{numeric_pmid}"
            
            # Special handling for preprints
            if study_data.get('source_type') == 'ppr' and study_data.get('doi'):
                print(f"Special extraction for preprint with DOI: {study_data.get('doi')}")
                doi = study_data.get('doi')
                
                # For preprints.org, construct direct URL to manuscript
                if 'preprints' in doi:
                    match = re.search(r'preprints(\d+)\.(\d+)(?:\.v(\d+))?', doi)
                    if match:
                        year_month = match.group(1)
                        number = match.group(2)
                        version = match.group(3) if match.group(3) else "1"
                        extraction_url = f"https://www.preprints.org/manuscript/{year_month}.{number}/v{version}"
                        print(f"Using direct preprints.org URL for content extraction: {extraction_url}")
            
            # Check if we have a DOI - some repositories have good content extraction with DOI
            doi_url = None
            if study_data.get('doi'):
                doi = study_data['doi']
                doi_url = f"https://doi.org/{doi}"
            
            # Extract content from the article
            article_content = None
            if extraction_url:
                article_content = extract_article_content(extraction_url, study_data, self.headers)
            
            # If that failed and we have an alternative URL, try that
            if (not article_content or len(article_content.get('sections', [])) <= 1) and europe_pmc_url:
                print(f"Trying alternative source: {europe_pmc_url}")
                article_content = extract_article_content(europe_pmc_url, study_data, self.headers)
            
            # If Europe PMC failed and we have a DOI, try the DOI link
            if (not article_content or len(article_content.get('sections', [])) <= 1) and doi_url:
                print(f"Trying DOI source: {doi_url}")
                article_content = extract_article_content(doi_url, study_data, self.headers)
            
            # Generate PDF if we have content
            if article_content and article_content.get('sections', []):
                pdf_filename = os.path.join(self.output_dir, "pdfs", f"{pmid}.pdf")
                return generate_pdf_from_content(article_content, pdf_filename)
            else:
                print(f"Could not extract sufficient content for {pmid}")
                return None
                    
        except Exception as e:
            print(f"Error creating PDF from article content: {e}")
            return None
    
    def run(self, query, additional_terms=None, databases=None, test_mode=False):
        """Execute the full workflow: search, get details, and download PDFs.
        
        Args:
            query (str): Main search query
            additional_terms (list): Additional search terms to refine results
            databases (list): List of databases to search (default: all)
            test_mode (bool): If True, only download one study per database
        
        Returns:
            DataFrame: Results as a pandas DataFrame
        """
        # Default additional terms if none provided
        if additional_terms is None:
            additional_terms = [
                "clinical trial", "human study", "systematic review", 
                "meta-analysis", "randomized controlled trial"
            ]
        
        # Default databases if none provided
        if databases is None:
            databases = ['pubmed', 'pmc', 'europepmc', 'biorxiv', 'sciencedirect', 'doaj', 'semanticscholar', 'googlescholar']
        
        # Reset study data
        self.studies_data = []
        
        # Process each database
        for db_name in databases:
            try:
                # Dynamically import the database module
                db_module = importlib.import_module(f"database.{db_name}")
                # Get the search function
                search_func = getattr(db_module, f"search_{db_name}")
                # Call the search function
                results = search_func(query, additional_terms, self.headers, self.max_results)
                
                if not results:
                    continue
                
                print(f"\nFound {len(results)} relevant studies on {db_name.capitalize()}")
                
                download_choice = input(f"Download {db_name.capitalize()} studies? (yes/no): ").strip().lower()
                if download_choice in ['yes', 'y']:
                    # Process studies (just one if in test mode)
                    study_count = 1 if test_mode else len(results)
                    
                    # Get the process function
                    if hasattr(db_module, f"process_{db_name}_results"):
                        process_func = getattr(db_module, f"process_{db_name}_results")
                        
                        processed_results = process_func(
                            results[:study_count], 
                            self.download_pdf, 
                            self.output_dir,
                            self.headers,
                            self.delay
                        )
                        
                        # Add the studies to our collection
                        for study in processed_results:
                            self.studies_data.append(study)
                            self.sources[db_name] += 1
                    else:
                        # Generic processing
                        for i, study in enumerate(results[:study_count]):
                            print(f"Processing {db_name} study {i+1}/{study_count}...")
                            
                            # Add database name
                            study['database'] = db_name.capitalize()
                            
                            # Try to download PDF if available
                            if study.get('pdf_link'):
                                identifier = study.get('pmid', study.get('doi', study.get('unique_id', f"{db_name}_{i}")))
                                if isinstance(identifier, str):
                                    identifier = identifier.replace('/', '_')
                                pdf_path = self.download_pdf(study['pdf_link'], f"{db_name}_{identifier}", overwrite=True)
                                study['local_pdf_path'] = pdf_path
                            
                            self.studies_data.append(study)
                            self.sources[db_name] += 1
                            
                            # Delay to prevent overloading the server
                            time.sleep(self.delay)
                    
                    if test_mode and len(results) > 1:
                        print(f"Test mode: Only downloaded 1 of {len(results)} studies from {db_name.capitalize()}")
            
            except Exception as e:
                print(f"Error processing {db_name}: {e}")
        
        # Export results to CSV and JSON
        self.export_results()
        
        # Create a DataFrame for easy viewing
        df = pd.DataFrame(self.studies_data)
        
        # Print summary of sources
        print("\nStudies found by source:")
        for source, count in self.sources.items():
            if count > 0:
                print(f"  {source.capitalize()}: {count}")
        
        return df
    
    def export_results(self):
        """Export the collected study data to CSV and JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Export to CSV
        csv_path = os.path.join(self.output_dir, f"studies_{timestamp}.csv")
        pd.DataFrame(self.studies_data).to_csv(csv_path, index=False)
        print(f"Exported study data to {csv_path}")
        
        # Export to JSON
        json_path = os.path.join(self.output_dir, f"studies_{timestamp}.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(self.studies_data, f, ensure_ascii=False, indent=4)
        print(f"Exported study data to {json_path}")

        # Create a simple HTML report
        html_report = generate_html_report(self.studies_data)
        html_path = os.path.join(self.output_dir, f"studies_report_{timestamp}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_report)
        print(f"Generated HTML report at {html_path}")
