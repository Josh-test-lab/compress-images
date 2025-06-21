"""
Image Compression Tool
=======================

This script compresses all images in a specified directory with optional backup and generates a summary report (CSV and/or console).

Author: Hsu, Yao-Chih
Version: 1140621
License: MIT License
Email: hyc0113@hlc.edu.tw
GitHub: https://github.com/Josh-test-lab/compress-images

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

--author / --email / --license / --status / --github
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
"""

__author__ = "Hsu, Yao-Chih"
__version__ = "1140621"  # YYYYMMDD format
__license__ = "MIT"
__email__ = "hyc0113@hlc.edu.tw"
__status__ = "Development"             # "Production" or "Development"
__description__ = "Image compression script with backup and CSV summary reporting."
__github__ = "https://github.com/Josh-test-lab/compress-images"

# import modules
import os
import shutil
import csv
from datetime import datetime
from PIL import Image, ImageFile
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from collections import defaultdict
from functools import partial
import argparse
import yaml

# global variables
ImageFile.LOAD_TRUNCATED_IMAGES = True
image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif', '.avif', '.heic']

# functions
def compress_images():
    """
    Main function to handle command line arguments and initiate image compression.
    """
    parser = argparse.ArgumentParser(description='Image Compression Tool')

    # CLI argument definitions (corresponding to config.yaml)
    parser.add_argument('--path',               type=str,                                   help='Path to the folder to process')
    parser.add_argument('--compress_quality',   type=int,       default=85,                 help='Compression quality (1-100)')
    parser.add_argument('--backup',             type=str2bool,  default=True,               help='Whether to backup original images')
    parser.add_argument('--backup_folder',      type=str,       default='original image',   help='Folder name for storing backup images')
    parser.add_argument('--original_suffix',    type=str,       default='_original',        help='Suffix for original images')
    parser.add_argument('--skip_suffix',        type=str,       default='_skip',            help='Suffix for images to skip')
    parser.add_argument('--skip_original',      type=str2bool,  default=True,               help='Whether to skip images already backed up')
    parser.add_argument('--skip_skip',          type=str2bool,  default=True,               help='Whether to skip images marked with _skip')
    parser.add_argument('--print_image_reduced',type=str2bool,  default=True,               help='Whether to print information about compressed images')
    parser.add_argument('--print_summary',      type=str2bool,  default=True,               help='Whether to print the compression summary report')
    parser.add_argument('--save_summary_to_csv',type=str2bool,  default=True,               help='Whether to save the summary report as a CSV file')
    parser.add_argument('--summary_folder',     type=str,       default='summary',          help='Folder name for storing summary reports')
    parser.add_argument('--summary_filename',   type=str,       default='report',           help='Filename for summary report (without extension)')
    parser.add_argument('--config',             type=str,       default='config.yaml',      help='Path to configuration YAML file')
    parser.add_argument('--lang_code',          type=str,       default='zh-tw',            help='Language code, e.g., zh-tw, en')

    parser.add_argument('--about',              action='store_true',                        help='Show all author and project info')
    parser.add_argument('--author',             action='store_true',                        help='Show author name only')
    parser.add_argument('--email',              action='store_true',                        help='Show author email only')
    parser.add_argument('--license',            action='store_true',                        help='Show license type only')
    parser.add_argument('--status',             action='store_true',                        help='Show development status only')
    parser.add_argument('--github',             action='store_true',                        help='Show GitHub URL only')
    parser.add_argument('--version',            action='version',                           version=f'%(prog)s {__version__}')

    args = parser.parse_args()
    config = _load_config(args.config)

    if args.about:
        print(f"Author: {__author__}")
        print(f"Email: {__email__}")
        print(f"Version: {__version__}")
        print(f"License: {__license__}")
        print(f"Status: {__status__}")
        print(f"GitHub: {__github__}")
        return
    if args.author:
        print(__author__)
        return
    if args.email:
        print(__email__)
        return
    if args.license:
        print(__license__)
        return
    if args.status:
        print(__status__)
        return
    if args.github:
        print(__github__)
        return

    # CLI > config.yaml > default
    def get_param(key, default=None):
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            return cli_value
        config_value = config.get(key)
        if config_value is not None:
            return config_value
        if key != 'path':
            print(t("general.missing_param").format(key=key, default=default))
        return default

    # global language dictionary
    global LANG_DICT
    LANG_DICT = _load_language(f'language/{get_param('lang_code', 'zh-tw')}.yaml')

    # target directory
    target_dir = get_param('path')
    if not target_dir:
        target_dir = input(t("general.ask_input_path")).strip()

    if os.path.isdir(target_dir):
        _process_directory(
            root_path=target_dir,
            compress_quality=get_param('compress_quality', 85),
            backup=get_param('backup', True),
            backup_folder=get_param('backup_folder', 'original image'),
            original_suffix=get_param('original_suffix', '_original'),
            skip_suffix=get_param('skip_suffix', '_skip'),
            skip_original=get_param('skip_original', True),
            skip_skip=get_param('skip_skip', True),
            print_image_reduced=get_param('print_image_reduced', True),
            print_summary=get_param('print_summary', True),
            save_summary_to_csv=get_param('save_summary_to_csv', True),
            summary_folder=get_param('summary_folder', 'summary'),
            summary_filename=get_param('summary_filename', 'report'),
        )
        print(t("general.finished_processing").format(folder=target_dir))
    else:
        print(t("general.folder_not_found"))

