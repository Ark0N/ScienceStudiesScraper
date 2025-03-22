"""
bioRxiv/medRxiv search module for NMN Study Downloader
"""

import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def search_biorxiv(query, additional_terms, headers, max_results=None):
    """Search bioRxiv and medRxiv for preprints related to NMN.
    
    Args:
        query (str): Main search query
        additional_terms (list): Additional search terms to refine results
        headers (dict): HTTP headers for requests
        max_results (int): Maximum number of results to retrieve
    
    Returns:
        list: List of preprint metadata
    """
    # For bioRxiv, we need to use simpler search terms
    # Extract main keywords - NMN or Nicotinamide
    main_terms = []
    if "NMN" in query:
        main_terms.append("NMN")
    if "Nicotinamide" in query:
        main_terms.append("Nicotinamide")
    if "Mononucleotide" in query:
        main_terms.append("Mononucleotide")
    
    # If no matches, use the first word
    if not main_terms and " " in query:
        main_terms.append(query.split()[0])
    elif not main_terms:
        main_terms.append(query)
    
    results = []
    
    # Try each main term
    for term in main_terms:
        print(f"Searching bioRxiv/medRxiv for: {term}")
        
        # Search bioRxiv using content server
        results.extend(_search_biorxiv_site(term, headers))
        
        # Also search medRxiv
        results.extend(_search_medrxiv_site(term, headers))
        
        # Delay between searches
        time.sleep(1)
    
    print(f"Found {len(results)} relevant preprints on bioRxiv/medRxiv")
    return results[:max_results] if max_results else results

def _search_biorxiv_site(term, headers):
    """Search the bioRxiv website directly.
    
    Args:
        term (str): Search term
        headers (dict): HTTP headers for requests
    
    Returns:
        list: bioRxiv results
    """
    results = []
    try:
        search_url = f"https://www.biorxiv.org/search/{term}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract articles
        for article in soup.select('.highwire-article-citation'):
            title_elem = article.select_one('.highwire-cite-title')
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            link_elem = title_elem.find('a') if title_elem else None
            article_link = link_elem.get('href') if link_elem else ""
            full_link = urljoin("https://www.biorxiv.org", article_link) if article_link else ""
            
            doi_elem = article.select_one('.highwire-cite-metadata-doi')
            doi = doi_elem.text.strip().replace('DOI: ', '') if doi_elem else ""
            
            date_elem = article.select_one('.highwire-cite-metadata-date')
            date = date_elem.text.strip() if date_elem else "Unknown Date"
            
            # Extract authors
            authors = []
            for author_elem in article.select('.highwire-citation-author'):
                authors.append(author_elem.text.strip())
            
            # Get abstract if possible (need to visit the article page)
            abstract = "Abstract not available via search"
            if full_link:
                try:
                    article_response = requests.get(full_link, headers=headers, timeout=5)
                    article_soup = BeautifulSoup(article_response.text, 'html.parser')
                    abstract_elem = article_soup.select_one('.abstract')
                    if abstract_elem:
                        abstract = abstract_elem.text.strip()
                except:
                    # Skip if we can't get the abstract
                    pass
            
            pdf_link = ""
            if doi:
                pdf_link = f"https://www.biorxiv.org/content/10.1101/{doi.split('/')[-1]}.full.pdf"
            elif full_link:
                pdf_link = full_link + ".full.pdf"
            
            study = {
                'doi': doi,
                'title': title,
                'authors': authors,
                'journal': 'bioRxiv',
                'publication_date': date,
                'abstract': abstract,
                'source_url': full_link,
                'pdf_link': pdf_link,
                'database': 'bioRxiv'
            }
            
            # Only add if related to NMN/NAD+
            if (
                "NMN" in title or 
                "Nicotinamide" in title or 
                "NAD+" in title or
                "Nicotinamide" in abstract or
                "NMN" in abstract or
                "NAD+" in abstract
            ):
                results.append(study)
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching bioRxiv via web: {e}")
    
    return results

def _search_medrxiv_site(term, headers):
    """Search the medRxiv website directly.
    
    Args:
        term (str): Search term
        headers (dict): HTTP headers for requests
    
    Returns:
        list: medRxiv results
    """
    results = []
    try:
        search_url = f"https://www.medrxiv.org/search/{term}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract articles (similar code as above)
        for article in soup.select('.highwire-article-citation'):
            title_elem = article.select_one('.highwire-cite-title')
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            link_elem = title_elem.find('a') if title_elem else None
            article_link = link_elem.get('href') if link_elem else ""
            full_link = urljoin("https://www.medrxiv.org", article_link) if article_link else ""
            
            doi_elem = article.select_one('.highwire-cite-metadata-doi')
            doi = doi_elem.text.strip().replace('DOI: ', '') if doi_elem else ""
            
            date_elem = article.select_one('.highwire-cite-metadata-date')
            date = date_elem.text.strip() if date_elem else "Unknown Date"
            
            # Extract authors
            authors = []
            for author_elem in article.select('.highwire-citation-author'):
                authors.append(author_elem.text.strip())
            
            # Get abstract if possible
            abstract = "Abstract not available via search"
            
            pdf_link = ""
            if doi:
                pdf_link = f"https://www.medrxiv.org/content/10.1101/{doi.split('/')[-1]}.full.pdf"
            elif full_link:
                pdf_link = full_link + ".full.pdf"
            
            study = {
                'doi': doi,
                'title': title,
                'authors': authors,
                'journal': 'medRxiv',
                'publication_date': date,
                'abstract': abstract,
                'source_url': full_link,
                'pdf_link': pdf_link,
                'database': 'medRxiv'
            }
            
            # Only add if related to NMN/NAD+
            if (
                "NMN" in title or 
                "Nicotinamide" in title or 
                "NAD+" in title
            ):
                results.append(study)
    
    except requests.exceptions.RequestException as e:
        print(f"Error searching medRxiv via web: {e}")
    
    return results

def process_biorxiv_results(results, download_func, output_dir, headers, delay):
    """Process bioRxiv/medRxiv search results.
    
    Args:
        results (list): List of bioRxiv study metadata
        download_func (function): Function to download PDFs
        output_dir (str): Output directory
        headers (dict): HTTP headers for requests
        delay (int): Delay between requests
    
    Returns:
        list: List of processed study data
    """
    processed_studies = []
    
    for study in results:
        print(f"Processing bioRxiv/medRxiv preprint: {study.get('doi', 'Unknown DOI')}...")
        
        # Try to download PDF if available
        if study.get('pdf_link'):
            identifier = study.get('doi', '').split('/')[-1] if study.get('doi') else f"biorxiv_{len(processed_studies)}"
            pdf_path = download_func(study['pdf_link'], f"biorxiv_{identifier}", overwrite=True)
            study['local_pdf_path'] = pdf_path
        
        processed_studies.append(study)
        
        # Delay to prevent overloading the server
        time.sleep(delay)
    
    return processed_studies
