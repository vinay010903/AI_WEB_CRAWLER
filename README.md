# Selector Categorizer

An intelligent CSS selector categorization system that uses Groq AI to automatically classify extracted web selectors into predefined categories for better organization and analysis.

## Overview

The `selector_categorizer.py` module provides an automated way to categorize CSS selectors extracted from websites into meaningful categories. It uses Groq's LLaMA-3.1-8B model to intelligently analyze selectors and classify them based on their purpose and functionality.

## Features

- **AI-Powered Categorization**: Uses Groq AI for intelligent selector classification
- **6 Predefined Categories**: Organizes selectors into meaningful business categories
- **Fallback System**: Rule-based categorization when AI is unavailable
- **Batch Processing**: Process multiple selector files simultaneously
- **Detailed Output**: Comprehensive categorization results with confidence scores
- **Error Handling**: Robust error handling with fallback mechanisms

## Categories

The system categorizes selectors into these 6 categories:

1. **Navigation & Layout** (`navigation_layout`)
   - Navigation menus, headers, footers, breadcrumbs, page structure elements

2. **Authentication & User Account** (`authentication_account`)
   - Login, registration, user profile, account settings, authentication forms

3. **Search & Filters** (`search_filters`)
   - Search bars, filter options, sorting controls, search results

4. **Category & Product Listing Pages** (`category_listing`)
   - Product lists, category pages, pagination, product cards, listing controls

5. **Product Details** (`product_details`)
   - Product pages, specifications, reviews, ratings, add to cart, product images

6. **Support & Miscellaneous** (`support_misc`)
   - Help, contact, customer service, notifications, alerts, other elements

## Installation

### Prerequisites

1. Python 3.7+
2. Groq API key
3. Required dependencies:

```bash
pip install groq python-dotenv
```

### Environment Setup

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key_here
```

## Usage

### Command Line Interface

#### Single File Processing
```bash
python selector_categorizer.py path/to/selector_file.json
```

#### Batch Directory Processing
```bash
python selector_categorizer.py --batch path/to/selectors/directory/
```

#### Direct Directory Processing
```bash
python selector_categorizer.py path/to/selectors/directory/
```

### Python API

#### Basic Usage
```python
from selector_categorizer import SelectorCategorizer

# Initialize categorizer
categorizer = SelectorCategorizer()

# Process single file
result = categorizer.process_selector_file("selectors.json")

# Batch process directory
results = categorizer.batch_categorize_selectors("./selectors/")
```

#### Advanced Usage
```python
# Load selector data
with open("selectors.json", "r") as f:
    selectors = json.load(f)

# Categorize with AI
categorized = categorizer.categorize_selectors_with_groq(selectors)

