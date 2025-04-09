# Ollama Models Toolbox (v1.0.0)

A collection of tools to extract, filter, and analyze models available for download on Ollama.com. 
This toolbox helps you discover and select appropriate models for your needs based on capabilities, 
parameter size, and popularity.

> **⚠️ IMPORTANT NOTE ⚠️**  
> These scripts depend on webscraping from the ollama.com/library page to function properly. 
> This approach is used until the Ollama organization provides a more canonical method 
> (such as an API) to access model information. As such, changes to the Ollama website's 
> structure may require updates to these scripts.

## Overview

The Ollama Models Toolbox provides tools to:

1. Extract model information from Ollama's model library website
2. Filter models based on various criteria (name, capabilities, parameter size, popularity, update time)
3. Get fully-qualified model names for all matching variants
4. Sort results based on the last specified filter parameter

## Scripts

### ollama-update-models-library

Downloads and cleans the HTML from Ollama's library page to prepare it for parsing:

```bash
# Default usage
ollama-update-models-library

# Show help
ollama-update-models-library -h

# Show version information
ollama-update-models-library -V
```

**Input:** None (downloads directly from ollama.com/library)  
**Output:** `library-cleaned.html` (cleaned HTML ready for processing)

### ollama-update-models

Extracts model information from the cleaned HTML and creates individual JSON files:

```bash
# Default usage
ollama-update-models

# Show version information
ollama-update-models -V

# Specify custom input file
ollama-update-models -i custom-library.html

# Specify custom output directory
ollama-update-models -o /path/to/custom/models/dir

# Show debug information during processing
ollama-update-models --debug
```

**Input:** `library-cleaned.html`  
**Output:** JSON files for each model in `/usr/local/share/ollama/models/` (or `~/.local/share/ollama/models/`)

### ollama-models

Filters models based on name, capability, parameter size, and/or popularity:

```bash
# List all models (all variants)
ollama-models -a

# Find all llama models
ollama-models -n llama

# Find all vision-capable models
ollama-models -c vision

# Find all models with 7 billion parameters or less
ollama-models -s -7

# Find models between 4 and 28 billion parameters (size range)
ollama-models -s +4 -s -28

# Find top 5 most popular models
ollama-models -p top5

# Find models updated within the last 3 months
ollama-models -u 'since:3 months ago'

# Find models updated before a specific date
ollama-models -u before:2023-06-01

# List all available capabilities
ollama-models -l

# Show version information
ollama-models -V

# Debug size filtering (troubleshooting)
ollama-models -s +12 -s -49 --debug
```

**Input:** Model JSON files  
**Output:** Fully-qualified model names (`model:size`) for matching models

## Data Structure

Each model JSON file contains:

```json
{
  "model": "model-name",        // Model identifier
  "title": "Model Title",       // Display title
  "short_desc": "Description",  // Short description
  "capabilities": [             // Model capabilities (vision, tools, etc)
    "capability1",
    "capability2"
  ],
  "sizes": [                    // Available model sizes (1b, 7b, etc)
    "size1",
    "size2"
  ],
  "pull_count": "1.2M",         // Number of pulls/downloads
  "updated": "2025-03-25 00:12:00", // Standardized timestamp (YYYY-MM-DD HH:MM:SS)
  "updated_relative": "2 weeks ago", // Relative time as shown on website
  "updated_raw": "Mar 25, 2025 12:12 AM UTC", // Raw timestamp from website
  "tag_count": "5 tags"         // Number of tags
}
```

## Installation

1. Clone this repository
2. Run the installation script:

```bash
# Default installation
./install.sh

# Show help
./install.sh -h

# Show version information
./install.sh -V
```

3. Run the scripts in sequence:

```bash
ollama-update-models-library    # Download and create cleaned HTML
ollama-update-models            # Extract model data
ollama-models                   # Query models as needed
```

## Usage Examples

Find all models with vision capability and parameters between 3 and 8 billion:
```bash
ollama-models -c vision -s +3 -s -8
```

Find top 10 most popular Llama models:
```bash
ollama-models -n llama -p top10
```

Find recently updated models with specific capabilities:
```bash
ollama-models -c vision -u 'after:1 month ago'
```

Find models with at least 1 million pulls:
```bash
ollama-models -p +1M
```

Find models with 'coder' in their name and the 'code' capability:
```bash
ollama-models -n coder -c code
```

Find small and efficient models (less than 3B parameters):
```bash
ollama-models -s -3
```

List all available models and pipe to grep for filtering:
```bash
ollama-models -a | grep "llama.*7b"
```

Combine multiple criteria for precise filtering:
```bash
ollama-models -n llama -c chat -s +7 -s -14 -p +500K
```

Sort order is based on the last filter parameter specified:
```bash
# Sort by popularity (most popular first)
ollama-models -n llama -s -15 -p +1M

# Sort by size (smallest first)
ollama-models -n llama -p +1M -s -15
```

## Storage Locations

The scripts use the following directory structure:

- Individual model JSON files: `/usr/local/share/ollama/models/`

If this directory is not writable, the scripts fall back to:

- `~/.local/share/ollama/models/`

## Requirements

- Python 3.6+
- BeautifulSoup4 library (`pip install beautifulsoup4`)
- python-dateutil library (`pip install python-dateutil`)
- `html_deltags` command for processing HTML
  - Available at: https://github.com/Open-Technology-Foundation/html_deltags

## License

[GPL-3.0 License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.