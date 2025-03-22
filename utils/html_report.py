"""
HTML report generation for Science Study Scraper
"""

from datetime import datetime
import os

def generate_html_report(studies_data):
    """Generate a simple HTML report of the studies.
    
    Args:
        studies_data (list): List of study data dictionaries
    
    Returns:
        str: HTML report content
    """
    # Count studies by database
    db_counts = {}
    for study in studies_data:
        db = study.get('database', 'Unknown')
        db_counts[db] = db_counts.get(db, 0) + 1
    
    # Extract the query from the first study if available
    query_topic = "Scientific Studies"
    if studies_data and 'title' in studies_data[0]:
        # Try to extract a topic from the title
        words = studies_data[0]['title'].split()
        if len(words) >= 2:
            query_topic = ' '.join(words[:2])
    
    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Science Study Scraper - Report</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .summary { background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 30px; }
            .summary-title { font-weight: bold; margin-bottom: 10px; }
            .summary-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 10px; }
            .summary-item { padding: 8px; background-color: #e9ecef; border-radius: 4px; text-align: center; }
            .database-label { font-weight: bold; }
            .count-label { color: #2c3e50; }
            .filters { margin-bottom: 20px; display: flex; flex-wrap: wrap; gap: 10px; }
            .filter-button { padding: 8px 15px; background-color: #f1f1f1; border: none; border-radius: 20px; cursor: pointer; }
            .filter-button.active { background-color: #3498db; color: white; }
            .study { border: 1px solid #ddd; padding: 20px; margin-bottom: 20px; border-radius: 5px; }
            .study-title { font-size: 18px; font-weight: bold; color: #2c3e50; margin-bottom: 10px; }
            .study-meta { color: #7f8c8d; margin-bottom: 10px; font-size: 14px; }
            .study-abstract { line-height: 1.6; }
            .study-links { margin-top: 15px; }
            .study-links a { color: #3498db; text-decoration: none; margin-right: 15px; }
            .study-links a:hover { text-decoration: underline; }
            .database-tag { display: inline-block; padding: 3px 8px; border-radius: 3px; font-size: 12px; margin-right: 8px; color: white; }
            .tag-pubmed { background-color: #4CAF50; }
            .tag-pmc { background-color: #2196F3; }
            .tag-europepmc { background-color: #2196F3; }
            .tag-biorxiv { background-color: #FF9800; }
            .tag-medrxiv { background-color: #FF9800; }
            .tag-doaj { background-color: #9C27B0; }
            .tag-semanticscholar { background-color: #607D8B; }
            .tag-sciencedirect { background-color: #E91E63; }
            .tag-googlescholar { background-color: #4285F4; }
            .tag-unknown { background-color: #9E9E9E; }
            .no-results { text-align: center; padding: 40px; background-color: #f8f9fa; border-radius: 5px; }
            .search-box { margin-bottom: 20px; }
            .search-input { padding: 10px; width: 100%; max-width: 500px; border-radius: 5px; border: 1px solid #ddd; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Science Study Scraper Report</h1>
                <p>Generated on: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
                <p>Total studies found: """ + str(len(studies_data)) + """</p>
            </div>
            
            <div class="summary">
                <div class="summary-title">Sources Summary:</div>
                <div class="summary-grid">
    """
    
    # Add summary boxes for each database
    for db, count in db_counts.items():
        html += f"""
                    <div class="summary-item">
                        <div class="database-label">{db}</div>
                        <div class="count-label">{count} studies</div>
                    </div>
        """
    
    html += """
                </div>
            </div>
            
            <div class="search-box">
                <input type="text" id="study-search" class="search-input" placeholder="Search studies by title, author, journal...">
            </div>
            
            <div class="filters">
                <button class="filter-button active" data-filter="all">All Sources</button>
    """
    
    # Add filter buttons for each database
    for db in db_counts.keys():
        db_class = db.lower().replace(' ', '')
        html += f"""
                <button class="filter-button" data-filter="{db_class}">{db}</button>
        """
    
    html += """
            </div>
            
            <div id="studies-container">
    """
    
    for study in studies_data:
        # Get database and create CSS class
        db = study.get('database', 'Unknown')
        db_class = db.lower().replace(' ', '')
        
        # Determine what ID to show (PMID, DOI, etc.)
        id_label = "ID"
        id_value = "N/A"
        
        if study.get('pmid'):
            id_label = "PMID"
            id_value = study.get('pmid')
        elif study.get('pmc_id'):
            id_label = "PMC ID"
            id_value = study.get('pmc_id')
        elif study.get('doi'):
            id_label = "DOI"
            id_value = study.get('doi')
        elif study.get('paper_id'):
            id_label = "Paper ID"
            id_value = study.get('paper_id')
        
        # Create local PDF link
        pdf_link = ''
        if study.get('local_pdf_path'):
            filename = os.path.basename(study['local_pdf_path'])
            pdf_link = f'<a href="pdfs/{filename}" target="_blank">Download PDF</a>'
        
        html += f"""
            <div class="study" data-source="{db_class}">
                <div class="study-title">
                    <span class="database-tag tag-{db_class}">{db}</span>
                    {study.get('title', 'Unknown Title')}
                </div>
                <div class="study-meta">
                    <strong>Authors:</strong> {', '.join(study.get('authors', ['Unknown'])[:3])}
                    {' et al.' if len(study.get('authors', [])) > 3 else ''}<br>
                    <strong>Journal:</strong> {study.get('journal', 'Unknown Journal')}<br>
                    <strong>Publication Date:</strong> {study.get('publication_date', 'Unknown Date')}<br>
                    <strong>{id_label}:</strong> {id_value}
                </div>
                <div class="study-abstract">
                    <strong>Abstract:</strong><br>
                    {study.get('abstract', 'Abstract not available')}
                </div>
                <div class="study-links">
                    <a href="{study.get('source_url', '#')}" target="_blank">View Source</a>
                    {pdf_link}
                </div>
            </div>
        """
    
    html += """
            <div class="no-results" style="display: none;">
                No studies found matching the selected filter or search term.
            </div>
            </div>
        </div>
        
        <script>
            // Filter and search functionality
            document.addEventListener('DOMContentLoaded', function() {
                const filterButtons = document.querySelectorAll('.filter-button');
                const studies = document.querySelectorAll('.study');
                const noResults = document.querySelector('.no-results');
                const searchInput = document.getElementById('study-search');
                
                // Filter by database
                filterButtons.forEach(button => {
                    button.addEventListener('click', function() {
                        // Update active button
                        filterButtons.forEach(btn => btn.classList.remove('active'));
                        this.classList.add('active');
                        
                        // Apply filter
                        applyFilters();
                    });
                });
                
                // Search functionality
                searchInput.addEventListener('input', function() {
                    applyFilters();
                });
                
                function applyFilters() {
                    const activeFilter = document.querySelector('.filter-button.active').getAttribute('data-filter');
                    const searchTerm = searchInput.value.toLowerCase();
                    
                    let visibleCount = 0;
                    
                    studies.forEach(study => {
                        const matchesFilter = activeFilter === 'all' || study.getAttribute('data-source') === activeFilter;
                        
                        // Check if study matches search term
                        const studyContent = study.textContent.toLowerCase();
                        const matchesSearch = searchTerm === '' || studyContent.includes(searchTerm);
                        
                        if (matchesFilter && matchesSearch) {
                            study.style.display = 'block';
                            visibleCount++;
                        } else {
                            study.style.display = 'none';
                        }
                    });
                    
                    // Show "no results" message if needed
                    noResults.style.display = visibleCount === 0 ? 'block' : 'none';
                }
            });
        </script>
    </body>
    </html>
    """
    
    return html
