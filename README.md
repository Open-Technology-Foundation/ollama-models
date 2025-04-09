# Ollama Models Toolbox

A collection of tools to extract, filter, and analyze models available for download on Ollama.com. 
This toolbox helps you discover and select appropriate models for your needs based on capabilities, 
parameter size, and popularity.

## Overview

The Ollama Models Toolbox provides tools to:

1. Extract model information from Ollama's model library website
2. Filter models based on various criteria (name, capabilities, parameter size, popularity)
3. Get fully-qualified model names for all matching variants

## Scripts

### ollama-update-models-library

Downloads and cleans the HTML from Ollama's library page to prepare it for parsing:

```bash
ollama-update-models-library
```

**Input:** None (downloads directly from ollama.com/library)  
**Output:** `library-cleaned.html` (cleaned HTML ready for processing)

### ollama-update-models

Extracts model information from the cleaned HTML and creates individual JSON files:

```bash
ollama-update-models
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

# Find top 5 most popular models
ollama-models -p top5

# List all available capabilities
ollama-models -l
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
  "pull_count": "1.2M"          // Number of pulls/downloads
}
```

## Installation

1. Clone this repository
2. Run the installation script:

```bash
./install.sh
```

3. Run the scripts in sequence:

```bash
ollama-update-models-library    # Download and create cleaned HTML
ollama-update-models            # Extract model data
ollama-models                   # Query models as needed
```

## Usage Examples

Find all models with vision capability and parameters under 8 billion:
```bash
ollama-models -c vision -s -8
```

Find top 10 most popular Llama models:
```bash
ollama-models -n llama -p top10
```

List all available models and pipe to grep for filtering:
```bash
ollama-models -a | grep "llama.*7b"
```

## Storage Locations

The scripts use the following directory structure:

- Individual model JSON files: `/usr/local/share/ollama/models/`

If this directory is not writable, the scripts fall back to:

- `~/.local/share/ollama/models/`

## Requirements

- Python 3.6+
- BeautifulSoup4 library (`pip install beautifulsoup4`)
- `html_deltags` command for processing HTML 

## License

[GPL-3.0 License](LICENSE)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.