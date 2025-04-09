#!/usr/bin/env python3
"""
ollama-models - Filter and search Ollama models based on various criteria

Version: 1.0.0

This script allows searching through Ollama models based on:
- Model name
- Capabilities/features
- Parameter size
- Popularity (download count)

Results are printed as fully-qualified model names (e.g., llama3:8b) 
for all variants that match the criteria.

Usage:
  ollama-models [options]

Options:
  -n, --name NAME          Filter by model name substring (case-insensitive)
  -c, --capability CAP     Filter by capability (e.g., vision, tools, embedding)
  -s, --size SIZE          Filter by parameter size (n, +n for >=n, -n for <=n) in billions
  -p, --popularity POP     Filter by popularity: top<n> for top n models,
                           +<pulls> for >= pulls, -<pulls> for <= pulls
  -d, --models_dir DIR     Directory containing model JSON files
                           (defaults to system or user directory)
  -l, --list-capabilities  List all available capabilities
  -a, --all                List all models (all variants)
  -V, --version            Show version information
  --help                   Show this help message

Examples:
  # List all models (all variants)
  ollama-models --all
  
  # Find all llama models
  ollama-models --name llama
  
  # Find all vision-capable models
  ollama-models --capability vision
  
  # Find all models with 7 billion parameters or less
  ollama-models --size -7
  
  # Find llama models with tools capability and 10B parameters or less
  ollama-models --name llama --capability tools --size -10
  
  # Find top 5 most popular models
  ollama-models --popularity top5
"""
import json
import os
import re
import argparse
import sys

def get_models_dir():
    """
    Get the canonical models directory with fallback to user directory
    
    Returns:
        str: Path to the models directory
    """
    # System-wide location
    system_dir = '/usr/local/share/ollama/models'
    
    if os.path.isdir(system_dir) and os.access(system_dir, os.R_OK):
        return system_dir
    
    # Fall back to user directory if system dir isn't accessible
    user_dir = os.path.expanduser('~/.local/share/ollama/models')
    
    if os.path.isdir(user_dir):
        return user_dir
    
    print(f"Error: Neither system ({system_dir}) nor user ({user_dir}) models directory exists", file=sys.stderr)
    sys.exit(1)

def parse_size(size_str):
    """
    Convert a model size string like '7b' to a numeric value in billions
    
    Args:
        size_str: Size string (e.g. '7b', '500m')
        
    Returns:
        float: Size in billions of parameters, or None if not parseable
    """
    match = re.match(r'(\d+\.?\d*)([a-zA-Z]+)', size_str)
    if not match:
        return None
        
    value, unit = match.groups()
    value = float(value)
    
    # Apply multiplier based on unit
    if unit.lower() == 'b':
        return value
    elif unit.lower() == 'm':
        return value / 1000.0
    elif unit.lower() == 'k':
        return value / 1_000_000.0
    else:
        return value

def size_matches_filter(size_str, size_filter):
    """
    Check if a size matches the filter criteria
    
    Args:
        size_str: Size string (e.g. '7b')
        size_filter: Filter string (e.g. '7', '+7', '-7')
        
    Returns:
        bool: True if size matches filter, False otherwise
    """
    if not size_filter:
        return True
        
    size_value = parse_size(size_str)
    if size_value is None:
        return False
        
    if size_filter.startswith('+'):
        # Greater than or equal to
        filter_value = float(size_filter[1:])
        return size_value >= filter_value
    elif size_filter.startswith('-'):
        # Less than or equal to
        filter_value = float(size_filter[1:])
        return size_value <= filter_value
    else:
        # Exact match
        filter_value = float(size_filter)
        return size_value == filter_value

def parse_pull_count(pull_count):
    """
    Convert a pull count string like '3.3M' to a numeric value
    
    Args:
        pull_count: Pull count string (e.g. '3.3M', '500K')
        
    Returns:
        float: Numeric pull count
    """
    if not pull_count:
        return 0
        
    # Extract the numeric part and convert to float
    match = re.match(r'([\d.]+)([KMB]?)', pull_count)
    if not match:
        return 0
        
    num, unit = match.groups()
    value = float(num)
    
    # Apply multiplier based on unit
    if unit == 'K':
        value *= 1_000
    elif unit == 'M':
        value *= 1_000_000
    elif unit == 'B':
        value *= 1_000_000_000
        
    return value

def popularity_matches_filter(pull_count, popularity_filter):
    """
    Check if a pull count matches the popularity criteria
    
    Args:
        pull_count: Pull count string (e.g. '3.3M')
        popularity_filter: Filter string (e.g. 'top5', '+1M', '-500K')
        
    Returns:
        bool: True if pull count matches filter, False otherwise
    """
    if not popularity_filter:
        return True
        
    numeric_pull_count = parse_pull_count(pull_count)
    
    if popularity_filter.startswith('top'):
        # Nothing to check here, will be handled later via sorting
        return True
    elif popularity_filter.startswith('+'):
        # Greater than or equal to specified pull count
        filter_value = parse_pull_count(popularity_filter[1:])
        return numeric_pull_count >= filter_value
    elif popularity_filter.startswith('-'):
        # Less than or equal to specified pull count
        filter_value = parse_pull_count(popularity_filter[1:])
        return numeric_pull_count <= filter_value
    else:
        # Try parsing as a number of pulls
        try:
            filter_value = parse_pull_count(popularity_filter)
            return numeric_pull_count == filter_value
        except ValueError:
            # If not a valid number format, return False
            return False

