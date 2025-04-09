#!/usr/bin/env python3
"""
ollama-models - Filter and search Ollama models based on various criteria

Version: 1.0.0

This script allows searching through Ollama models based on:
- Model name
- Capabilities/features
- Parameter size
- Popularity (download count)
- Update time (when the model was last updated)

Results are printed as fully-qualified model names (e.g., llama3:8b) 
for all variants that match the criteria. The output is sorted based on
the last filter parameter specified on the command line.

Usage:
  ollama-models [options]

Options:
  -n, --name NAME          Filter by model name substring (case-insensitive)
  -c, --capability CAP     Filter by capability (e.g., vision, tools, embedding)
  -s, --size SIZE          Filter by parameter size (n, +n for >=n, -n for <=n) in billions
                           Can be specified multiple times to create a range
  -p, --popularity POP     Filter by popularity: top<n> for top n models,
                           +<pulls> for >= pulls, -<pulls> for <= pulls
  -u, --updated DATE       Filter by update time: since:DATE, after:DATE, before:DATE, 
                           until:DATE, or on:DATE. DATE can be an absolute date (2023-01-15) 
                           or a relative time ('3 months ago'). Quote arguments with spaces.
  -d, --models_dir DIR     Directory containing model JSON files
                           (defaults to system or user directory)
  -l, --list-capabilities  List all available capabilities
  --long                   Display results in long format (tabular view with more details)
  --update                 Update model data and exit (standalone command)
  -a, --all                List all models (all variants)
  -V, --version            Show version information
  --debug                  Show debug information about the filtering process
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
  
  # Find models with size between 4B and 28B parameters
  ollama-models --size +4 --size -28
  
  # Find vision-capable models between 3B and 8B parameters
  ollama-models --capability vision --size +3 --size -8
  
  # Show debug information (useful for troubleshooting)
  ollama-models --size +12 --size -49 --debug
  
  # Find models updated within the last 3 months
  ollama-models --updated 'since:3 months ago'
  
  # Find models updated before a specific date
  ollama-models --updated before:2023-06-01
  
  # Find recently updated models with vision capability
  ollama-models --capability vision --updated 'after:1 month ago'
  
  # Display results in a detailed tabular format
  ollama-models --name llama --long
  
  # Update model data (standalone command)
  ollama-models --update
"""
import json
import os
import re
import argparse
import sys
import datetime
import subprocess
import dateutil.parser
import dateutil.relativedelta

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

def size_matches_filter(size_str, size_filter, debug=False):
    """
    Check if a size matches the filter criteria
    
    Args:
        size_str: Size string (e.g. '7b')
        size_filter: Filter string (e.g. '7', '+7', '-7')
        debug: Whether to print debug information
        
    Returns:
        bool: True if size matches filter, False otherwise
    """
    if not size_filter:
        return True
        
    size_value = parse_size(size_str)
    if size_value is None:
        if debug:
            print(f"DEBUG: Could not parse size '{size_str}'", file=sys.stderr)
        return False
        
    if debug:
        print(f"DEBUG: Comparing size {size_str} ({size_value}B) with filter {size_filter}", file=sys.stderr)
        
    if size_filter.startswith('+'):
        # Greater than or equal to
        filter_value = float(size_filter[1:])
        result = size_value >= filter_value
        if debug:
            print(f"DEBUG:   {size_value} >= {filter_value}: {result}", file=sys.stderr)
        return result
    elif size_filter.startswith('-'):
        # Less than or equal to
        filter_value = float(size_filter[1:])
        result = size_value <= filter_value
        if debug:
            print(f"DEBUG:   {size_value} <= {filter_value}: {result}", file=sys.stderr)
        return result
    else:
        # Exact match
        filter_value = float(size_filter)
        result = size_value == filter_value
        if debug:
            print(f"DEBUG:   {size_value} == {filter_value}: {result}", file=sys.stderr)
        return result

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

