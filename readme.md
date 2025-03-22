# Science Study Scraper

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)

**Science Study Scraper** is a powerful tool designed to automatically find and download scientific studies from open access repositories on any topic in the scientific and medical field. This tool is part of the https://bio-hacking.blog and is used as an research tool.

## 🔍 Features

- **Multi-Database Search**: Search across PubMed, PMC, Europe PMC, bioRxiv, ScienceDirect, DOAJ, Semantic Scholar, and Google Scholar
- **Automatic PDF Downloads**: Download full-text PDFs when available
- **Content Extraction**: Create PDF documents from article content when direct PDFs are unavailable
- **Interactive HTML Reports**: Generate beautiful, interactive reports of your search results
- **Flexible Query Building**: Refine searches with additional terms and filters
- **Query Management**: Save and load previous search queries
- **Test Mode**: Try out the scraper with limited downloads before a full run

## 📋 Requirements

- Python 3.7 or higher
- Required packages: `requests`, `beautifulsoup4`, `pandas`, `reportlab`

## 🚀 Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/Ark0N/ScienceStudiesScraper.git
   cd science-study-scraper
   ```

2. Install required packages:
   ```bash
   cd science_scraper
   pip install -r requirements.txt
   ```

## 📚 Usage

### Basic Usage

Run a search with a specific query:

```bash
python main.py --query "diabetes treatment"
```

Use the test option to download only one study per database:

```bash
python main.py --test --query "nmn"
```

### Advanced Options

```bash
python main.py --query "cancer immunotherapy" --terms "clinical trial" "systematic review" --max-results 50 --databases pubmed pmc --delay 2
```

### Command Line Options

| Option | Description |
| ------ | ----------- |
| `--query`, `-q` | Main search query (required if no saved query) |
| `--terms`, `-t` | Additional search terms to refine results |
| `--output`, `-o` | Output directory for downloaded studies (default: 'studies') |
| `--max-results`, `-m` | Maximum number of results to retrieve (default: unlimited) |
| `--delay`, `-d` | Delay between requests in seconds (default: 1) |
| `--databases` | Databases to search (choices: pubmed, pmc, europepmc, biorxiv, sciencedirect, doaj, semanticscholar, googlescholar, all) |
| `--test` | Test mode: only download one study per database |
| `--save-query` | Save the current query for future use |
| `--load-saved` | Load the previously saved query |

### Example Workflows

**Quick Test Run**:
```bash
python main.py --query "alzheimer's disease" --test
```

**Comprehensive Research**:
```bash
python main.py --query "COVID-19" --terms "treatment" "vaccine" "long COVID" --databases all --save-query
```

**Follow-up Research**:
```bash
python main.py --load-saved --max-results 100
```
![image](https://github.com/user-attachments/assets/26e78749-ee09-4cb9-8542-45ef65e29a4b)

## 📊 Output

The Science Study Scraper generates several types of output:

1. **PDFs**: Downloaded and generated PDFs are stored in the `studies/pdfs` directory
2. **CSV Data**: Detailed study information in CSV format
3. **JSON Data**: Complete study data in JSON format
4. **HTML Report**: Interactive web report with filtering and search capabilities

<img width="1212" alt="image" src="https://github.com/user-attachments/assets/879d7824-6c8d-44dc-8230-bf6ca121a9dd" />

## 📂 Project Structure

```
science_scraper/
├── main.py                  # Main script
├── downloader.py            # Core downloader class
├── requirements.txt         # Required packages
├── database/                # Database-specific modules
│   ├── __init__.py
│   ├── pubmed.py            # PubMed search module
│   ├── pmc.py               # PMC search module
│   └── ...                  # Other database modules
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── pdf_generator.py     # PDF generation utilities
│   └── html_report.py       # HTML report generation
└── studies/                 # Output directory
    └── pdfs/                # Downloaded PDFs
```

## 🛠️ Customization

You can extend the scraper by:

1. Adding new database modules in the `database/` directory
2. Modifying the PDF generation in `utils/pdf_generator.py`
3. Customizing the HTML report in `utils/html_report.py`

## 📝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🔒 Ethical Use Guidelines

This tool is designed for legitimate research purposes only. Please:

- Respect the terms of service of all scientific databases
- Use reasonable request delays to avoid overloading servers
- Only download open access content that you have the right to access
- Use the obtained papers for lawful research purposes

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

This project was made possible thanks to:

- Open-source community - For the libraries and frameworks that form the foundation of this project
- Claude AI 3.7 Sonnet - For assistance with code development, debugging, and documentation
- Scientific publishing platforms - For making research accessible and inspiring this tool
- Friends and colleagues - For your support throughout the development process

---

Created with ❤️ for researchers and scientists worldwide.
