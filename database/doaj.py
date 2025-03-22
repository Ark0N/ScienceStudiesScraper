"""
DOAJ (Directory of Open Access Journals) search module for NMN Study Downloader
"""

import time
import requests

def search_doaj(query, additional_terms, headers, max_results=None):
    """Search Directory of Open Access Journals for NMN studies.
    
    Args:
        query (str): Search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of article metadata
    """
    print(f"Searching DOAJ for: {query}")
    
    # Encode the query for URL
    search_query = query.replace(' ', '+')
    page_size = 100 if max_results is None or max_results > 100 else max_results
    url = f"https://doaj.org/api/search/articles/{search_query}?pageSize={page_size}"
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        results = []
        
        if 'results' in data:
            for item in data['results']:
                bibjson = item.get('bibjson', {})
                
                # Extract authors
                authors = []
                for author in bibjson.get('author', []):
                    name_parts = []
                    if 'name' in author:
                        name_parts.append(author['name'])
                    else:
                        if 'given' in author:
                            name_parts.append(author['given'])
                        if 'family' in author:
                            name_parts.append(author['family'])
                    authors.append(' '.join(name_parts))
                
                # Get journal
                journal = bibjson.get('journal', {}).get('title', 'Unknown Journal')
                
                # Get URL and PDF link
                source_url = None
                pdf_link = None
                for link in bibjson.get('link', []):
                    if link.get('type') == 'fulltext':
                        source_url = link.get('url')
                    if link.get('content_type', '').lower() == 'application/pdf':
                        pdf_link = link.get('url')
                
                # Extract DOI - handle identifier as either list or dict
                doi = ""
                identifiers = bibjson.get('identifier', [])
                if isinstance(identifiers, list):
                    # Handle identifier as list
                    for identifier in identifiers:
                        if identifier.get('type') == 'doi':
                            doi = identifier.get('id', '')
                            break
                elif isinstance(identifiers, dict):
                    # Handle identifier as dictionary (old method)
                    doi = identifiers.get('doi', '')
                
                study = {
                    'doi': doi,
                    'title': bibjson.get('title', 'Unknown Title'),
                    'authors': authors,
                    'journal': journal,
                    'publication_date': bibjson.get('year', 'Unknown Date'),
                    'abstract': bibjson.get('abstract', 'Abstract not available'),
                    'source_url': source_url or (f"https://doi.org/{doi}" if doi else "#"),
                    'pdf_link': pdf_link,
                    'database': 'DOAJ'
                }
                results.append(study)
                
                if max_results is not None and len(results) >= max_results:
                    break
        
        return results
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching DOAJ: {e}")
        return []

def process_doaj_results(results, download_func, output_dir, headers, delay):
    """Process DOAJ search results.
    
    Args:
        results (list): List of DOAJ study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for study in results:
        print(f"Processing DOAJ article: {study.get('doi', 'Unknown DOI')}...")
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            identifier = study.get('doi', '').replace('/', '_') if study.get('doi') else f"doaj_{len(processed_studies)}"
            pdf_path = download_func(study['pdf_link'], f"doaj_{identifier}", overwrite=True)
            study['local_pdf_path'] = pdf_path
        
        processed_studies.append(study)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
