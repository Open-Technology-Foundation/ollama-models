#!/usr/bin/env python3
"""
ollama-update-models - Extract model information from Ollama's library page

Version: 1.0.0

This script extracts model information from the cleaned HTML of Ollama's library page
and creates individual JSON files for each model with their attributes.

Usage:
  ollama-update-models [options]

Options:
  -i, --input FILE       Input HTML file path (default: library-cleaned.html)
  -o, --output-dir DIR   Output directory for model JSON files
                         (default: /usr/local/share/ollama/models or ~/.local/share/ollama/models)
  -V, --version          Show version information
  --debug                Show debug information during processing
  -h, --help             Show this help message

Input:
  library-cleaned.html - The cleaned HTML file from Ollama's library page

Output:
  Creates model JSON files in the models directory (default: /usr/local/share/ollama/models)
  Each JSON file contains: model name, title, description, capabilities, sizes, pull count,
  updated timestamp, and tag count

Dependencies:
  - BeautifulSoup4 library for HTML parsing
  
Prerequisites:
  - Run ollama-update-models-library first to download and clean the HTML file
"""
import json
import os
import re
import sys
import argparse
import datetime
from bs4 import BeautifulSoup

def get_models_dir():
    """
    Get the canonical models directory with fallback to user directory
    
    Returns:
        str: Path to the models directory
    """
    # System-wide location
    system_dir = '/usr/local/share/ollama/models'
    
    if os.path.isdir(system_dir) and os.access(system_dir, os.W_OK):
        return system_dir
    
    # Fall back to user directory if system dir isn't accessible
    user_dir = os.path.expanduser('~/.local/share/ollama/models')
    os.makedirs(user_dir, exist_ok=True)
    
    print(f"Warning: System models directory not writable, using {user_dir}", file=sys.stderr)
    return user_dir

# Constants
INPUT_FILE = 'library-cleaned.html'
OUTPUT_DIR = get_models_dir()

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

def extract_models(debug=False):
    """
    Extract model data from the HTML file and save as JSON files
    
    Args:
        debug: Whether to show debug information
    """
    # Read the input file
    try:
        with open(INPUT_FILE, 'r') as f:
            html_content = f.read()
    except FileNotFoundError:
        print(f"Error: {INPUT_FILE} not found. Run ollama-update-models-library first.", file=sys.stderr)
        sys.exit(1)
    
    # Parse the HTML
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Find all model items
    model_items = soup.select('li[x-test-model]')
    
    # Process each model
    for model_item in model_items:
        # Initialize model data
        model_data = {}
        
        # Extract model name from the URL
        model_link = model_item.find('a')
        if model_link and 'href' in model_link.attrs:
            model_name = model_link['href'].split('/')[-1]
            model_data['model'] = model_name
        else:
            # Skip if we can't find the model name
            continue
        
        # Find the title element (span with group-hover:underline class inside h2)
        title_span = model_item.select_one('h2 span.group-hover\\:underline')
        if title_span:
            model_data['title'] = title_span.text.strip()
        
        # Find the description paragraph element
        desc_elem = model_item.select_one('div.flex.flex-col[title] + p')
        if desc_elem:
            model_data['short_desc'] = desc_elem.text.strip()
        
        # Extract capabilities
        capabilities = []
        for span in model_item.select('span[x-test-capability]'):
            capability = span.text.strip()
            if capability and capability not in capabilities:
                capabilities.append(capability)
        model_data['capabilities'] = capabilities
        
        # Extract sizes
        sizes = []
        for span in model_item.select('span[x-test-size]'):
            size_text = span.text.strip()
            if size_text and size_text not in sizes:
                sizes.append(size_text)
        model_data['sizes'] = sizes
        
        # Extract pull count
        pull_count_span = model_item.select_one('span[x-test-pull-count]')
        if pull_count_span:
            model_data['pull_count'] = pull_count_span.text.strip()
        
        # Extract updated time
        updated_span = model_item.select_one('span[x-test-updated]')
        if updated_span:
            # Store the relative time as displayed on the page
            model_data['updated_relative'] = updated_span.text.strip()
            
            # Find the parent span with the exact timestamp in the title attribute
            parent_span = updated_span.find_parent('span', attrs={'title': True})
            if parent_span and 'title' in parent_span.attrs:
                # Extract the raw timestamp from title attribute
                raw_timestamp = parent_span['title']
                model_data['updated_raw'] = raw_timestamp
                
                # Convert to standardized format (YYYY-MM-DD HH:MM:SS)
                try:
                    # Parse the date format "Mar 25, 2025 12:12 AM UTC"
                    dt = datetime.datetime.strptime(raw_timestamp, "%b %d, %Y %I:%M %p UTC")
                    # Format as YYYY-MM-DD HH:MM:SS
                    model_data['updated'] = dt.strftime("%Y-%m-%d %H:%M:%S")
                except (ValueError, TypeError) as e:
                    # If parsing fails, just store the raw value
                    model_data['updated'] = raw_timestamp
                    if debug:
                        print(f"Warning: Could not parse timestamp '{raw_timestamp}' for model {model_data['model']}: {e}", file=sys.stderr)
        
        # Extract tag count
        tag_count_span = model_item.select_one('span[x-test-tag-count]')
        if tag_count_span:
            model_data['tag_count'] = tag_count_span.text.strip()
        
        # Create filename using model name
        filename = f"{OUTPUT_DIR}/{model_data['model']}.json"
        
        # Write to JSON file
        with open(filename, 'w') as f:
            json.dump(model_data, f, indent=2)
        
        print(f"Extracted model: {model_data['model']}")
    
    print(f"Extracted {len(model_items)} models to {OUTPUT_DIR}/")
    return model_items

def main():
    global INPUT_FILE, OUTPUT_DIR
    
    parser = argparse.ArgumentParser(
        description='Extract model information from Ollama\'s library page',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-V', '--version', action='store_true',
            help='Show version information')
    parser.add_argument('-i', '--input', default=INPUT_FILE,
            help=f'Input HTML file path (default: {INPUT_FILE})')
    parser.add_argument('-o', '--output-dir',
            help=f'Output directory for model JSON files (default: {OUTPUT_DIR})')
    parser.add_argument('--debug', action='store_true',
            help='Show debug information during processing')
    
    args = parser.parse_args()
    
    # Show version if requested
    if args.version:
        print("Ollama Models Toolbox v1.0.0")
        sys.exit(0)
    
    # Override constants if specified in args
    if args.input:
        INPUT_FILE = args.input
    if args.output_dir:
        OUTPUT_DIR = args.output_dir
        # Create output directory if it doesn't exist
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    extract_models(args.debug)

if __name__ == "__main__":
    main()

#fin