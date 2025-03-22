"""
PDF generation utilities for Science Study Scraper
"""

import requests
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

def extract_article_content(url, study_data, headers):
    """Extract full article content from the web page.
    
    Args:
        url (str): URL of the article page
        study_data (dict): Study data dictionary
        headers (dict): HTTP headers for requests
    
    Returns:
        dict: Article content with sections
    """
    if not url:
        return None
    
    print(f"Attempting to extract article content from: {url}")
    
    article_content = {
        'title': study_data.get('title', 'Unknown Title'),
        'authors': study_data.get('authors', []),
        'journal': study_data.get('journal', 'Unknown Journal'),
        'publication_date': study_data.get('publication_date', 'Unknown Date'),
        'abstract': study_data.get('abstract', ''),
        'sections': [],
        'references': []
    }
    
    try:
        # Create a session with retry capabilities
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=30, allow_redirects=True)
        response.raise_for_status()
        
        # Detect source and use appropriate extraction method
        if 'pubmed.ncbi.nlm.nih.gov' in url:
            return _extract_from_pubmed(response.text, study_data)
        elif 'ncbi.nlm.nih.gov/pmc' in url:
            return _extract_from_pmc(response.text, study_data)
        elif 'europepmc.org' in url:
            return _extract_from_europepmc(response.text, study_data)
        else:
            # Generic content extraction
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Try to find the main article content
            article_elem = soup.select_one('article, .article, .content, main, #content, #main')
            
            if not article_elem:
                # Fallback to common content patterns
                article_elem = soup
            
            # Extract sections
            for section in article_elem.select('section, .section, h1 + p, h2 + p, h3 + p'):
                section_title = None
                section_content = []
                
                # Find section title
                heading = section.find_previous(['h1', 'h2', 'h3', 'h4'])
                if heading:
                    section_title = heading.text.strip()
                
                # Extract section content
                for p in section.select('p'):
                    if p.text.strip():
                        section_content.append(p.text.strip())
                
                if section_title and section_content:
                    article_content['sections'].append({
                        'title': section_title,
                        'content': '\n\n'.join(section_content)
                    })
            
            # If no sections were found, try to grab all paragraphs
            if not article_content['sections']:
                all_paragraphs = article_elem.select('p')
                content = '\n\n'.join([p.text.strip() for p in all_paragraphs if p.text.strip()])
                
                if content:
                    article_content['sections'].append({
                        'title': 'Content',
                        'content': content
                    })
        
        return article_content
            
    except Exception as e:
        print(f"Error extracting article content: {e}")
        return None

