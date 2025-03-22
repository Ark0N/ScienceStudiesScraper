"""
ScienceDirect search module for NMN Study Downloader
"""

import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def search_sciencedirect(query, additional_terms, headers, max_results=None):
    """Search ScienceDirect for open access studies related to NMN.
    
    Note: This is a simplified implementation. ScienceDirect might require
    an API key for programmatic access to their articles.
    
    Args:
        query (str): Search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of article URLs and metadata
    """
    print(f"Searching ScienceDirect for: {query}")
    
    # Encode the query for URL
    search_query = query.replace(' ', '+')
    url = f"https://www.sciencedirect.com/search?qs={search_query}&show=100&accessTypes=openaccess"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Parse the HTML response
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract article information
        results = []
        for result in soup.select('.result-item-content'):
            # Get title and URL
            title_elem = result.select_one('a.result-list-title-link')
            if not title_elem:
                continue
                
            title = title_elem.text.strip()
            article_url = urljoin(url, title_elem.get('href', ''))
            
            # Get authors
            authors = []
            authors_elem = result.select_one('.authors')
            if authors_elem:
                for author in authors_elem.select('.author'):
                    authors.append(author.text.strip())
            
            # Get journal
            journal = "Unknown Journal"
            journal_elem = result.select_one('.publication-title')
            if journal_elem:
                journal = journal_elem.text.strip()
            
            # Get date
            date = "Unknown Date"
            date_elem = result.select_one('.srctitle-date-fields .preceding-comma')
            if date_elem:
                date = date_elem.text.strip().replace(',', '')
            
            study = {
                'title': title,
                'authors': authors,
                'journal': journal,
                'publication_date': date,
                'abstract': "Abstract not available", # Would need to visit article page to get this
                'source_url': article_url,
                'pdf_link': article_url.replace('/science/article/pii/', '/science/article/pdf/') + "/pdf",
                'database': 'ScienceDirect'
            }
            
            results.append(study)
            
            if max_results is not None and len(results) >= max_results:
                break
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching ScienceDirect: {e}")
        return []

def process_sciencedirect_results(results, download_func, output_dir, headers, delay):
    """Process ScienceDirect search results.
    
    Args:
        results (list): List of ScienceDirect study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for i, study in enumerate(results):
        print(f"Processing ScienceDirect article {i+1}: {study.get('title')[:50]}...")
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            pdf_path = download_func(study['pdf_link'], f"sciencedirect_{i}", overwrite=True)
            study['local_pdf_path'] = pdf_path
        
        processed_studies.append(study)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
