"""
Title: Compress Images
Description: This script compresses images in a specified directory using the Pillow library.
Author: Hsu, Yao-Chih
Version: 1140621
References:
"""

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

ImageFile.LOAD_TRUNCATED_IMAGES = True

image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif', '.avif', '.heic']

def should_skip(filename: str,
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

def is_image(file_path: str) -> bool:
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
    
def backup_image(file_path: str,
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
        return False, '已備份，跳過'

    try:
        shutil.copy2(file_path, backup_path)
        return True, backup_path
    except Exception as e:
        return False, f'備份錯誤: {e}'

def compress_image(file_path: str,
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
        backed_up, backup_status = backup_image(file_path=file_path, backup_folder=backup_folder, original_suffix=original_suffix)
        if not backed_up:
            return (file_path, 0, 0, backup_status, ext_lower, '')

    try:
        size_before = os.path.getsize(file_path)

        with Image.open(file_path) as img:
            img.save(file_path, optimize=True, quality=compress_quality)

        size_after = os.path.getsize(file_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (file_path, size_before, size_after, '成功壓縮', ext_lower, timestamp)

    except Exception as e:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (file_path, 0, 0, f'壓縮錯誤: {e}', ext_lower, timestamp)

def get_all_images(root_path: str,
                   backup_folder: str='original image',
                   original_suffix: str='_original',
                   skip_original: bool=True,
                   skip_skip: bool=True
                   ):
    """
    Recursively get all image files in the specified directory, excluding the backup folder.
    
    Parameters:
        root_path (str): The root directory to search for images.
        backup_folder (str, optional): The folder name to exclude from the search.
        original_suffix (str, optional): The suffix indicating an original file.
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
            if ext in image_extensions and not should_skip(filename=filename, original_suffix=original_suffix, skip_original=skip_original, skip_skip=skip_skip) and is_image(file_path=file_path):
                all_files.append(file_path)
    return all_files

def print_summary_report(results: list,
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
        print('\n📊 壓縮結果報表：')

    for file_path, before, after, status, ext, timestamp in results:
        if before and after:
            savings = before - after
            percent = savings / before * 100
            if print_image_reduced:
                print(f'{file_path}\n  原始大小: {before/1024:.1f} KB → 壓縮後: {after/1024:.1f} KB（減少 {percent:.1f}%）')
            ext_stats[ext]['count'] += 1
            ext_stats[ext]['before'] += before
            ext_stats[ext]['after'] += after
        elif print_image_reduced:
            print(f'{file_path}\n  {status}')

    # 總結輸出
    if print_summary:
        print(f'\n📦 壓縮總結：')
        print(f'⏱️ 壓縮開始時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')}')
        print(f'⏱️ 壓縮結束時間：{end_time.strftime('%Y-%m-%d %H:%M:%S')}')
        print(f'🕒 總耗時：{str(elapsed)}')
        print(f'  總圖片數量：{total_files}')
        if count_success > 0:
            avg_time = elapsed.total_seconds() / count_success
            print(f'📊 平均每張圖片處理時間：{avg_time:.2f} 秒')
        else:
            print('📊 無成功壓縮的圖片，無法計算平均處理時間')
        print(f'    ✔ 成功壓縮：{count_success}')
        print(f'    ⏭ 已備份/跳過：{count_original_backups}')
        print(f'    ⏹ _skip 命名跳過：{count_skipped - count_original_backups}')
        print(f'    ❌ 圖片打開錯誤/非支援：{count_unreadable}')
        print(f'    ⚠ 壓縮錯誤：{count_error}')

        # 空間節省
        print(f'\n  原始總大小: {total_before / 1024 / 1024:.2f} MB')
        print(f'  壓縮後大小: {total_after / 1024 / 1024:.2f} MB')
        if total_before:
            print(f'  節省空間: {(total_before - total_after) / 1024 / 1024:.2f} MB（減少 {((total_before - total_after) / total_before * 100):.1f}%）')

        # 副檔名統計
        print(f'\n📁 各副檔名類型統計：')
        for ext, stats in ext_stats.items():
            before_mb = stats['before'] / 1024 / 1024
            after_mb = stats['after'] / 1024 / 1024
            savings = before_mb - after_mb
            percent = (savings / before_mb * 100) if before_mb > 0 else 0
            print(f'  {ext.upper():<6}：{stats['count']} 張  節省 {savings:.2f} MB（{percent:.1f}%）')

    return ext_stats

def write_csv_report(csv_path: str,
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

        # 第一段：總結統計
        writer.writerow(['開始時間', start_time.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['結束時間', end_time.strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow(['總耗時', str(elapsed)])
        if count_success > 0:
            avg_time = elapsed.total_seconds() / count_success
            writer.writerow(['平均每張圖片處理時間 (秒)', f'{avg_time:.2f}'])
        else:
            writer.writerow(['平均每張圖片處理時間', '無法計算'])

        writer.writerow([])  # 空行分隔區塊

        writer.writerow(['📦 壓縮總結'])
        writer.writerow(['項目', '數值'])
        writer.writerow(['總圖片數量', total_files])
        writer.writerow(['成功壓縮', count_success])
        writer.writerow(['已備份/跳過', count_original_backups])
        writer.writerow(['_skip 命名跳過', count_skipped - count_original_backups])
        writer.writerow(['圖片打開錯誤/非支援', count_unreadable])
        writer.writerow(['壓縮錯誤', count_error])
        writer.writerow(['原始總大小 (MB)', f'{total_before / 1024 / 1024:.2f}'])
        writer.writerow(['壓縮後大小 (MB)', f'{total_after / 1024 / 1024:.2f}'])
        if total_before:
            percent_saved = (total_before - total_after) / total_before * 100
            writer.writerow(['節省空間 (MB)', f'{(total_before - total_after) / 1024 / 1024:.2f}'])
            writer.writerow(['節省百分比 (%)', f'{percent_saved:.1f}'])

        writer.writerow([])  # 空行分隔區塊

        # 第二段：副檔名統計
        writer.writerow(['📁 各副檔名類型統計'])
        writer.writerow(['副檔名', '圖片數量', '原始大小 (MB)', '壓縮後大小 (MB)', '節省空間 (MB)', '節省百分比 (%)'])
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

        writer.writerow([])  # 空行分隔區塊

        # 第三段：每張圖片詳細資料
        writer.writerow(['檔案詳細情況'])
        writer.writerow(['檔案路徑', '副檔名', '原始大小 (KB)', '壓縮後大小 (KB)', '節省百分比 (%)', '狀態', '處理時間'])
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

    print(f'\n📁 壓縮報表已儲存至：{csv_path}')

def process_directory(root_path: str,
                      compress_quality: int = 85,
                      backup: bool = True,
                      backup_folder: str = 'original image',
                      original_suffix: str = '_original',
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
        skip_original (bool, optional): Whether to skip files with `original_suffix` suffix.
        skip_skip (bool, optional): Whether to skip files with `_skip` suffix.
        print_image_reduced (bool, optional): Whether to print reduced image details.
        print_summary (bool, optional): Whether to print the summary report.
        save_summary_to_csv (bool, optional): Whether to save the summary report to a CSV file.

    Returns:
        None
    """
    start_time = datetime.now()

    files = get_all_images(root_path=root_path,
                           backup_folder=backup_folder,
                           original_suffix=original_suffix,
                           skip_original=skip_original,
                           skip_skip=skip_skip
                           )
    total_before, total_after = 0, 0
    results = []

    print(f'共找到 {len(files)} 張圖片，開始處理...\n')

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        task = partial(compress_image, compress_quality=compress_quality, backup=backup, backup_folder=backup_folder)
        futures = {executor.submit(task, f): f for f in files}
        for future in tqdm(as_completed(futures), total=len(futures), desc='壓縮中'):
            file_path, before, after, status, ext, timestamp = future.result()
            results.append((file_path, before, after, status, ext, timestamp))
            if before and after:
                total_before += before
                total_after += after
            tqdm.write(f'{status} - {file_path}')

        
    end_time = datetime.now()

    # 統計分類
    total_files = len(files)
    count_success = sum(1 for r in results if r[3] == '成功壓縮')
    count_skipped = sum(1 for r in results if '跳過' in r[3])
    count_error = sum(1 for r in results if r[3].startswith('錯誤'))
    count_unreadable = sum(1 for r in results if r[5] == '') - count_skipped
    count_original_backups = sum(1 for r in results if r[3] == '已備份，跳過')

    ext_stats = print_summary_report(results=results,
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

    if save_summary_to_csv:
        # 儲存 CSV 報表
        dir_path = os.path.join(root_path, summary_folder)
        os.makedirs(dir_path, exist_ok=True)
        csv_path = os.path.join(root_path, f'{summary_filename}.csv')

        write_csv_report(csv_path=csv_path,
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

def load_config(config_path='config.yaml') -> dict:
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


def compress_images():
    """
    Main function to handle command line arguments and initiate image compression.
    """
    parser = argparse.ArgumentParser(description='圖片壓縮工具')

    # CLI 參數定義（與 config.yaml 對應）
    parser.add_argument('--path')
    parser.add_argument('--compress_quality', type=int)
    parser.add_argument('--backup', type=bool)
    parser.add_argument('--backup_folder')
    parser.add_argument('--original_suffix')
    parser.add_argument('--skip_original', type=bool)
    parser.add_argument('--skip_skip', type=bool)
    parser.add_argument('--print_image_reduced', type=bool)
    parser.add_argument('--print_summary', type=bool)
    parser.add_argument('--save_summary_to_csv', type=bool)
    parser.add_argument('--summary_folder')
    parser.add_argument('--summary_filename')
    parser.add_argument('--config', default='config.yaml')

    args = parser.parse_args()
    config = load_config(args.config)

    # 順序：CLI > config.yaml > 預設值
    def get_param(key, default=None):
        return getattr(args, key) if getattr(args, key) is not None else config.get(key, default)

    # 圖片目錄處理
    target_dir = get_param('path')
    if not target_dir:
        target_dir = input('請輸入要處理的資料夾路徑：').strip()

    if os.path.isdir(target_dir):
        process_directory(
            root_path=target_dir,
            compress_quality=get_param('compress_quality', 85),
            backup=get_param('backup', True),
            backup_folder=get_param('backup_folder', 'original image'),
            original_suffix=get_param('original_suffix', '_original'),
            skip_original=get_param('skip_original', True),
            skip_skip=get_param('skip_skip', True),
            print_image_reduced=get_param('print_image_reduced', True),
            print_summary=get_param('print_summary', True),
            save_summary_to_csv=get_param('save_summary_to_csv', True),
            summary_folder=get_param('summary_folder', 'summary'),
            summary_filename=get_param('summary_filename', 'report'),
        )
        print(f'✅ 資料夾 "{target_dir}" 處理完成！')
    else:
        print('❌ 資料夾不存在，請重新確認路徑。')
    

if __name__ == '__main__':
    compress_images()






