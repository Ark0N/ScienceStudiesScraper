"""
PubMed Central (PMC) search module for NMN Study Downloader
"""

import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def search_pmc(query, additional_terms, headers, max_results=None):
    """Search PubMed Central for open access studies related to NMN.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of PMC IDs
    """
    base_query = query
    if additional_terms:
        base_query += " AND (" + " OR ".join(additional_terms) + ")"
    
    print(f"Searching PubMed Central for: {base_query}")
    
    # Encode the query for URL
    search_query = base_query.replace(' ', '+')
    url = f"https://www.ncbi.nlm.nih.gov/pmc/?term={search_query}&filter=simsearch1.fha"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract PMC IDs
        pmc_ids = []
        for article in soup.select('.rslt'):
            pmc_id = article.get('data-chunk-id')
            if pmc_id:
                pmc_ids.append(pmc_id)
        
        return pmc_ids[:max_results] if max_results else pmc_ids
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching PMC: {e}")
        return []

def get_pmc_details(pmc_id, headers):
    """Get details for a specific study by its PMC ID.
    
    Args:
        pmc_id (str): PMC ID of the study
        headers (dict): HTTP headers for requests
    
    Returns:
        dict: Study details
    """
    url = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract title
        title_elem = soup.select_one('.content-title')
        title = title_elem.text.strip() if title_elem else "Unknown Title"
        
        # Extract authors
        authors = []
        for author_elem in soup.select('.contrib-author'):
            authors.append(author_elem.text.strip())
        
        # Extract journal info
        journal_elem = soup.select_one('.journal-title')
        journal = journal_elem.text.strip() if journal_elem else "Unknown Journal"
        
        # Extract publication date
        date_elem = soup.select_one('.pub-date')
        pub_date = date_elem.text.strip() if date_elem else "Unknown Date"
        
        # Extract abstract
        abstract_elem = soup.select_one('.abstract')
        abstract = abstract_elem.text.strip() if abstract_elem else "Abstract not available"
        
        # Extract DOI if available
        doi = None
        doi_elem = soup.select_one('.doi')
        if doi_elem:
            doi_text = doi_elem.text.strip()
            doi_match = doi_text.replace('doi: ', '')
            if doi_match:
                doi = doi_match
        
        # Create PDF link
        pdf_link = f"{url.rstrip('/')}/pdf/"
        
        # Extract PMID if available
        pmid = None
        for id_elem in soup.select('.accid'):
            if 'PMID:' in id_elem.text:
                pmid = id_elem.text.replace('PMID:', '').strip()
                break
        
        return {
            'pmc_id': pmc_id,
            'pmid': pmid,
            'title': title,
            'authors': authors,
            'journal': journal,
            'publication_date': pub_date,
            'abstract': abstract,
            'pdf_link': pdf_link,
            'doi': doi,
            'source_url': url,
            'database': 'PMC'
        }
    
    except requests.exceptions.RequestException as e:
        print(f"Error getting details for PMC article {pmc_id}: {e}")
        return None

def process_pmc_results(pmc_ids, download_func, output_dir, headers, delay):
    """Process PMC search results.
    
    Args:
        pmc_ids (list): List of PMC IDs
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for pmc_id in pmc_ids:
        print(f"Processing PMC study {pmc_id}...")
        study_data = get_pmc_details(pmc_id, headers)
        
        if study_data:
            # Try to download PDF if available
            if study_data.get('pdf_link'):
                pdf_path = download_func(study_data['pdf_link'], f"pmc_{pmc_id}", overwrite=True)
                study_data['local_pdf_path'] = pdf_path
            
            processed_studies.append(study_data)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
