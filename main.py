import os
import re
from datetime import datetime
import filedate
import shutil
import uuid
import string
import time
from pathlib import Path

# Define patterns for date extraction from filenames - with full datetime support
DATE_PATTERNS = [
    # Pattern: IMG20230710162352.jpg (IMG + YYYYMMDDHHMMSS)
    re.compile(r'^IMG(\d{14})\.\w+$', re.IGNORECASE),
    # Pattern: VID20240731092916.mp4 (VID + YYYYMMDDHHMMSS)
    re.compile(r'^VID(\d{14})\.\w+$', re.IGNORECASE),
    # Pattern: IMG20241124155122.jpg (IMG + YYYYMMDD + partial time)
    re.compile(r'^IMG(\d{8})\d+\.\w+$', re.IGNORECASE),
    # Pattern: IMG_20230525_101125.jpg (IMG_ + YYYYMMDD + time)
    re.compile(r'^IMG_(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: 20230525_101125.jpg (YYYYMMDD + time)
    re.compile(r'^(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: IMG-20230525-WA0000.jpg (IMG-YYYYMMDD-)
    re.compile(r'^IMG-(\d{8})-.*\.\w+$', re.IGNORECASE),
    # Pattern: DSC_20230525_101125.jpg (DSC_ + YYYYMMDD + time)
    re.compile(r'^DSC_(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: PXL_20230525_101125.jpg (PXL_ + YYYYMMDD + time)
    re.compile(r'^PXL_(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: VID_20240731092916.mp4 (VID_ + YYYYMMDD + time)
    re.compile(r'^VID_(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: Screenshot_20230525-101125.jpg (Screenshot_YYYYMMDD-HHMMSS)
    re.compile(r'^Screenshot_(\d{8})-(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: WP_20230525_101125.jpg (WP_ + YYYYMMDD + time)
    re.compile(r'^WP_(\d{8})_(\d{6})\.\w+$', re.IGNORECASE),
    # Pattern: FB_IMG_20230525101125.jpg (FB_IMG_ + YYYYMMDD + time)
    re.compile(r'^FB_IMG_(\d{14})\.\w+$', re.IGNORECASE),
    # Pattern: Signal-2023-05-25-10-11-25-123.jpg (Signal-YYYY-MM-DD-HH-MM-SS)
    re.compile(r'^Signal-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-\d+\.\w+$', re.IGNORECASE),
]

# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.tiff', '.tif', '.webp', '.raw', '.arw', '.cr2', '.nef'}
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}
ALL_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)

def extract_datetime_from_filename(filename):
    """
    Extract datetime from filename using multiple patterns
    Returns datetime object or None if no datetime found
    """
    # Remove extension for matching
    name_without_ext = os.path.splitext(filename)[0]
    
    for pattern in DATE_PATTERNS:
        match = pattern.match(name_without_ext)
        if match:
            try:
                # Pattern with 14-digit datetime (YYYYMMDDHHMMSS)
                if pattern.pattern in [r'^IMG(\d{14})\.\w+$', r'^VID(\d{14})\.\w+$', r'^FB_IMG_(\d{14})\.\w+$']:
                    date_str = match.group(1)
                    if len(date_str) == 14:
                        date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        print(f"  ✓ Extracted full datetime from filename: {date_str}")
                        return date_obj
                
                # Patterns with separate date and time (8+6 digits)
                elif pattern.pattern in [r'^IMG_(\d{8})_(\d{6})\.\w+$', r'^(\d{8})_(\d{6})\.\w+$', 
                                       r'^DSC_(\d{8})_(\d{6})\.\w+$', r'^PXL_(\d{8})_(\d{6})\.\w+$',
                                       r'^VID_(\d{8})_(\d{6})\.\w+$', r'^Screenshot_(\d{8})-(\d{6})\.\w+$',
                                       r'^WP_(\d{8})_(\d{6})\.\w+$']:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"  ✓ Extracted datetime from filename: {date_str}_{time_str}")
                        return date_obj
                
                # Pattern with only date (8 digits)
                elif pattern.pattern in [r'^IMG(\d{8})\d+\.\w+$', r'^IMG-(\d{8})-.*\.\w+$']:
                    date_str = match.group(1)
                    if len(date_str) == 8:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        print(f"  ✓ Extracted date from filename: {date_str} (time set to 00:00:00)")
                        return date_obj
                
                # Pattern with separated date components (Signal format)
                elif pattern.pattern == r'^Signal-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-\d+\.\w+$':
                    year, month, day, hour, minute, second = match.groups()
                    datetime_str = f"{year}{month}{day}{hour}{minute}{second}"
                    date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                    print(f"  ✓ Extracted datetime from Signal format: {year}-{month}-{day} {hour}:{minute}:{second}")
                    return date_obj
                    
            except (ValueError, TypeError) as e:
                print(f"  ✗ Error parsing date from pattern {pattern.pattern}: {e}")
                continue
    
    return None

def get_file_dates(file_path):
    """
    Get all available dates for a file
    Returns dictionary with creation, modification, and filename dates
    """
    dates = {}
    
    # Get filesystem dates
    stat = os.stat(file_path)
    dates['creation'] = datetime.fromtimestamp(stat.st_ctime)
    dates['modification'] = datetime.fromtimestamp(stat.st_mtime)
    dates['access'] = datetime.fromtimestamp(stat.st_atime)
    
    # Get datetime from filename (only for files with clear datetime patterns)
    filename_datetime = extract_datetime_from_filename(os.path.basename(file_path))
    if filename_datetime:
        dates['filename'] = filename_datetime
    
    return dates

def get_oldest_date(date_dict):
    """
    Find the oldest date from creation, modification and filename dates
    Priority: Use filename date if it exists and is older than system dates
    Otherwise use the oldest system date
    """
    creation = date_dict.get('creation')
    modification = date_dict.get('modification')
    filename_date = date_dict.get('filename')
    
    # Collect all available dates
    all_dates = []
    if creation:
        all_dates.append(creation)
    if modification:
        all_dates.append(modification)
    if filename_date:
        all_dates.append(filename_date)
    
    if not all_dates:
        return None
    
    # Find the oldest date
    oldest_date = min(all_dates)
    
    # Check if filename date is the oldest
    if filename_date and filename_date == oldest_date:
        print(f"  ✓ Using filename datetime (oldest available)")
        return filename_date
    elif filename_date and filename_date < creation and filename_date < modification:
        print(f"  ✓ Using filename datetime (older than system dates)")
        return filename_date
    else:
        print(f"  ✓ Using oldest system date")
        return oldest_date

def needs_correction(date_dict, target_date):
    """
    Check if file needs date correction
    Returns True if creation or modification date differs from target date
    """
    creation = date_dict.get('creation')
    modification = date_dict.get('modification')
    
    # Check if either creation or modification date differs from target date
    if creation and abs((creation - target_date).total_seconds()) > 60:  # 1 minute tolerance
        return True
    if modification and abs((modification - target_date).total_seconds()) > 60:
        return True
    
    return False

def correct_file_dates(file_path, target_date):
    """
    Correct file dates to the target date
    """
    try:
        file_path_obj = filedate.File(file_path)
        file_path_obj.set(
            created=target_date,
            modified=target_date,
            accessed=target_date
        )
        return True
    except Exception as e:
        print(f"Error correcting dates for {file_path}: {str(e)}")
        return False

def get_year_folder_name(target_date):
    """
    Generate folder name in format: Photos from YYYY
    Example: Photos from 2023
    """
    return f"Photos from {target_date.strftime('%Y')}"

def generate_new_filename(file_path, target_date, file_counter):
    """
    Generate new filename based on date and counter
    Format: VID_YYYYMMDD_HHMMSS_counter.extension for videos
    Format: IMG_YYYYMMDD_HHMMSS_counter.extension for images
    """
    file_ext = os.path.splitext(file_path)[1].lower()
    
    # Determine prefix based on file type
    if file_ext in VIDEO_EXTENSIONS:
        prefix = "VID"
    else:
        prefix = "IMG"
    
    # Format: YYYYMMDD_HHMMSS
    date_part = target_date.strftime('%Y%m%d_%H%M%S')
    
    # Add counter to ensure unique filenames
    new_filename = f"{prefix}_{date_part}_{file_counter:04d}{file_ext}"
    
    return new_filename

def process_media_file(file_path, output_base_dir, file_counter):
    """
    Process a single media file - correct dates in original file and create copy with new name in year folder
    """
    try:
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        file_type = "IMAGE" if file_ext in IMAGE_EXTENSIONS else "VIDEO"
        
        print(f"Processing {file_type}: {filename}")
        
        # Get all available dates from ORIGINAL file
        dates = get_file_dates(file_path)
        
        creation = dates.get('creation')
        modification = dates.get('modification')
        filename_date = dates.get('filename')
        
        print(f"  Creation date:    {creation}")
        print(f"  Modification date: {modification}")
        if filename_date:
            print(f"  Filename datetime: {filename_date}")
        
        # Find the oldest date (priority: filename if older than system dates)
        target_date = get_oldest_date(dates)
        if not target_date:
            print(f"  ✗ No valid target date found, using current date...")
            target_date = datetime.now()
        
        print(f"  Target date:      {target_date}")
        
        # Check if correction is needed
        if needs_correction(dates, target_date):
            print(f"  ✓ Correcting dates in original file...")
            if correct_file_dates(file_path, target_date):
                print(f"  ✓ Dates corrected in original file")
            else:
                print(f"  ✗ Failed to correct dates in original file")
                return False, file_counter
        else:
            print(f"  ✓ Dates are consistent, no correction needed")
        
        # Create year folder
        year_folder = get_year_folder_name(target_date)
        year_output_dir = os.path.join(output_base_dir, year_folder)
        
        if not os.path.exists(year_output_dir):
            os.makedirs(year_output_dir)
            print(f"  ✓ Created year folder: {year_folder}")
        
        # Generate new filename for the COPY
        new_filename = generate_new_filename(file_path, target_date, file_counter)
        new_file_path = os.path.join(year_output_dir, new_filename)
        
        # Copy file with new name to year folder (original remains unchanged)
        shutil.copy2(file_path, new_file_path)
        print(f"  ✓ Copy created in '{year_folder}': {new_filename}")
        
        return True, file_counter + 1
            
    except Exception as e:
        print(f"Error processing {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, file_counter

def find_photos_directories(search_path):
    """
    Find all directories that contain 'Photos from' in their name
    """
    photos_dirs = []
    
    for root, dirs, files in os.walk(search_path):
        for dir_name in dirs:
            if 'Photos from' in dir_name:
                full_path = os.path.join(root, dir_name)
                photos_dirs.append(full_path)
                print(f"Found Photos directory: {full_path}")
    
    return photos_dirs

def find_media_files_in_directories(directories):
    """
    Find all media files (images and videos) in the given directories
    """
    media_files = []
    
    for directory in directories:
        print(f"Searching in: {directory}")
        for root, dirs, files in os.walk(directory):
            for file in files:
                file_ext = os.path.splitext(file)[1].lower()
                if file_ext in ALL_EXTENSIONS:
                    full_path = os.path.join(root, file)
                    media_files.append(full_path)
    
    return media_files

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Correct media file dates and create copies with standardized names organized by year')
    parser.add_argument('--path', type=str, default='.', 
                       help='Path to search for media files (default: current directory)')
    parser.add_argument('--output', type=str, required=True,
                       help='Output directory for renamed copies organized by year (required)')
    
    args = parser.parse_args()
    
    search_path = args.path
    output_base_dir = args.output
    
    # Validate paths
    if not os.path.exists(search_path):
        print(f"Error: Path '{search_path}' does not exist")
        return
    
    if not os.path.exists(output_base_dir):
        os.makedirs(output_base_dir)
        print(f"Created output directory: {output_base_dir}")
    
    print(f"Searching for 'Photos from' directories in: {os.path.abspath(search_path)}")
    print(f"Output directory for copies: {os.path.abspath(output_base_dir)}")
    print(f"Files will be organized in folders: 'Photos from YYYY'")
    print(f"Supported formats: {', '.join(sorted(ALL_EXTENSIONS))}")
    print(f"Date priority: Oldest date (filename if older than system dates) > Oldest system date")
    print(f"Original files will be preserved with corrected dates")
    print(f"Copies with new names will be created in year folders")
    print(f"Supported filename patterns:")
    print(f"  - IMG20230710162352.jpg (full datetime)")
    print(f"  - IMG_20230525_101125.jpg (date + time)")
    print(f"  - VID20240731092916.mp4 (full datetime)")
    print(f"  - 20230525_101125.jpg (date + time)")
    print(f"  - And many others...")
    
    # Find all directories containing 'Photos from'
    photos_dirs = find_photos_directories(search_path)
    print(f"Found {len(photos_dirs)} directories with 'Photos from'")
    
    if not photos_dirs:
        print("No 'Photos from' directories found.")
        return
    
    # Find all media files in Photos directories
    media_files = find_media_files_in_directories(photos_dirs)
    print(f"Found {len(media_files)} media files in Photos directories")
    
    if not media_files:
        print("No media files found in Photos directories.")
        return
    
    # Sort files by current creation date for consistent processing
    media_files.sort(key=lambda x: os.path.getctime(x))
    
    # Process each media file
    processed_count = 0
    file_counter = 1
    year_folders_created = set()
    
    for media_file in media_files:
        success, file_counter = process_media_file(media_file, output_base_dir, file_counter)
        if success:
            processed_count += 1
        
        print("-" * 60)
    
    # List all created year folders
    created_folders = [d for d in os.listdir(output_base_dir) if os.path.isdir(os.path.join(output_base_dir, d)) and 'Photos from' in d]
    print(f"\nCreated {len(created_folders)} year folders:")
    for folder in sorted(created_folders):
        print(f"  - {folder}")
    
    print(f"\nProcessing completed!")
    print(f"Successfully processed: {processed_count}/{len(media_files)} files")
    print(f"Original files preserved with corrected dates")
    print(f"Copies with standardized names created in: {os.path.abspath(output_base_dir)}")
    print(f"\nOrganization:")
    print(f"  Files organized in folders: 'Photos from YYYY'")
    print(f"  Naming pattern:")
    print(f"    Images: IMG_YYYYMMDD_HHMMSS_####.extension")
    print(f"    Videos: VID_YYYYMMDD_HHMMSS_####.extension")
    print(f"  Example: 'Photos from 2023/IMG_20230710_162352_0001.jpg'")

if __name__ == "__main__":
    main()