def main():
    """Main function to parse arguments and filter models"""
    parser = argparse.ArgumentParser(
        description='Filter Ollama models based on name, capability, size, and popularity',
        epilog=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument('-n', '--name',
            help='Filter by model name (case-insensitive substring match)')
    parser.add_argument('-c', '--capability',
            help='Filter by capability (e.g., vision, tools, embedding)')
    parser.add_argument('-s', '--size',
            help='Filter by parameter size (n, +n for >=n, -n for <=n) in billions')
    parser.add_argument('-p', '--popularity',
            help='Filter by popularity: top<n> for top n models, +<pulls> for >= pulls, -<pulls> for <= pulls')
    parser.add_argument('-d', '--models_dir',
            help='Directory containing model JSON files (defaults to system or user directory)')
    parser.add_argument('-l', '--list-capabilities', action='store_true',
            help='List all available capabilities')
    parser.add_argument('-a', '--all', action='store_true',
            help='List all models (all variants)')
    parser.add_argument('-V', '--version', action='store_true',
            help='Show version information')
    
    args = parser.parse_args()
    
    # Get the models directory
    models_dir = args.models_dir if args.models_dir else get_models_dir()
    
    # Check if the directory exists and contains model files
    if not os.path.isdir(models_dir):
        print(f"Error: Models directory {models_dir} does not exist.", file=sys.stderr)
        print("Run ollama-update-models first to generate model files.", file=sys.stderr)
        sys.exit(1)
    
    # Get list of model files
    model_files = [f for f in os.listdir(models_dir) if f.endswith('.json')]
    
    if not model_files:
        print(f"Error: No model files found in {models_dir}.", file=sys.stderr)
        print("Run ollama-update-models first to generate model files.", file=sys.stderr)
        sys.exit(1)
    
    # If list-capabilities flag is used, show all unique capabilities and exit
    if args.list_capabilities:
        unique_capabilities = set()
        for filename in model_files:
            filepath = os.path.join(models_dir, filename)
            with open(filepath, 'r') as f:
                model_data = json.load(f)
                for cap in model_data.get('capabilities', []):
                    unique_capabilities.add(cap)
        
        print("Available capabilities:")
        for cap in sorted(unique_capabilities):
            print(f"  {cap}")
        sys.exit(0)
    
    # Show version if requested
    if args.version:
        print("Ollama Models Toolbox v1.0.0")
        sys.exit(0)
        
    # Check if at least one filter is specified (or --all flag)
    if not (args.name or args.capability or args.size or args.popularity or args.all):
        parser.print_help()
        sys.exit(1)
    
    # Process each model
    matches = []
    for filename in model_files:
        filepath = os.path.join(models_dir, filename)
        with open(filepath, 'r') as f:
            model_data = json.load(f)
        
        # If --all flag is specified, include all models
        if args.all:
            matches.append(model_data)
            continue
        
        # Check name filter (if specified)
        name_match = True
        if args.name:
            name_match = args.name.lower() in model_data['model'].lower()
        
        # Check capability filter (if specified)
        capability_match = True
        if args.capability and name_match:
            capability_match = False
            for cap in model_data.get('capabilities', []):
                if args.capability.lower() in cap.lower():
                    capability_match = True
                    break
        
        # For size filter, we'll handle it during output
        
        # Check popularity filter (if not top-n format)
        popularity_match = True
        if args.popularity and name_match and capability_match:
            if not args.popularity.startswith('top'):
                popularity_match = popularity_matches_filter(model_data.get('pull_count', '0'), args.popularity)
        
        # If basic filters match, add to results (size filtering happens during output)
        if name_match and capability_match and popularity_match:
            # Store matched sizes if size filter specified
            if args.size:
                matched_sizes = []
                for size in model_data.get('sizes', []):
                    if size_matches_filter(size, args.size):
                        matched_sizes.append(size)
                
                # Only add if at least one size matches
                if matched_sizes:
                    model_data['matched_sizes'] = matched_sizes
                    matches.append(model_data)
            else:
                # No size filter, add all
                matches.append(model_data)
    
    # Handle top-n popularity filter
    if args.popularity and args.popularity.startswith('top'):
        try:
            top_n = int(args.popularity[3:])  # Extract the number after 'top'
            # Sort by pull count (descending)
            matches.sort(key=lambda x: parse_pull_count(x.get('pull_count', '0')), reverse=True)
            # Limit to top n
            matches = matches[:top_n]
        except ValueError:
            print(f"Invalid top-n format: {args.popularity}. Should be like 'top5'.", file=sys.stderr)
            sys.exit(1)
    
    # Print results
    if not matches:
        print("No models found matching the specified criteria.", file=sys.stderr)
        sys.exit(1)
    
    # Output format: modelname:size for each variant    
    for model in matches:
        model_name = model['model']
        
        # If model has no sizes, just print the model name
        if not model.get('sizes', []):
            print(model_name)
            continue
            
        # If size filter was specified, use the matched sizes
        if args.size and 'matched_sizes' in model:
            sizes = model['matched_sizes']
        else:
            sizes = model.get('sizes', [])
            
        # Print each model variant
        for size in sizes:
            print(f"{model_name}:{size}")

if __name__ == "__main__":
    main()

#fin