def parse_date_string(date_str, debug=False):
    """
    Parse a date string in various formats, including relative times
    
    Args:
        date_str: Date string in various formats (e.g. '2023-01-15', '3 months ago')
        debug: Whether to print debug information
        
    Returns:
        datetime.datetime: Parsed datetime object, or None if parsing fails
    """
    if not date_str:
        return None
        
    now = datetime.datetime.now()
    
    try:
        # First try to parse as an absolute date
        return dateutil.parser.parse(date_str)
    except (ValueError, TypeError):
        # If that fails, try to parse as a relative date
        pass
    
    # Parse relative date strings (e.g. "3 months ago")
    relative_pattern = re.match(r'(\d+)\s+(day|days|week|weeks|month|months|year|years)\s+ago', date_str.lower())
    if relative_pattern:
        number, unit = relative_pattern.groups()
        number = int(number)
        
        # Create the appropriate relativedelta
        if unit in ('day', 'days'):
            delta = dateutil.relativedelta.relativedelta(days=number)
        elif unit in ('week', 'weeks'):
            delta = dateutil.relativedelta.relativedelta(weeks=number)
        elif unit in ('month', 'months'):
            delta = dateutil.relativedelta.relativedelta(months=number)
        elif unit in ('year', 'years'):
            delta = dateutil.relativedelta.relativedelta(years=number)
        else:
            if debug:
                print(f"DEBUG: Unrecognized time unit: {unit}", file=sys.stderr)
            return None
            
        # Subtract the delta from now
        return now - delta
    
    if debug:
        print(f"DEBUG: Could not parse date string: {date_str}", file=sys.stderr)
    return None

def date_matches_filter(updated_date, date_filter, debug=False):
    """
    Check if an updated date matches the date filter criteria
    
    Args:
        updated_date: Date string (e.g. '2023-01-15', timestamp format)
        date_filter: Filter string (e.g. 'since:2023-01-01', 'newer:3 months ago')
        debug: Whether to print debug information
        
    Returns:
        bool: True if date matches filter, False otherwise
    """
    if not date_filter or not updated_date:
        return True
        
    try:
        # Parse the updated date
        model_date = dateutil.parser.parse(updated_date)
        
        if debug:
            print(f"DEBUG: Parsed model date: {model_date}", file=sys.stderr)
        
        # Handle 'since:' and 'after:' prefix (newer than the specified date)
        if date_filter.startswith(('since:', 'after:')):
            filter_date_str = date_filter.split(':', 1)[1]
            filter_date = parse_date_string(filter_date_str, debug)
            
            if filter_date and model_date:
                result = model_date >= filter_date
                if debug:
                    print(f"DEBUG: Checking if {model_date} >= {filter_date}: {result}", file=sys.stderr)
                return result
                
        # Handle 'before:' and 'until:' prefix (older than the specified date)
        elif date_filter.startswith(('before:', 'until:')):
            filter_date_str = date_filter.split(':', 1)[1]
            filter_date = parse_date_string(filter_date_str, debug)
            
            if filter_date and model_date:
                result = model_date <= filter_date
                if debug:
                    print(f"DEBUG: Checking if {model_date} <= {filter_date}: {result}", file=sys.stderr)
                return result
                
        # Handle 'on:' prefix (on the specified date)
        elif date_filter.startswith('on:'):
            filter_date_str = date_filter.split(':', 1)[1]
            filter_date = parse_date_string(filter_date_str, debug)
            
            if filter_date and model_date:
                # Compare just the date parts (ignore time)
                result = (model_date.year == filter_date.year and 
                         model_date.month == filter_date.month and 
                         model_date.day == filter_date.day)
                if debug:
                    print(f"DEBUG: Checking if {model_date.date()} == {filter_date.date()}: {result}", file=sys.stderr)
                return result
                
        # If no prefix, assume 'since:' (newer than the specified date)
        else:
            filter_date = parse_date_string(date_filter, debug)
            
            if filter_date and model_date:
                result = model_date >= filter_date
                if debug:
                    print(f"DEBUG: Checking if {model_date} >= {filter_date}: {result}", file=sys.stderr)
                return result
    
    except (ValueError, TypeError) as e:
        if debug:
            print(f"DEBUG: Error comparing dates: {e}", file=sys.stderr)
        
    # Default to True if we can't parse the dates or filters
    return True


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

