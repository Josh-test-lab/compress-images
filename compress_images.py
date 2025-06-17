"""
Title: Compress Images
Description: This script compresses images in a specified directory using the Pillow library.
Author: Hsu, Yao-Chih
Version: 1140617
References:
"""

import os
import shutil
import csv
import time
from datetime import datetime
from PIL import Image, ImageFile
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from collections import defaultdict

ImageFile.LOAD_TRUNCATED_IMAGES = True

image_extensions = ['.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff', '.gif', '.avif', '.heic']

def should_skip(filename):
    name, _ = os.path.splitext(filename)
    return name.endswith('_original') or name.endswith('_skip')

def is_image(file_path):
    try:
        with Image.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def compress_image(file_path):
    foldername = os.path.dirname(file_path)
    filename = os.path.basename(file_path)
    name, ext = os.path.splitext(filename)
    ext_lower = ext.lower()

    original_dir = os.path.join(foldername, "original image")
    os.makedirs(original_dir, exist_ok=True)
    backup_path = os.path.join(original_dir, f"{name}_original{ext}")

    if os.path.exists(backup_path):
        return (file_path, 0, 0, "已備份，跳過", ext_lower, "")

    start_time = time.time()

    try:
        shutil.copy2(file_path, backup_path)
        size_before = os.path.getsize(file_path)

        with Image.open(file_path) as img:
            img.save(file_path, optimize=True, quality=85)

        size_after = os.path.getsize(file_path)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return (file_path, size_before, size_after, "成功壓縮", ext_lower, timestamp)

    except Exception as e:
        return (file_path, 0, 0, f"錯誤: {e}", ext_lower, "")

def get_all_images(root_path):
    all_files = []
    for foldername, _, filenames in os.walk(root_path):
        if os.path.basename(foldername).lower() == "original image":
            continue
        for filename in filenames:
            file_path = os.path.join(foldername, filename)
            ext = os.path.splitext(filename)[1].lower()
            if ext in image_extensions and not should_skip(filename) and is_image(file_path):
                all_files.append(file_path)
    return all_files

