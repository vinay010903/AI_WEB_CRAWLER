# AI Web Crawler - Refactored Architecture

This is a modular AI-driven web crawler specifically designed for Amazon automation with intelligent selector discovery.

## Architecture Overview

The codebase has been refactored into specialized modules for better maintainability and separation of concerns:

### 📁 Module Structure

#### 1. `main.py` - Entry Point
- **Purpose**: Main application entry point
- **Dependencies**: `pipeline_orchestrator`
- **Size**: ~20 lines (significantly reduced from 1600+ lines)

#### 2. `ai_communicator.py` - AI Communication Layer
- **Purpose**: Handles all AI/LLM communications for selector discovery
- **Key Functions**:
  - `ask_local_ai_for_specific_selectors()` - Batched AI queries with fallback
  - `find_username_selectors()`, `find_password_selectors()`, etc. - Groq LLM calls
- **Dependencies**: `httpx`, `groq`, `json`
- **Size**: ~500 lines

#### 3. `web_automator.py` - Web Automation Engine
- **Purpose**: Playwright-based web automation and data extraction
- **Key Functions**:
  - `go_to_login()`, `perform_username_entry()`, `perform_password_entry()` - Form automation
  - `extract_product_links()`, `navigate_to_review_page()` - Navigation
  - `extract_all_reviews()`, `process_products_and_reviews()` - Data extraction
- **Dependencies**: `playwright`, `asyncio`, `json`
- **Size**: ~600 lines

#### 4. `selector_processor.py` - Selector Processing
- **Purpose**: HTML parsing and selector organization
- **Key Functions**:
  - `extract_selectors()` - BeautifulSoup-based HTML parsing
  - `group_selectors_by_category()` - Selector categorization
- **Dependencies**: `beautifulsoup4`, `json`
- **Size**: ~150 lines

#### 5. `pipeline_orchestrator.py` - Main Pipeline Logic
- **Purpose**: Orchestrates the complete AI-driven automation pipeline
- **Key Functions**:
  - `run_ai_pipeline_navigator()` - Main AI-driven pipeline (uses pre-existing grouped selectors)
  - `run_pipeline()` - Alternative pipeline with live selector extraction
- **Dependencies**: All other modules, `playwright`
- **Size**: ~400 lines

## 🚀 Usage

### Quick Start
```bash
cd src/
python3 main.py
```

### Pipeline Options

#### Option 1: AI Pipeline Navigator (Default)
Uses pre-existing categorized selectors for faster execution:
```python
model = "qwen/qwen3-4b-2507"
asyncio.run(run_ai_pipeline_navigator(model))
```

#### Option 2: Traditional Pipeline
Extracts selectors live during execution:
```python
asyncio.run(run_pipeline())
```

## 🔧 Configuration

### Environment Variables
```bash
GROQ_API_KEY=your_groq_api_key
AMAZON_USERNAME=your_amazon_email
AMAZON_PASSWORD=your_amazon_password
LOCAL_AI_MODEL=your_local_model_name  # Optional
```

### Model Configuration
- **Local AI Models**: Requires LM Studio running on `localhost:1234`
- **Groq Models**: Used for traditional pipeline selector discovery
- **Supported Models**: qwen/qwen3-4b-2507, openai/gpt-4o-mini, etc.

## 📊 Data Flow

```
main.py
    ↓
pipeline_orchestrator.py
    ├── ai_communicator.py (AI queries)
    ├── web_automator.py (Browser automation)
    └── selector_processor.py (HTML parsing)
```

## 🧪 Benefits of Refactoring

### Before Refactoring
- **Single file**: 1600+ lines in main.py
- **Mixed concerns**: AI, web automation, and data processing in one place
- **Hard to maintain**: Difficult to modify individual components
- **15+ unused files**: Cluttered codebase

### After Refactoring
- **Modular design**: 5 focused modules with clear responsibilities  
- **Separation of concerns**: Each module handles specific functionality
- **Easy maintenance**: Individual modules can be updated independently
- **Clean codebase**: Removed all unnecessary files (15 files deleted)
- **Better testing**: Each module can be tested in isolation

## 🔍 Key Features

- **Intelligent Selector Discovery**: Uses AI to find optimal web selectors
- **Batch Processing**: Handles large selector sets efficiently
- **Fault Tolerance**: Multiple fallback strategies for selector failure
- **Review Extraction**: Automated product review collection with pagination
- **Modular Architecture**: Easy to extend and maintain

## 🎯 Main Pipeline Flow

1. **Load Grouped Selectors** (pre-categorized)
2. **AI Selector Selection** (batched queries to local AI)
3. **Amazon Login Automation** (username → password flow)
4. **Product Search & Extraction**
5. **Review Page Navigation**
6. **Multi-page Review Extraction**
7. **Structured Data Export**

This refactored architecture provides a clean, maintainable, and scalable foundation for AI-driven web automation.