def determine_sort_order(arg_order, args):
    """
    Determine the sort order based on the last specified filter parameter
    
    Args:
        arg_order: List of argument names in the order they were specified on the command line
        args: The parsed arguments
        
    Returns:
        tuple: (sort_key_function, reverse_flag)
    """
    # Default sort order: by model name, ascending
    default_sort = (lambda x: x['model'].lower(), False)
    
    # Check the arguments in reverse order (to find the last specified one)
    for arg_name in reversed(arg_order):
        if arg_name == 'popularity' and args.popularity:
            # Sort by popularity, highest first
            if args.popularity.startswith('top'):
                return (lambda x: parse_pull_count(x.get('pull_count', '0')), True)
            else:
                return (lambda x: parse_pull_count(x.get('pull_count', '0')), True)
        elif arg_name == 'size' and args.size:
            # Sort by average size, smallest first
            return (lambda x: sum(parse_size(s) for s in x.get('sizes', ['0b']) if parse_size(s) is not None) / 
                           max(1, len([s for s in x.get('sizes', ['0b']) if parse_size(s) is not None])), 
                   False)
        elif arg_name == 'updated' and args.updated:
            # Sort by update date, most recent first
            return (lambda x: dateutil.parser.parse(x.get('updated', '1970-01-01 00:00:00')) 
                           if 'updated' in x and x['updated'] else datetime.datetime(1970, 1, 1), 
                   True)
        elif arg_name == 'capability' and args.capability:
            # Sort by whether it has the capability, then by model name
            capability = args.capability.lower()
            return (lambda x: (
                any(capability in cap.lower() for cap in x.get('capabilities', [])),
                x['model'].lower()
            ), True)
        elif arg_name == 'name' and args.name:
            # Sort by name, with matching name patterns first
            name_pattern = args.name.lower()
            return (lambda x: (
                name_pattern not in x['model'].lower(),  # False (match) comes before True (no match)
                x['model'].lower()
            ), False)
    
    # If no recognized sort parameters, use default sort
    return default_sort