def process_directory(root_path):
    start_time = datetime.now()


    files = get_all_images(root_path)
    total_before, total_after = 0, 0
    results = []

    print(f"共找到 {len(files)} 張圖片，開始處理...\n")

    with ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
        futures = {executor.submit(compress_image, f): f for f in files}
        for future in tqdm(as_completed(futures), total=len(futures), desc="壓縮中"):
            file_path, before, after, status, ext, timestamp = future.result()
            results.append((file_path, before, after, status, ext, timestamp))
            if before and after:
                total_before += before
                total_after += after
            tqdm.write(f"{status} - {file_path}")

        
    end_time = datetime.now()
    elapsed = end_time - start_time


    print("\n📊 壓縮結果報表：")
    ext_stats = defaultdict(lambda: {"count": 0, "before": 0, "after": 0})

    for file_path, before, after, status, ext, timestamp in results:
        if before and after:
            savings = before - after
            percent = savings / before * 100
            print(f"{file_path}\n  原始大小: {before/1024:.1f} KB → 壓縮後: {after/1024:.1f} KB（減少 {percent:.1f}%）")
            ext_stats[ext]["count"] += 1
            ext_stats[ext]["before"] += before
            ext_stats[ext]["after"] += after
        else:
            print(f"{file_path}\n  {status}")

    # 圖片分類統計
    total_files = len(files)
    count_success = sum(1 for r in results if r[3] == "成功壓縮")
    count_skipped = sum(1 for r in results if "跳過" in r[3])
    count_error = sum(1 for r in results if r[3].startswith("錯誤"))
    count_unreadable = sum(1 for r in results if r[5] == "") - count_skipped
    count_original_backups = sum(1 for r in results if r[3] == "已備份，跳過")

    print(f"\n📦 壓縮總結：")
    print(f"⏱️ 壓縮開始時間：{start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"⏱️ 壓縮結束時間：{end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🕒 總耗時：{str(elapsed)}")
    print(f"  總圖片數量：{total_files}")
    if count_success > 0:
        avg_time = elapsed.total_seconds() / count_success
        print(f"📊 平均每張圖片處理時間：{avg_time:.2f} 秒")
    else:
        print("📊 無成功壓縮的圖片，無法計算平均處理時間")
    print(f"    ✔ 成功壓縮：{count_success}")
    print(f"    ⏭ 已備份/跳過：{count_original_backups}")
    print(f"    ⏹ _skip 命名跳過：{count_skipped - count_original_backups}")
    print(f"    ❌ 圖片打開錯誤/非支援：{count_unreadable}")
    print(f"    ⚠ 壓縮錯誤：{count_error}")

    print(f"\n  原始總大小: {total_before / 1024 / 1024:.2f} MB")
    print(f"  壓縮後大小: {total_after / 1024 / 1024:.2f} MB")
    if total_before:
        print(f"  節省空間: {(total_before - total_after) / 1024 / 1024:.2f} MB（減少 {((total_before - total_after) / total_before * 100):.1f}%）")

    # 副檔名類型統計
    print(f"\n📁 各副檔名類型統計：")
    for ext, stats in ext_stats.items():
        before_mb = stats["before"] / 1024 / 1024
        after_mb = stats["after"] / 1024 / 1024
        savings = before_mb - after_mb
        percent = (savings / before_mb * 100) if before_mb > 0 else 0
        print(f"  {ext.upper():<6}：{stats['count']} 張  節省 {savings:.2f} MB（{percent:.1f}%）")


    # ➕ 輸出 CSV 報表
    csv_path = os.path.join(root_path, "壓縮報表.csv")
    with open(csv_path, mode='w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        # 第一段：總結統計
        writer.writerow(["開始時間", start_time.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["結束時間", end_time.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["總耗時", str(elapsed)])
        if count_success > 0:
            avg_time = elapsed.total_seconds() / count_success
            writer.writerow(["平均每張圖片處理時間 (秒)", f"{avg_time:.2f}"])
        else:
            writer.writerow(["平均每張圖片處理時間", "無法計算"])

        writer.writerow([])  # 空行分隔區塊

        writer.writerow(["📦 壓縮總結"])
        writer.writerow(["項目", "數值"])
        writer.writerow(["總圖片數量", total_files])
        writer.writerow(["成功壓縮", count_success])
        writer.writerow(["已備份/跳過", count_original_backups])
        writer.writerow(["_skip 命名跳過", count_skipped - count_original_backups])
        writer.writerow(["圖片打開錯誤/非支援", count_unreadable])
        writer.writerow(["壓縮錯誤", count_error])
        writer.writerow(["原始總大小 (MB)", f"{total_before / 1024 / 1024:.2f}"])
        writer.writerow(["壓縮後大小 (MB)", f"{total_after / 1024 / 1024:.2f}"])
        if total_before:
            percent_saved = (total_before - total_after) / total_before * 100
            writer.writerow(["節省空間 (MB)", f"{(total_before - total_after) / 1024 / 1024:.2f}"])
            writer.writerow(["節省百分比 (%)", f"{percent_saved:.1f}"])

        writer.writerow([])  # 空行分隔區塊

        # 第二段：副檔名統計
        writer.writerow(["📁 各副檔名類型統計"])
        writer.writerow(["副檔名", "圖片數量", "原始大小 (MB)", "壓縮後大小 (MB)", "節省空間 (MB)", "節省百分比 (%)"])
        for ext, stats in ext_stats.items():
            before_mb = stats["before"] / 1024 / 1024
            after_mb = stats["after"] / 1024 / 1024
            savings = before_mb - after_mb
            percent = (savings / before_mb * 100) if before_mb > 0 else 0
            writer.writerow([
                ext.upper(),
                stats["count"],
                f"{before_mb:.2f}",
                f"{after_mb:.2f}",
                f"{savings:.2f}",
                f"{percent:.1f}"
            ])
        
        writer.writerow([])  # 空行分隔區塊

        # 第三段：每張圖片詳細資料
        writer.writerow(["檔案詳細情況"])
        writer.writerow(["檔案路徑", "副檔名", "原始大小 (KB)", "壓縮後大小 (KB)", "節省百分比 (%)", "狀態", "處理時間"])
        for file_path, before, after, status, ext, timestamp in results:
            if before and after:
                percent = (before - after) / before * 100
                writer.writerow([
                    file_path,
                    ext,
                    f"{before / 1024:.1f}",
                    f"{after / 1024:.1f}",
                    f"{percent:.1f}",
                    status,
                    timestamp
                ])
            else:
                writer.writerow([file_path, ext, "", "", "", status, timestamp])



    print(f"\n📁 壓縮報表已儲存至：{csv_path}")


if __name__ == "__main__":
    target_dir = input("請輸入要處理的資料夾路徑：").strip()
    if os.path.isdir(target_dir):
        process_directory(target_dir)
        print(f"資料夾 '{target_dir}' 處理完成！")
    else:
        print("資料夾不存在，請重新確認路徑。")