def str2bool(v):
    """
    Convert a string to a boolean value.
    """
    if isinstance(v, bool):
        return v
    if v.lower() in ('yes', 'true', 't', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

def _load_config(config_path='config.yaml') -> dict:
    """
    Load configuration from a YAML file.

    Parameters:
        config_path (str): The path to the configuration file.

    Returns:
        dict: The configuration settings loaded from the file.
    """
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    return {}
    
def _load_language(lang_path: str = 'language/en.yaml') -> dict:
    """
    Load language translation dictionary from YAML file.

    Parameters:
        lang_path (str): Path to the language file.

    Returns:
        dict: Dictionary containing translated text.
    """
    if os.path.exists(lang_path):
        with open(lang_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    print(f'Language file "{lang_path}" not found.')
    return {}

def t(key: str) -> str:
    """
    Fetch translated string from the loaded language dict.
    """
    keys = key.split('.')
    d = LANG_DICT
    for k in keys:
        if isinstance(d, dict) and k in d:
            d = d[k]
        else:
            return key
    return d

def _process_directory(root_path: str,
                      compress_quality: int = 85,
                      backup: bool = True,
                      backup_folder: str = 'original image',
                      original_suffix: str = '_original',
                      skip_suffix: str = '_skip',
                      skip_original: bool = True,
                      skip_skip: bool = True,
                      print_image_reduced: bool = True,
                      print_summary: bool = True,
                      save_summary_to_csv: bool = True,
                      summary_folder: str = 'summary',
                      summary_filename: str = 'report'
                      ) -> None:
    """
    Process all images in the specified directory, compressing them and generating a summary report.

    Parameters:
        root_path (str): The root directory to search for images.
        compress_quality (int, optional): The quality level for compression (1-100).
        backup (bool, optional): Whether to backup the original image before compression.
        backup_folder (str, optional): The folder where backups will be stored.
        original_suffix (str, optional): The suffix to append to the original file name.
        skip_suffix (str, optional): The suffix indicating a skipped file.
        skip_original (bool, optional): Whether to skip files with `original_suffix` suffix.
        skip_skip (bool, optional): Whether to skip files with `_skip` suffix.
        print_image_reduced (bool, optional): Whether to print reduced image details.
        print_summary (bool, optional): Whether to print the summary report.
        save_summary_to_csv (bool, optional): Whether to save the summary report to a CSV file.

    Returns:
        None
    """
    start_time = datetime.now()

    files = _get_all_images(root_path=root_path,
                           backup_folder=backup_folder,
                           original_suffix=original_suffix,
                           skip_suffix=skip_suffix,
                           skip_original=skip_original,
                           skip_skip=skip_skip
                           )
    total_before, total_after = 0, 0
    results = []

    print(t("general.start_processing").format(count=len(files)))

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        task = partial(_compress_image, compress_quality=compress_quality, backup=backup, backup_folder=backup_folder)
        futures = {executor.submit(task, f): f for f in files}
        for future in tqdm(as_completed(futures), total=len(futures), desc=t("general.processing")):
            file_path, before, after, status, ext, timestamp = future.result()
            results.append((file_path, before, after, status, ext, timestamp))
            if before and after:
                total_before += before
                total_after += after
            if print_image_reduced:
                tqdm.write(f'{status} - {file_path}')

        
    end_time = datetime.now()

    # statistics
    total_files = len(files)
    count_success = sum(1 for r in results if r[3] == t("status.compressed"))
    count_skipped = sum(1 for r in results if t("status.skip_keyword") in r[3])
    count_error = sum(1 for r in results if r[3].startswith(t("status.error_keyword")))
    count_unreadable = sum(1 for r in results if r[5] == '') - count_skipped
    count_original_backups = sum(1 for r in results if r[3] == t("status.skipped"))

    # print summary report
    ext_stats = _print_summary_report(results=results,
                                     start_time=start_time,
                                     end_time=end_time,
                                     total_files=total_files,
                                     count_success=count_success,
                                     count_skipped=count_skipped,
                                     count_original_backups=count_original_backups,
                                     count_unreadable=count_unreadable,
                                     count_error=count_error,
                                     total_before=total_before,
                                     total_after=total_after,
                                     print_image_reduced=print_image_reduced,
                                     print_summary=print_summary
                                     )

    # save summary report to CSV
    if save_summary_to_csv:
        dir_path = os.path.join(root_path, summary_folder)
        os.makedirs(dir_path, exist_ok=True)
        csv_path = os.path.join(dir_path, f'{summary_filename}_{end_time.strftime("%Y-%m-%d-%H-%M-%S")}.csv')

        _write_csv_report(csv_path=csv_path,
                        start_time=start_time,
                        end_time=end_time,
                        total_files=total_files,
                        count_success=count_success,
                        count_skipped=count_skipped,
                        count_original_backups=count_original_backups,
                        count_unreadable=count_unreadable,
                        count_error=count_error,
                        total_before=total_before,
                        total_after=total_after,
                        ext_stats=ext_stats,
                        results=results
                        )

def _get_all_images(root_path: str,
                   backup_folder: str='original image',
                   original_suffix: str='_original',
                   skip_suffix: str='_skip',
                   skip_original: bool=True,
                   skip_skip: bool=True
                   ):
    """
    Recursively get all image files in the specified directory, excluding the backup folder.
    
    Parameters:
        root_path (str): The root directory to search for images.
        backup_folder (str, optional): The folder name to exclude from the search.
        original_suffix (str, optional): The suffix indicating an original file.
        skip_suffix (str, optional): The suffix indicating a skipped file.
        skip_original (bool, optional): Whether to skip files with `original_suffix` suffix.
        skip_skip (bool, optional): Whether to skip files with `_skip` suffix.

    Returns:
        list: A list of paths to image files found in the directory.
    """
    all_files = []
    for foldername, _, filenames in os.walk(root_path):
        if os.path.basename(foldername).lower() == backup_folder.lower():
            continue
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions and not _should_skip(filename=filename, original_suffix=original_suffix, skip_suffix=skip_suffix, skip_original=skip_original, skip_skip=skip_skip) and _is_image(file_path=file_path):
                all_files.append(file_path)
    return all_files

def _should_skip(filename: str,
                original_suffix: str='_original',
                skip_suffix: str='_skip',
                skip_original: bool=True,
                skip_skip: bool=True
                ) -> bool:
    """
    Determine whether to skip a file based on its name.

    Parameters:
        filename (str): The name of the file to check.
        original_suffix (str, optional): The suffix indicating an original file.
        skip_suffix (str, optional): The suffix indicating a skipped file.
        skip_original (bool, optional): Whether to skip files with `original_suffix` suffix.
        skip_skip (bool, optional): Whether to skip files with `skip_suffix` suffix.

    Returns:
        bool: True if the file should be skipped, False otherwise.
    """
    name, _ = os.path.splitext(filename)
    if skip_original and name.endswith(original_suffix):
        return True
    elif skip_skip and name.endswith(skip_suffix):
        return True
    return False

def _is_image(file_path: str) -> bool:
    """
    Check if a file is a valid image.

    Parameters:
        file_path (str): The path to the file to check.

    Returns:
        bool: True if the file is a valid image, False otherwise.
    """
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def _compress_image(file_path: str,
                   compress_quality: int = 85,
                   backup: bool = True,
                   backup_folder: str = 'original image',
                   original_suffix: str = '_original'
                   ) -> tuple:
    """
    Compress an image file.

    Parameters:
        file_path (str): The path to the image file to compress.
        compress_quality (int, optional): The quality level for compression (1-100).
        backup (bool, optional): Whether to backup the original image before compression.
        backup_folder (str, optional): The folder where backups will be stored.
        original_suffix (str, optional): The suffix to append to the original file name.

    Returns:
        tuple: A tuple containing the file path, size before compression, size after compression, status message, file extension, and timestamp.
    """
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    if backup:
        backed_up, backup_status = _backup_image(file_path=file_path, backup_folder=backup_folder, original_suffix=original_suffix)
        if not backed_up:
            return (file_path, 0, 0, backup_status, ext_lower, '')

    try:
        size_before = os.path.getsize(file_path)

        with Image.open(file_path) as img:
            img.save(file_path, optimize=True, quality=compress_quality)

        size_after = os.path.getsize(file_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (file_path, size_before, size_after, t("status.compressed"), ext_lower, timestamp)

    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (file_path, 0, 0, t("status.compress_error").format(error=e), ext_lower, timestamp)
    
def _backup_image(file_path: str,
                 backup_folder: str = 'original image',
                 original_suffix: str = '_original'
                 ) -> tuple[bool, str]:
    """
    Backup the original image before compression.

    Parameters:
        file_path (str): The path to the image file to backup.
        backup_folder (str, optional): The folder where backups will be stored.
        original_suffix (str, optional): The suffix to append to the original file name.

    Returns:
        tuple: A tuple containing a boolean indicating success or failure, and a message or backup path.
    """
    foldername = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)

    backup_dir = os.path.join(foldername, backup_folder)
    os.makedirs(backup_dir, exist_ok=True)

    backup_path = os.path.join(backup_dir, f'{name}{original_suffix}{ext}')
    if os.path.exists(backup_path):
        return False, t('status.skipped')

    try:
        shutil.copy2(file_path, backup_path)
        return True, backup_path
    except Exception as e:
        return False, t("status.backup_error").format(error=e)
    
def _print_summary_report(results: list,
                         start_time: datetime,
                         end_time: datetime,
                         total_files: int,
                         count_success: int,
                         count_skipped: int,
                         count_original_backups: int,
                         count_unreadable: int,
                         count_error: int,
                         total_before: int,
                         total_after: int,
                         print_image_reduced: bool = True,
                         print_summary: bool = True
                         ) -> dict:
    """
    Print a summary report of the compression results.

    Parameters:
        results (list): List of tuples containing file paths, sizes before and after compression, status messages, file extensions, and timestamps.
        start_time (datetime): The start time of the compression process.
        end_time (datetime): The end time of the compression process.
        total_files (int): Total number of files processed.
        count_success (int): Count of successfully compressed images.
        count_skipped (int): Count of skipped images.
        count_original_backups (int): Count of images that were backed up and skipped.
        count_unreadable (int): Count of unreadable or unsupported images.
        count_error (int): Count of images that encountered errors during compression.
        total_before (int): Total size of images before compression.
        total_after (int): Total size of images after compression.
        print_image_reduced (bool): Whether to print reduced image details.
        print_summary (bool): Whether to print the summary report.

    Returns:
        dict: A dictionary containing statistics by file extension.
    """
    elapsed = end_time - start_time
    ext_stats = defaultdict(lambda: {'count': 0, 'before': 0, 'after': 0})

    if print_image_reduced:
        print('\n' + t("report.header_result"))

    for file_path, before, after, status, ext, timestamp in results:
        if before and after:
            savings = before - after
            percent = savings / before * 100
            if print_image_reduced:
                print(f'{file_path}\n  ' + t("report.size_before").format(mb=before/1024) + 
                      f' → ' + t("report.size_after").format(mb=after/1024) + 
                      f'(' + t("report.size_saved").format(mb=(before - after)/1024, percent=percent) + ')')
            ext_stats[ext]['count'] += 1
            ext_stats[ext]['before'] += before
            ext_stats[ext]['after'] += after
        elif print_image_reduced:
            print(f'{file_path}\n  {status}')

    if print_summary:
        print('\n' + t("report.header_summary"))
        print(t("report.start_time").format(time=start_time.strftime('%Y-%m-%d %H:%M:%S')))
        print(t("report.end_time").format(time=end_time.strftime('%Y-%m-%d %H:%M:%S')))
        print(t("report.elapsed").format(elapsed=str(elapsed)))
        print(t("report.total_images").format(count=total_files))
        if count_success > 0:
            avg_time = elapsed.total_seconds() / count_success
            print(t("report.avg_time").format(seconds=avg_time))
        else:
            print(t("report.no_avg_time"))
        print(t("report.compressed_success").format(count=count_success))
        print(t("report.skipped_backup").format(count=count_original_backups))
        print(t("report.skipped_named").format(count=count_skipped - count_original_backups))
        print(t("report.error_unreadable").format(count=count_unreadable))
        print(t("report.error_failed").format(count=count_error))
        print(t("report.size_before").format(mb=total_before / 1024 / 1024))
        print(t("report.size_after").format(mb=total_after / 1024 / 1024))
        if total_before:
            print(t("report.size_saved").format(mb=(total_before - total_after) / 1024 / 1024,
                                                percent=((total_before - total_after) / total_before * 100)
                                                ))

        print('\n' + t("report.header_ext_summary"))
        for ext, stats in ext_stats.items():
            before_mb = stats['before'] / 1024 / 1024
            after_mb = stats['after'] / 1024 / 1024
            savings = before_mb - after_mb
            percent = (savings / before_mb * 100) if before_mb > 0 else 0
            print(t("report.ext_format").format(ext=ext.upper(),
                                                count=stats["count"],
                                                savings=before_mb - after_mb,
                                                percent=percent
                                                ))

    return ext_stats

def _write_csv_report(csv_path: str,
                     start_time: datetime,
                     end_time: datetime,
                     total_files: int,
                     count_success: int,
                     count_skipped: int,
                     count_original_backups: int,
                     count_unreadable: int,
                     count_error: int,
                     total_before: int,
                     total_after: int,
                     ext_stats: dict,
                     results: list
                     ) -> None:
    """
    Write a summary report to a CSV file.

    Parameters:
        csv_path (str): The path to the CSV file to write the report.
        start_time (datetime): The start time of the compression process.
        end_time (datetime): The end time of the compression process.
        total_files (int): Total number of files processed.
        count_success (int): Count of successfully compressed images.
        count_skipped (int): Count of skipped images.
        count_original_backups (int): Count of images that were backed up and skipped.
        count_unreadable (int): Count of unreadable or unsupported images.
        count_error (int): Count of images that encountered errors during compression.
        total_before (int): Total size of images before compression.
        total_after (int): Total size of images after compression.
        ext_stats (dict): Statistics by file extension.
        results (list): List of tuples containing file paths, sizes before and after compression, status messages, file extensions, and timestamps.

    Returns:
        None
    """
    elapsed = end_time - start_time

    with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # first part: general info
        writer.writerow([t("csv.fields.start_time"), start_time.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([t("csv.fields.end_time"), end_time.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([t("csv.fields.elapsed"), str(elapsed)])
        if count_success > 0:
            avg_time = elapsed.total_seconds() / count_success
            writer.writerow([t("csv.fields.avg_time"), f'{avg_time:.2f}'])
        else:
            writer.writerow([t("csv.fields.avg_time_unavailable"), t("csv.fields.avg_time_cannot_calculate")])
        writer.writerow([])

        writer.writerow([t("csv.section_general")])
        writer.writerow([t("csv.fields.key"), t("csv.fields.value")])
        writer.writerow([t("csv.fields.total_images"), total_files])
        writer.writerow([t("csv.fields.compressed"), count_success])
        writer.writerow([t("csv.fields.skipped_backup"), count_original_backups])
        writer.writerow([t("csv.fields.skipped_named"), count_skipped - count_original_backups])
        writer.writerow([t("csv.fields.unreadable"), count_unreadable])
        writer.writerow([t("csv.fields.errors"), count_error])
        writer.writerow([t("csv.fields.size_before"), f'{total_before / 1024 / 1024:.2f}'])
        writer.writerow([t("csv.fields.size_after"), f'{total_after / 1024 / 1024:.2f}'])
        if total_before:
            percent_saved = (total_before - total_after) / total_before * 100
            writer.writerow([t("csv.fields.size_saved"), f'{(total_before - total_after) / 1024 / 1024:.2f}'])
            writer.writerow([t("csv.fields.size_percent"), f'{percent_saved:.1f}'])
        writer.writerow([])

        # section: extension summary
        writer.writerow([t("csv.section_ext")])
        writer.writerow([t("csv.fields.ext"),
                         t("csv.fields.ext_count"),
                         t("csv.fields.ext_before"),
                         t("csv.fields.ext_after"),
                         t("csv.fields.ext_saved"),
                         t("csv.fields.ext_percent")
                        ])

        for ext, stats in ext_stats.items():
            before_mb = stats['before'] / 1024 / 1024
            after_mb = stats['after'] / 1024 / 1024
            savings = before_mb - after_mb
            percent = (savings / before_mb * 100) if before_mb > 0 else 0
            writer.writerow([
                ext.upper(),
                stats['count'],
                f'{before_mb:.2f}',
                f'{after_mb:.2f}',
                f'{savings:.2f}',
                f'{percent:.1f}'
            ])
        writer.writerow([])

        # third part: detailed results
        writer.writerow([t("csv.section_detail")])
        writer.writerow([t("csv.fields.detail_path"),
                         t("csv.fields.detail_ext"),
                         t("csv.fields.detail_before"),
                         t("csv.fields.detail_after"),
                         t("csv.fields.detail_percent"),
                         t("csv.fields.detail_status"),
                         t("csv.fields.detail_time")
                        ])
        for file_path, before, after, status, ext, timestamp in results:
            if before and after:
                percent = (before - after) / before * 100
                writer.writerow([
                    file_path,
                    ext,
                    f'{before / 1024:.1f}',
                    f'{after / 1024:.1f}',
                    f'{percent:.1f}',
                    status,
                    timestamp
                ])
            else:
                writer.writerow([file_path, ext, '', '', '', status, timestamp])

    print(t("general.saved_report").format(path=csv_path))
    

# main programs
if __name__ == '__main__':
    compress_images()