def _extract_from_pubmed(html, study_data):
    """Extract article content from PubMed page.
    
    Args:
        html (str): HTML content of the page
        study_data (dict): Study data dictionary
    
    Returns:
        dict: Article content
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    article_content = {
        'title': study_data.get('title', 'Unknown Title'),
        'authors': study_data.get('authors', []),
        'journal': study_data.get('journal', 'Unknown Journal'),
        'publication_date': study_data.get('publication_date', 'Unknown Date'),
        'abstract': '',
        'sections': [],
        'references': []
    }
    
    # Extract abstract
    abstract_elem = soup.select_one('#abstract')
    if abstract_elem:
        abstract_text = abstract_elem.get_text().strip()
        article_content['abstract'] = abstract_text
        
        # Add abstract as first section
        article_content['sections'].append({
            'title': 'Abstract',
            'content': abstract_text
        })
    
    # PubMed usually doesn't contain full text, so we check for link to PMC
    pmc_link = None
    for link in soup.select('a'):
        if 'pmc/articles/PMC' in link.get('href', ''):
            pmc_link = link.get('href')
            print(f"Found PMC link for full text: {pmc_link}")
            break
    
    # If PMC link found, try to extract content from there
    if pmc_link:
        try:
            response = requests.get(pmc_link, headers={'User-Agent': 'Mozilla/5.0'})
            response.raise_for_status()
            return _extract_from_pmc(response.text, study_data)
        except Exception as e:
            print(f"Error fetching PMC content: {e}")
    
    return article_content

def _extract_from_pmc(html, study_data):
    """Extract article content from PMC page.
    
    Args:
        html (str): HTML content of the page
        study_data (dict): Study data dictionary
    
    Returns:
        dict: Article content
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    article_content = {
        'title': study_data.get('title', 'Unknown Title'),
        'authors': study_data.get('authors', []),
        'journal': study_data.get('journal', 'Unknown Journal'),
        'publication_date': study_data.get('publication_date', 'Unknown Date'),
        'abstract': '',
        'sections': [],
        'references': []
    }
    
    # Extract abstract
    abstract_elem = soup.select_one('.abstract')
    if abstract_elem:
        abstract_text = abstract_elem.get_text().strip()
        article_content['abstract'] = abstract_text
        
        # Add abstract as first section
        article_content['sections'].append({
            'title': 'Abstract',
            'content': abstract_text
        })
    
    # Extract sections from PMC full text article
    main_content = soup.select_one('.jig-ncbiinpagenav, .article')
    if main_content:
        # Find all section headers and their content
        sections = []
        current_section = None
        
        for element in main_content.find_all(['h2', 'h3', 'h4', 'p', 'div']):
            if element.name in ['h2', 'h3', 'h4'] and element.text.strip():
                # Start a new section
                if current_section and current_section['content']:
                    sections.append(current_section)
                
                current_section = {
                    'title': element.text.strip(),
                    'content': ''
                }
            elif element.name == 'p' and current_section:
                # Add paragraph content to current section
                if element.text.strip():
                    if current_section['content']:
                        current_section['content'] += '\n\n'
                    current_section['content'] += element.text.strip()
            elif element.name == 'div' and 'sec' in element.get('class', []) and current_section is None:
                # Handle complete sections in divs
                sec_title = element.select_one('.sec-title')
                sec_content = element.select_one('.sec-content')
                
                if sec_title and sec_content:
                    sections.append({
                        'title': sec_title.text.strip(),
                        'content': sec_content.text.strip()
                    })
        
        # Add the last section if it exists
        if current_section and current_section['content']:
            sections.append(current_section)
        
        # Add all sections to article content
        article_content['sections'].extend(sections)
    
    # If no sections were extracted, try to get the full article text
    if not article_content['sections'] or (len(article_content['sections']) == 1 and article_content['sections'][0]['title'] == 'Abstract'):
        full_text = soup.select_one('.article-body, .article')
        if full_text:
            text_content = full_text.get_text().strip()
            article_content['sections'].append({
                'title': 'Full Text',
                'content': text_content
            })
    
    # Extract references
    refs_section = soup.select_one('.ref-list, .references')
    if refs_section:
        refs = []
        for ref in refs_section.select('li, .ref'):
            ref_text = ref.get_text().strip()
            if ref_text:
                refs.append(ref_text)
        
        article_content['references'] = refs
        
        # Add references as a section
        if refs:
            article_content['sections'].append({
                'title': 'References',
                'content': '\n\n'.join(refs)
            })
    
    return article_content