# Print summary
categorizer.print_categorization_summary([result])
```

## Input Format

The system expects selector files in this JSON format:

```json
{
    "id_selectors": [
        {
            "uuid": "unique-id",
            "selector": "#main-nav",
            "tag": "nav",
            "text_content": "Main Navigation"
        }
    ],
    "class_selectors": [
        {
            "uuid": "unique-id",
            "selector": ".product-card",
            "tag": "div",
            "text_content": "Product information"
        }
    ],
    "input_selectors": [
        {
            "uuid": "unique-id",
            "selector": "input[type='search']",
            "tag": "input",
            "type": "search",
            "name": "q",
            "placeholder": "Search products..."
        }
    ],
    "statistics": {
        "url": "https://example.com",
        "total_elements": 150
    }
}
```

## Output Format

The categorizer generates comprehensive output files:

```json
{
    "metadata": {
        "original_file": "selectors.json",
        "categorization_timestamp": "2024-01-15T10:30:00",
        "original_url": "https://example.com",
        "total_original_selectors": {
            "id_selectors": 25,
            "class_selectors": 45,
            "input_selectors": 12
        }
    },
    "categories": {
        "navigation_layout": {
            "name": "Navigation & Layout",
            "description": "Navigation menus, headers, footers..."
        }
    },
    "categorized_selectors": {
        "navigation_layout": [
            {
                "selector": "#main-nav",
                "confidence": 0.95,
                "reason": "Main navigation element"
            }
        ],
        "product_details": [
            {
                "selector": ".product-price",
                "confidence": 0.88,
                "reason": "Product pricing information"
            }
        ]
    },
    "categorization_summary": {
        "total_categorized": 82,
        "category_counts": {
            "navigation_layout": 15,
            "product_details": 25,
            "search_filters": 8
        },
        "average_confidence": 0.87
    },
    "original_selectors": {
        // Original selector data preserved
    }
}
```

## Core Classes and Methods

### SelectorCategorizer Class

#### `__init__()`
Initializes the categorizer with Groq client using API key from environment variables.

#### `create_categorization_prompt(selectors: Dict) -> str`
Creates detailed prompts for Groq AI with:
- Selector samples from all types
- Category definitions and instructions
- JSON output format specification
- Context from website URL and statistics

#### `categorize_selectors_with_groq(selectors: Dict) -> Dict`
Main AI categorization method:
- Calls Groq API with LLaMA-3.1-8B model
- Uses low temperature (0.1) for consistent results
- Handles JSON parsing and cleanup
- Falls back to rule-based categorization on errors

#### `create_fallback_categorization(selectors: Dict) -> Dict`
Rule-based fallback system:
- Keyword matching for categories
- Confidence scoring based on match quality
- Default categorization for unmatched selectors

#### `process_selector_file(file_path: str, output_path: str = None) -> Dict`
Complete file processing workflow:
- Loads selector JSON file
- Performs AI categorization
- Generates enhanced output with metadata
- Saves categorized results
- Returns processing summary

#### `batch_categorize_selectors(directory: str) -> List[Dict]`
Batch processing capabilities:
- Processes all JSON files in directory
- Includes API rate limiting (2-second delays)
- Returns results for all processed files

#### `print_categorization_summary(results: List[Dict])`
Comprehensive reporting:
- Success/failure statistics
- Category distribution analysis
- Per-file categorization summaries
- Overall batch processing results

## Error Handling

The system includes comprehensive error handling:

- **API Failures**: Falls back to rule-based categorization
- **JSON Parsing Errors**: Cleans response and retries parsing
- **File I/O Errors**: Detailed error reporting with file paths
- **Missing Environment Variables**: Clear error messages
- **Invalid Input Data**: Graceful handling with informative messages

## AI Integration

### Groq API Configuration
- **Model**: LLaMA-3.1-8B-instant
- **Temperature**: 0.1 (low for consistency)
- **Max Tokens**: 4000
- **Timeout**: 60 seconds

### Prompt Engineering
The system uses sophisticated prompt engineering:
- Clear category definitions with examples
- Structured JSON output format
- Context from website URL and statistics
- Confidence scoring requirements
- Detailed analysis instructions

## Performance Considerations

- **Rate Limiting**: 2-second delays between API calls
- **Token Management**: Limits selector samples to 50 items
- **Batch Processing**: Processes multiple files with progress tracking
- **Memory Efficiency**: Streams large JSON files
- **Fallback System**: Ensures operation even without AI access

## File Organization

```
project/
├── src/
│   ├── selector_categorizer.py     # Main categorizer module
│   ├── test_extract_selector.py    # Selector extraction
│   └── main.py                     # Main pipeline
├── extracted_data/
│   ├── selectors/                  # Input selector files
│   └── categorized_selectors/      # Output categorized files
├── .env                            # Environment variables
└── README.md                       # This documentation
```

## Integration with Main Pipeline

The categorizer integrates with the main web scraping pipeline:

1. **Selector Extraction**: `test_extract_selector.py` extracts selectors
2. **Categorization**: `selector_categorizer.py` categorizes them
3. **Action Processing**: Categorized selectors inform action strategies
4. **Analysis**: Structured categories enable better analysis

## Examples

### Example 1: E-commerce Site Categorization
```bash
python selector_categorizer.py selectors/amazon_selectors.json
```

Output categories might include:
- Navigation: Menu items, breadcrumbs
- Search: Search bar, filters, sort options
- Product Listing: Product cards, pagination
- Product Details: Price, reviews, add to cart
- Authentication: Login, account links

### Example 2: Batch Processing
```bash
python selector_categorizer.py --batch ./extracted_data/selectors/
```

Processes all JSON files and generates summary report showing category distribution across all sites.

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   ❌ GROQ_API_KEY not found in environment variables
   ```
   Solution: Add your Groq API key to `.env` file

2. **JSON Parsing Errors**
   ```
   ❌ JSON parsing error: Invalid JSON response
   ```
   Solution: System automatically falls back to rule-based categorization

3. **File Not Found**
   ```
   ❌ File or directory not found: path/to/file.json
   ```
   Solution: Verify file paths and permissions

4. **API Rate Limits**
   ```
   ❌ Groq API error: Rate limit exceeded
   ```
   Solution: System includes automatic delays; wait and retry

### Debug Mode

For detailed debugging, modify the script to include verbose logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Contributing

To contribute to the selector categorizer:

1. Follow existing code patterns and documentation
2. Add comprehensive error handling
3. Include unit tests for new features
4. Update this README for any new functionality
5. Ensure compatibility with existing pipeline components

## License

This project is part of the AI Web Crawler system. See project license for details.