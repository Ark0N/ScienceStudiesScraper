#!/usr/bin/env python3
"""
Science Study Scraper - Main script
Automatically find and download scientific studies from open access repositories
on any topic in the scientific and medical field.
"""

import argparse
from downloader import ScienceStudyScraper

def main():
    """Main function to run the Science Study Scraper."""
    parser = argparse.ArgumentParser(description='Download scientific studies on any topic')
    parser.add_argument('--output', '-o', type=str, default='studies',
                        help='Output directory for downloaded studies')
    parser.add_argument('--max-results', '-m', type=int, default=None,
                        help='Maximum number of results to retrieve (default: unlimited)')
    parser.add_argument('--query', '-q', type=str, default=None,
                        help='Main search query (required if no saved query)')
    parser.add_argument('--terms', '-t', type=str, nargs='+',
                        help='Additional search terms to refine results')
    parser.add_argument('--delay', '-d', type=int, default=1,
                        help='Delay between requests in seconds')
    parser.add_argument('--databases', type=str, nargs='+', 
                        choices=['pubmed', 'pmc', 'europepmc', 'biorxiv', 'sciencedirect', 'doaj', 'semanticscholar', 'googlescholar', 'all'],
                        default=['all'],
                        help='Databases to search (default: all)')
    parser.add_argument('--test', action='store_true',
                        help='Test mode: only download one study per database')
    parser.add_argument('--save-query', action='store_true',
                        help='Save the current query for future use')
    parser.add_argument('--load-saved', action='store_true',
                        help='Load the previously saved query')
    
    args = parser.parse_args()
    
    # Process databases argument
    if 'all' in args.databases:
        databases = ['pubmed', 'pmc', 'europepmc', 'biorxiv', 'sciencedirect', 'doaj', 'semanticscholar', 'googlescholar']
    else:
        databases = args.databases
    
    scraper = ScienceStudyScraper(
        output_dir=args.output,
        max_results=args.max_results,
        delay=args.delay
    )
    
    query = args.query
    additional_terms = args.terms
    
    # Handle saved queries
    if args.load_saved:
        try:
            saved_query = scraper.load_saved_query()
            if saved_query:
                query = saved_query.get('query')
                additional_terms = saved_query.get('terms')
                print(f"Loaded saved query: '{query}' with terms: {additional_terms}")
        except Exception as e:
            print(f"Error loading saved query: {e}")
    
    # Verify we have a query
    if not query:
        print("Error: No query provided. Please use --query to specify a search term or --load-saved to use a saved query.")
        return
    
    results = scraper.run(
        query=query, 
        additional_terms=additional_terms, 
        databases=databases,
        test_mode=args.test
    )
    
    # Save the query if requested
    if args.save_query and query:
        scraper.save_query(query, additional_terms)
        print(f"Saved query for future use: '{query}' with terms: {additional_terms}")
    
    print(f"\nDownloaded information for {len(results)} studies.")
    print(f"Results saved to {args.output} directory.")

if __name__ == "__main__":
    main()