def _extract_from_europepmc(html, study_data):
    """Extract article content from Europe PMC page.
    
    Args:
        html (str): HTML content of the page
        study_data (dict): Study data dictionary
    
    Returns:
        dict: Article content
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    article_content = {
        'title': study_data.get('title', 'Unknown Title'),
        'authors': study_data.get('authors', []),
        'journal': study_data.get('journal', 'Unknown Journal'),
        'publication_date': study_data.get('publication_date', 'Unknown Date'),
        'abstract': '',
        'sections': [],
        'references': []
    }
    
    # Extract abstract
    abstract_elem = soup.select_one('.abstract-content')
    if abstract_elem:
        abstract_text = abstract_elem.get_text().strip()
        article_content['abstract'] = abstract_text
        
        # Add abstract as first section
        article_content['sections'].append({
            'title': 'Abstract',
            'content': abstract_text
        })
    
    # Extract full text sections
    main_content = soup.select_one('#free-full-text, #full-view-heading-content')
    if main_content:
        # Find all section headers and their content
        current_section = None
        
        for element in main_content.find_all(['h2', 'h3', 'h4', 'p']):
            if element.name in ['h2', 'h3', 'h4'] and element.text.strip():
                # Start a new section
                if current_section and current_section['content']:
                    article_content['sections'].append(current_section)
                
                current_section = {
                    'title': element.text.strip(),
                    'content': ''
                }
            elif element.name == 'p' and current_section:
                # Add paragraph content to current section
                if element.text.strip():
                    if current_section['content']:
                        current_section['content'] += '\n\n'
                    current_section['content'] += element.text.strip()
        
        # Add the last section if it exists
        if current_section and current_section['content']:
            article_content['sections'].append(current_section)
    
    # If no sections were extracted, try with section divs
    if len(article_content['sections']) <= 1:  # Only abstract or nothing
        for section in soup.select('.sect'):
            title_elem = section.select_one('.title')
            
            title = title_elem.text.strip() if title_elem else 'Section'
            content = section.get_text().strip()
            
            if title_elem:
                # Remove the title from the content
                content = content.replace(title, '', 1).strip()
            
            if content:
                article_content['sections'].append({
                    'title': title,
                    'content': content
                })
    
    # Extract references
    refs_section = soup.select_one('.reference-list')
    if refs_section:
        refs = []
        for ref in refs_section.select('li'):
            ref_text = ref.get_text().strip()
            if ref_text:
                refs.append(ref_text)
        
        article_content['references'] = refs
        
        # Add references as a section
        if refs:
            article_content['sections'].append({
                'title': 'References',
                'content': '\n\n'.join(refs)
            })
    
    return article_content

def generate_pdf_from_content(article_content, filename):
    """Generate a PDF file from article content.
    
    Args:
        article_content (dict): Article content
        filename (str): Output filename
    
    Returns:
        str: Path to the generated PDF file
    """
    if not article_content:
        return None
    
    try:
        # Create a PDF document
        doc = SimpleDocTemplate(
            filename,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        # Define styles
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        heading1_style = styles['Heading1']
        heading2_style = styles['Heading2']
        normal_style = styles['Normal']
        
        # Custom styles
        author_style = ParagraphStyle(
            'AuthorStyle',
            parent=normal_style,
            textColor=colors.darkblue,
            spaceAfter=0.2*inch
        )
        
        journal_style = ParagraphStyle(
            'JournalStyle',
            parent=normal_style,
            textColor=colors.darkgrey,
            fontSize=9,
            spaceAfter=0.3*inch
        )
        
        # Build the document
        story = []
        
        # Title
        story.append(Paragraph(article_content['title'], title_style))
        story.append(Spacer(1, 0.1*inch))
        
        # Authors
        if article_content['authors']:
            authors_text = ', '.join(article_content['authors'])
            story.append(Paragraph(authors_text, author_style))
        
        # Journal and date
        journal_text = f"{article_content['journal']} • {article_content['publication_date']}"
        story.append(Paragraph(journal_text, journal_style))
        story.append(Spacer(1, 0.2*inch))
        
        # Sections
        for section in article_content['sections']:
            # Section heading
            story.append(Paragraph(section['title'], heading1_style))
            story.append(Spacer(1, 0.1*inch))
            
            # Section content - split paragraphs
            paragraphs = section['content'].split('\n\n')
            for para in paragraphs:
                if para.strip():
                    story.append(Paragraph(para, normal_style))
                    story.append(Spacer(1, 0.1*inch))
            
            story.append(Spacer(1, 0.2*inch))
        
        # Build the PDF
        doc.build(story)
        print(f"Successfully generated PDF: {filename}")
        
        return filename
    
    except Exception as e:
        print(f"Error generating PDF: {e}")
        return None
