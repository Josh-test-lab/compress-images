# compress-images

Image Compression Tool
=======================

This script compresses all images in a specified directory with optional backup and generates a summary report (CSV and/or console).

- Author: Hsu, Yao-Chih
- Version: v.1140621
- License: MIT License
- Email: hyc0113@hlc.edu.tw
- GitHub: https://github.com/Josh-test-lab/compress-images
- Website: https://yao-chih.netlify.app/en/image-compression-tools
- Python Version: 3.12.9 for Windows

------------------------
Command Line Arguments:
------------------------

--path PATH
    Path to the folder to process. If omitted, the program will ask for input.

--compress_quality INT (default: 85)
    Compression quality (1–100). Higher means better quality but larger file.

--backup BOOL (default: True)
    Whether to backup the original images before compressing.

--backup_folder STR (default: 'original image')
    Name of the folder to store original image backups.

--original_suffix STR (default: '_original')
    Suffix for original backup image files.

--skip_suffix STR (default: '_skip')
    Images with this suffix in filename will be skipped.

--skip_original BOOL (default: True)
    Skip images that already have the original suffix.

--skip_skip BOOL (default: True)
    Skip images that already have the skip suffix.

--print_image_reduced BOOL (default: True)
    Print individual image compression results.

--print_summary BOOL (default: True)
    Print a summary of the compression.

--save_summary_to_csv BOOL (default: True)
    Save a CSV report of the compression results.

--summary_folder STR (default: 'summary')
    Folder to store the summary report CSV.

--summary_filename STR (default: 'report')
    Base name for the CSV report file.

--config STR (default: 'config.yaml')
    Path to a YAML configuration file.

--lang_code STR (default: 'zh-tw')
    Language code for translation, e.g., 'en', 'zh-tw'.

--version
    Print script version and exit.

--about
    Print author, version, license, email, and GitHub info.

--author / --license / --status / --github
    Individually print each specific metadata field.

------------------------
Usage Examples:
------------------------

Compress with default settings:
    python compress_images.py --path images/

Use config.yaml and suppress per-image output:
    python compress_images.py --config my_config.yaml --print_image_reduced False

Show author info:
    python compress_images.py --author

Print help:
    python compress_images.py --help
