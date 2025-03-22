"""
Semantic Scholar search module for NMN Study Downloader
"""

import time
import requests

def search_semanticscholar(query, additional_terms, headers, max_results=None):
    """Search Semantic Scholar for NMN studies.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of article metadata
    """
    base_query = query
    if additional_terms:
        base_query += " " + " ".join(additional_terms)
    
    print(f"Searching Semantic Scholar for: {base_query}")
    
    # Note: This is using the public API which has rate limits
    # For production use, you should register for an API key
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    
    # API limit is 100 per request
    page_size = 100 if max_results is None or max_results > 100 else max_results
    
    params = {
        'query': base_query,
        'limit': page_size,
        'fields': 'paperId,title,abstract,url,year,journal,authors,openAccessPdf'
    }
    
    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        if 'data' in data:
            for item in data['data']:
                # Get PDF link if available
                pdf_link = None
                if 'openAccessPdf' in item and item['openAccessPdf']:
                    pdf_link = item['openAccessPdf'].get('url')
                
                study = {
                    'paper_id': item.get('paperId', ''),
                    'title': item.get('title', 'Unknown Title'),
                    'authors': [author.get('name', '') for author in item.get('authors', [])],
                    'journal': item.get('journal', {}).get('name', 'Unknown Journal'),
                    'publication_date': str(item.get('year', 'Unknown Date')),
                    'abstract': item.get('abstract', 'Abstract not available'),
                    'source_url': item.get('url', ''),
                    'pdf_link': pdf_link,
                    'database': 'Semantic Scholar'
                }
                results.append(study)
                
                if max_results is not None and len(results) >= max_results:
                    break
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching Semantic Scholar: {e}")
        return []

def process_semanticscholar_results(results, download_func, output_dir, headers, delay):
    """Process Semantic Scholar search results.
    
    Args:
        results (list): List of Semantic Scholar study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for study in results:
        print(f"Processing Semantic Scholar article: {study.get('paper_id', 'Unknown ID')}...")
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            identifier = study.get('paper_id', '').replace('/', '_') if study.get('paper_id') else f"semantic_{len(processed_studies)}"
            pdf_path = download_func(study['pdf_link'], f"semantic_{identifier}", overwrite=True)
            study['local_pdf_path'] = pdf_path
        
        processed_studies.append(study)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