def format_table(models, sizes_only=False):
    """
    Format models data into a tabular view
    
    Args:
        models: List of model dictionaries
        sizes_only: If True, create separate entries for each size variant
        
    Returns:
        str: Formatted table as a string
    """
    # Define column headers and widths
    headers = ["Model", "Size", "Pop.", "Update", "Capabilities"]
    widths = [25, 29, 8, 18, 17]  # Adjusted per requirements: Size +6, Pop -2, Update -2, Capabilities -3
    
    # Prepare data rows
    rows = []
    for model in models:
        name = model['model']
        
        # Handle sizes
        if sizes_only and 'matched_sizes' in model:
            # When showing individual sizes as separate rows
            sizes = model['matched_sizes']
        elif sizes_only and 'sizes' in model:
            # When showing individual sizes as separate rows
            sizes = model['sizes']
        elif 'sizes' in model and model['sizes']:
            # Always show all sizes, let the column width handle truncation
            sizes = [', '.join(model['sizes'])]
        else:
            sizes = ['']
            
        for size in sizes:
            # Format the full model identifier
            if size and sizes_only:
                model_id = f"{name}:{size}"
            else:
                model_id = name
                
            # Format the popularity count
            popularity = model.get('pull_count', '')
            
            # Format the update time (use relative time if available)
            if 'updated_relative' in model:
                update_time = model.get('updated_relative', '')
            else:
                update_time = model.get('updated', '')
            
            # Format capabilities - show all and let the column handle truncation
            caps = model.get('capabilities', [])
            capabilities = ', '.join(caps)
            
            # Add the row
            rows.append([model_id, size if sizes_only else sizes[0], popularity, update_time, capabilities])
    
    # Truncate or pad each column to fit the width
    formatted_rows = []
    
    # Add header row
    header_row = ""
    for i, header in enumerate(headers):
        header_row += header.ljust(widths[i]) + " | "
    formatted_rows.append(header_row)
    
    # Add separator row
    separator = ""
    for width in widths:
        separator += "-" * width + "-+-"
    formatted_rows.append(separator)
    
    # Add data rows
    for row in rows:
        formatted_row = ""
        for i, cell in enumerate(row):
            # Truncate if longer than width - 1 and add ellipsis character
            if len(cell) > widths[i] - 1:
                cell = cell[:widths[i] - 1] + "…"
            formatted_row += cell.ljust(widths[i]) + " | "
        formatted_rows.append(formatted_row)
    
    # Join all rows with newlines
    return "\n".join(formatted_rows)


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
    parser.add_argument('-s', '--size', action='append',
            help='Filter by parameter size (n, +n for >=n, -n for <=n) in billions, can be specified multiple times for a range')
    parser.add_argument('-p', '--popularity',
            help='Filter by popularity: top<n> for top n models, +<pulls> for >= pulls, -<pulls> for <= pulls')
    parser.add_argument('-u', '--updated',
            help="Filter by update time (e.g., since:2023-01-15, 'after:3 months ago', before:2023-05-01). Use quotes for dates with spaces.")
    parser.add_argument('-d', '--models_dir',
            help='Directory containing model JSON files (defaults to system or user directory)')
    parser.add_argument('-l', '--list-capabilities', action='store_true',
            help='List all available capabilities')
    parser.add_argument('--long', action='store_true',
            help='Display results in long format (tabular view with more details)')
    parser.add_argument('--update', action='store_true',
            help='Update model data and exit (runs ollama-update-models-library and ollama-update-models)')
    parser.add_argument('-a', '--all', action='store_true',
            help='List all models (all variants)')
    parser.add_argument('-V', '--version', action='store_true',
            help='Show version information')
    parser.add_argument('--debug', action='store_true',
            help='Show debug information about the filtering process')
    
    args = parser.parse_args()
    
    # Check if update is requested - treat it as a standalone subcommand
    if args.update:
        try:
            print("Updating Ollama model data...")
            print("Running: ollama-update-models-library")
            subprocess.run(["ollama-update-models-library"], check=True)
            print("Running: ollama-update-models")
            subprocess.run(["ollama-update-models"], check=True)
            print("Update completed successfully.")
            sys.exit(0)  # Exit after update is complete
        except subprocess.SubprocessError as e:
            print(f"Error during update: {e}")
            sys.exit(1)  # Exit with error code on failure
    
    # Get the models directory
    models_dir = args.models_dir if args.models_dir else get_models_dir()
    
    # Track argument order for determining sort order
    arg_order = []
    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith('-'):
            arg_name = arg.lstrip('-').split('=')[0]  # Handle both '--name value' and '--name=value'
            # Convert short options to long options
            if arg_name == 'n': arg_name = 'name'
            elif arg_name == 'c': arg_name = 'capability'
            elif arg_name == 's': arg_name = 'size'
            elif arg_name == 'p': arg_name = 'popularity'
            elif arg_name == 'u': arg_name = 'updated'
            arg_order.append(arg_name)
    
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
    if not (args.name or args.capability or args.size or args.popularity or args.updated or args.all):
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
        
        # Check update time filter
        update_match = True
        if args.updated and name_match and capability_match and popularity_match:
            if 'updated' in model_data:
                update_match = date_matches_filter(model_data['updated'], args.updated, args.debug)
            elif args.debug:
                print(f"DEBUG: Model {model_data['model']} has no 'updated' field", file=sys.stderr)
        
        # If basic filters match, add to results (size filtering happens during output)
        if name_match and capability_match and popularity_match and update_match:
            # Store matched sizes if size filter specified
            if args.size:
                matched_sizes = []
                for size in model_data.get('sizes', []):
                    # Check if size matches ALL of the provided size filters
                    matches_all_filters = True
                    for size_filter in args.size:
                        if not size_matches_filter(size, size_filter, args.debug):
                            matches_all_filters = False
                            break
                    
                    if matches_all_filters:
                        if args.debug:
                            print(f"DEBUG: Model {model_data['model']} size {size} matches all filters", file=sys.stderr)
                        matched_sizes.append(size)
                    elif args.debug:
                        print(f"DEBUG: Model {model_data['model']} size {size} does not match all filters", file=sys.stderr)
                
                # Only add if at least one size matches
                if matched_sizes:
                    model_data['matched_sizes'] = matched_sizes
                    matches.append(model_data)
            else:
                # No size filter, add all
                matches.append(model_data)
    
    # Handle top-n popularity filter first (to limit results)
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
    
    # Apply sort based on the last specified filter
    if matches:
        sort_key, reverse = determine_sort_order(arg_order, args)
        try:
            if args.debug:
                print(f"DEBUG: Sorting based on last specified filter: {arg_order[-1] if arg_order else 'default'}", file=sys.stderr)
            matches.sort(key=sort_key, reverse=reverse)
        except Exception as e:
            if args.debug:
                print(f"DEBUG: Error during sorting: {e}", file=sys.stderr)
    
    # Print results
    if not matches:
        print("No models found matching the specified criteria.", file=sys.stderr)
        sys.exit(1)
    
    # Check if long format is requested
    if args.long:
        # Print tabular output
        print(format_table(matches, sizes_only=bool(args.size)))
    else:
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
