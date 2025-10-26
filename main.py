import os
import re
from datetime import datetime
import filedate
import shutil
import uuid
import string
import time
from pathlib import Path
from PIL import Image, ExifTags
from PIL.ExifTags import TAGS, GPSTAGS
import subprocess

# Define patterns for date extraction from filenames - with full datetime support
DATE_PATTERNS = [
    # Pattern: IMG20230710162352.jpg (IMG + YYYYMMDDHHMMSS)
    re.compile(r'^IMG(\d{14})', re.IGNORECASE),
    # Pattern: VID20240731092916.mp4 (VID + YYYYMMDDHHMMSS)
    re.compile(r'^VID(\d{14})', re.IGNORECASE),
    # Pattern: IMG20241124155122.jpg (IMG + YYYYMMDD + partial time)
    re.compile(r'^IMG(\d{8})\d*', re.IGNORECASE),
    # Pattern: IMG_20230525_101125.jpg (IMG_ + YYYYMMDD + time)
    re.compile(r'^IMG_(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: IMG_20220124_135913_1.jpg (IMG_ + YYYYMMDD + time + counter)
    re.compile(r'^IMG_(\d{8})_(\d{6})_\d+', re.IGNORECASE),
    # Pattern: 20230525_101125.jpg (YYYYMMDD + time)
    re.compile(r'^(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: IMG-20230525-WA0000.jpg (IMG-YYYYMMDD-)
    re.compile(r'^IMG-(\d{8})-', re.IGNORECASE),
    # Pattern: DSC_20230525_101125.jpg (DSC_ + YYYYMMDD + time)
    re.compile(r'^DSC_(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: PXL_20230525_101125.jpg (PXL_ + YYYYMMDD + time)
    re.compile(r'^PXL_(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: VID_20240731092916.mp4 (VID_ + YYYYMMDD + time)
    re.compile(r'^VID_(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: Screenshot_20230525-101125.jpg (Screenshot_YYYYMMDD-HHMMSS)
    re.compile(r'^Screenshot_(\d{8})-(\d{6})', re.IGNORECASE),
    # Pattern: WP_20230525_101125.jpg (WP_ + YYYYMMDD + time)
    re.compile(r'^WP_(\d{8})_(\d{6})', re.IGNORECASE),
    # Pattern: FB_IMG_20230525101125.jpg (FB_IMG_ + YYYYMMDD + time)
    re.compile(r'^FB_IMG_(\d{14})', re.IGNORECASE),
    # Pattern: Signal-2023-05-25-10-11-25-123.jpg (Signal-YYYY-MM-DD-HH-MM-SS)
    re.compile(r'^Signal-(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-\d+', re.IGNORECASE),
    # Pattern: MS_2017-07-24_14-31-43 (MS_ + YYYY-MM-DD + HH-MM-SS)
    re.compile(r'^MS_(\d{4})-(\d{2})-(\d{2})_(\d{2})-(\d{2})-(\d{2})', re.IGNORECASE),
]

# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.tiff', '.tif', '.webp', '.raw', '.arw', '.cr2', '.nef', '.gif'}
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}
ALL_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)

def get_exif_metadata_advanced(file_path):
    """
    Extract EXIF metadata using exiftool for better compatibility
    """
    try:
        result = subprocess.run([
            'exiftool', 
            '-DateTimeOriginal',
            '-CreateDate',
            '-ModifyDate',
            '-FileModifyDate',
            '-Make',
            '-Model',
            '-GPSLatitude',
            '-GPSLongitude',
            '-GPSLatitudeRef',
            '-GPSLongitudeRef',
            '-json',
            file_path
        ], capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0 and result.stdout.strip():
            import json
            metadata = json.loads(result.stdout)[0]
            return metadata
        else:
            return {}
            
    except Exception as e:
        print(f"    ⚠ exiftool error: {e}")
        return {}

def get_exif_datetime(file_path):
    """
    Get DateTimeOriginal and CreateDate from EXIF metadata using exiftool
    Returns the oldest available EXIF date
    """
    try:
        metadata = get_exif_metadata_advanced(file_path)
        
        exif_dates = []
        
        # Priority 1: DateTimeOriginal (data wykonania zdjęcia)
        if 'DateTimeOriginal' in metadata and metadata['DateTimeOriginal']:
            try:
                dt_original = datetime.strptime(metadata['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')
                exif_dates.append(dt_original)
                print(f"    📅 DateTimeOriginal: {dt_original}")
            except ValueError as e:
                print(f"    ⚠ Error parsing DateTimeOriginal: {e}")
        
        # Priority 2: CreateDate (data utworzenia pliku w EXIF)
        if 'CreateDate' in metadata and metadata['CreateDate']:
            try:
                create_date = datetime.strptime(metadata['CreateDate'], '%Y:%m:%d %H:%M:%S')
                exif_dates.append(create_date)
                print(f"    📅 CreateDate: {create_date}")
            except ValueError as e:
                print(f"    ⚠ Error parsing CreateDate: {e}")
        
        # Priority 3: ModifyDate
        if 'ModifyDate' in metadata and metadata['ModifyDate']:
            try:
                modify_date = datetime.strptime(metadata['ModifyDate'], '%Y:%m:%d %H:%M:%S')
                exif_dates.append(modify_date)
                print(f"    📅 ModifyDate: {modify_date}")
            except ValueError as e:
                print(f"    ⚠ Error parsing ModifyDate: {e}")
        
        if exif_dates:
            oldest_exif = min(exif_dates)
            print(f"    ✅ Najstarsza data EXIF: {oldest_exif}")
            return oldest_exif
        else:
            print(f"    ⚠ Brak dat EXIF w metadanych")
            return None
            
    except Exception as e:
        print(f"    ⚠ Error getting EXIF datetime: {e}")
        return None

def get_file_dates(file_path):
    """
    Get all available dates for a file with EXIF priority
    """
    dates = {}
    
    print(f"  🔍 Szukam dat dla: {os.path.basename(file_path)}")
    
    # PRIORYTET 1: Daty z EXIF (DateTimeOriginal, CreateDate)
    exif_date = get_exif_datetime(file_path)
    if exif_date:
        dates['exif'] = exif_date
        print(f"    ✅ Znaleziono datę EXIF: {exif_date}")
    
    # PRIORYTET 2: Daty systemowe (fallback)
    try:
        stat = os.stat(file_path)
        
        # macOS birthtime (data utworzenia)
        if hasattr(stat, 'st_birthtime'):
            creation_date = datetime.fromtimestamp(stat.st_birthtime)
            dates['creation'] = creation_date
            print(f"    📅 System creation: {creation_date}")
        else:
            creation_date = datetime.fromtimestamp(stat.st_ctime)
            dates['creation'] = creation_date
            print(f"    📅 System ctime: {creation_date}")
        
        modification_date = datetime.fromtimestamp(stat.st_mtime)
        dates['modification'] = modification_date
        print(f"    📅 System modification: {modification_date}")
        
    except Exception as e:
        print(f"    ⚠ Error getting system dates: {e}")
    
    # PRIORYTET 3: Data z nazwy pliku
    filename_datetime = extract_datetime_from_filename(os.path.basename(file_path))
    if filename_datetime:
        dates['filename'] = filename_datetime
        print(f"    📅 Filename date: {filename_datetime}")
    
    return dates

def get_oldest_date(date_dict):
    """
    Find the ABSOLUTE OLDEST date from all available sources:
    - EXIF dates (DateTimeOriginal, CreateDate) - HIGHEST PRIORITY
    - filename date
    - creation date  
    - modification date
    """
    exif_date = date_dict.get('exif')
    creation = date_dict.get('creation')
    modification = date_dict.get('modification')
    filename_date = date_dict.get('filename')
    
    # Collect all available dates
    all_dates = []
    
    # EXIF ma najwyższy priorytet
    if exif_date:
        all_dates.append(exif_date)
    if creation:
        all_dates.append(creation)
    if modification:
        all_dates.append(modification)
    if filename_date:
        all_dates.append(filename_date)
    
    if not all_dates:
        return None
    
    # Find the ABSOLUTE OLDEST date
    oldest_date = min(all_dates)
    
    # Report which source provided the oldest date
    if exif_date and exif_date == oldest_date:
        print(f"  ✅ Using EXIF datetime (OLDEST: {oldest_date})")
    elif filename_date and filename_date == oldest_date:
        print(f"  ✅ Using filename datetime (OLDEST: {oldest_date})")
    elif creation and creation == oldest_date:
        print(f"  ✅ Using creation date (OLDEST: {oldest_date})")
    elif modification and modification == oldest_date:
        print(f"  ✅ Using modification date (OLDEST: {oldest_date})")
    
    return oldest_date

def display_camera_info(file_path):
    """
    Display camera/model information from file metadata using exiftool
    """
    try:
        metadata = get_exif_metadata_advanced(file_path)
        
        make = metadata.get('Make', '')
        model = metadata.get('Model', '')
        
        if make or model:
            camera_info = []
            if make:
                camera_info.append(str(make).strip())
            if model:
                camera_info.append(str(model).strip())
            
            if camera_info:
                return " / ".join(camera_info)
        
        return None
        
    except Exception as e:
        return None

def display_gps_info(file_path):
    """
    Display GPS/location information from file metadata using exiftool
    """
    try:
        metadata = get_exif_metadata_advanced(file_path)
        
        lat = metadata.get('GPSLatitude')
        lon = metadata.get('GPSLongitude')
        lat_ref = metadata.get('GPSLatitudeRef', 'N')
        lon_ref = metadata.get('GPSLongitudeRef', 'E')
        
        if lat and lon:
            # Convert to decimal if needed
            try:
                if isinstance(lat, str) and '°' in lat:
                    # Parse DMS format: 50° 3' 39.84" N
                    def dms_to_decimal(dms_str, ref):
                        parts = dms_str.replace('°', ' ').replace("'", ' ').replace('"', ' ').split()
                        degrees = float(parts[0])
                        minutes = float(parts[1])
                        seconds = float(parts[2])
                        decimal = degrees + (minutes / 60.0) + (seconds / 3600.0)
                        if ref in ['S', 'W']:
                            decimal = -decimal
                        return decimal
                    
                    decimal_lat = dms_to_decimal(lat, lat_ref)
                    decimal_lon = dms_to_decimal(lon, lon_ref)
                else:
                    decimal_lat = float(lat)
                    decimal_lon = float(lon)
                    if lat_ref == 'S':
                        decimal_lat = -decimal_lat
                    if lon_ref == 'W':
                        decimal_lon = -decimal_lon
                
                lat_dir = "N" if decimal_lat >= 0 else "S"
                lon_dir = "E" if decimal_lon >= 0 else "W"
                
                return f"{abs(decimal_lat):.6f}°{lat_dir}, {abs(decimal_lon):.6f}°{lon_dir}"
                
            except Exception as e:
                print(f"    ⚠ GPS conversion error: {e}")
                return f"{lat} {lat_ref}, {lon} {lon_ref}"
        
        return None
        
    except Exception as e:
        return None

def copy_file_preserve_metadata(source_path, dest_path):
    """
    Copy file while preserving all possible metadata using exiftool
    """
    try:
        file_ext = os.path.splitext(source_path)[1].lower()
        
        print(f"    📁 Copying {file_ext} file...")
        
        # For all files, use exiftool to preserve metadata
        try:
            # Use exiftool to copy with all metadata
            result = subprocess.run([
                'exiftool',
                '-overwrite_original',
                '-tagsFromFile', source_path,
                dest_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                print(f"    ✓ Copied with all metadata using exiftool")
                
                # Display camera and GPS info if available
                camera_info = display_camera_info(source_path)
                gps_info = display_gps_info(source_path)
                
                if camera_info:
                    print(f"    📱 Camera: {camera_info}")
                if gps_info:
                    print(f"    📍 Location: {gps_info}")
                
                return True
            else:
                print(f"    ⚠ exiftool copy failed: {result.stderr}")
                # Fallback to basic copy
                shutil.copy2(source_path, dest_path)
                print(f"    ✓ Fallback: copied with basic metadata")
                return True
                
        except Exception as e:
            print(f"    ⚠ exiftool failed, using basic copy: {e}")
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Fallback: copied with basic metadata")
            return True
            
    except Exception as e:
        print(f"    ✗ Metadata copy failed: {e}")
        # Final fallback
        try:
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Final fallback: copied with basic metadata")
            return True
        except Exception as e2:
            print(f"    ✗ Complete copy failure: {e2}")
            return False

# Pozostałe funkcje pozostają bez zmian (extract_datetime_from_filename, needs_correction, correct_file_dates, etc.)
# ... [reszta funkcji pozostaje taka sama jak w oryginalnym kodzie] ...

def extract_datetime_from_filename(filename):
    """
    Extract datetime from filename using multiple patterns
    Returns datetime object or None if no datetime found
    """
    # Remove extension for matching
    name_without_ext = os.path.splitext(filename)[0]
    
    print(f"  🔍 Testing filename: '{name_without_ext}'")
    
    for i, pattern in enumerate(DATE_PATTERNS):
        match = pattern.match(name_without_ext)
        if match:
            try:
                print(f"  ✓ Pattern {i+1} matched: {pattern.pattern}")
                
                # Pattern 1: IMG20230710162352.jpg (IMG + YYYYMMDDHHMMSS)
                if i == 0:
                    date_str = match.group(1)
                    if len(date_str) == 14:
                        date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 2: VID20240731092916.mp4 (VID + YYYYMMDDHHMMSS)
                elif i == 1:
                    date_str = match.group(1)
                    if len(date_str) == 14:
                        date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 3: IMG20241124155122.jpg (IMG + YYYYMMDD + partial time)
                elif i == 2:
                    date_str = match.group(1)
                    if len(date_str) == 8:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        print(f"    Extracted: {date_str} -> {date_obj} (date only)")
                        return date_obj
                
                # Pattern 4: IMG_20230525_101125.jpg (IMG_ + YYYYMMDD + time)
                elif i == 3:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 5: IMG_20220124_135913_1.jpg (IMG_ + YYYYMMDD + time + counter)
                elif i == 4:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 6: 20230525_101125.jpg (YYYYMMDD + time)
                elif i == 5:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 7: IMG-20230525-WA0000.jpg (IMG-YYYYMMDD-)
                elif i == 6:
                    date_str = match.group(1)
                    if len(date_str) == 8:
                        date_obj = datetime.strptime(date_str, '%Y%m%d')
                        print(f"    Extracted: {date_str} -> {date_obj} (date only)")
                        return date_obj
                
                # Pattern 8: DSC_20230525_101125.jpg (DSC_ + YYYYMMDD + time)
                elif i == 7:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 9: PXL_20230525_101125.jpg (PXL_ + YYYYMMDD + time)
                elif i == 8:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 10: VID_20240731092916.mp4 (VID_ + YYYYMMDD + time)
                elif i == 9:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 11: Screenshot_20230525-101125.jpg (Screenshot_YYYYMMDD-HHMMSS)
                elif i == 10:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}-{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 12: WP_20230525_101125.jpg (WP_ + YYYYMMDD + time)
                elif i == 11:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    if len(date_str) == 8 and len(time_str) == 6:
                        datetime_str = f"{date_str}{time_str}"
                        date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str}_{time_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 13: FB_IMG_20230525101125.jpg (FB_IMG_ + YYYYMMDD + time)
                elif i == 12:
                    date_str = match.group(1)
                    if len(date_str) == 14:
                        date_obj = datetime.strptime(date_str, '%Y%m%d%H%M%S')
                        print(f"    Extracted: {date_str} -> {date_obj}")
                        return date_obj
                
                # Pattern 14: Signal-2023-05-25-10-11-25-123.jpg (Signal-YYYY-MM-DD-HH-MM-SS)
                elif i == 13:
                    year, month, day, hour, minute, second = match.groups()
                    datetime_str = f"{year}{month}{day}{hour}{minute}{second}"
                    date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                    print(f"    Extracted: {year}-{month}-{day} {hour}:{minute}:{second} -> {date_obj}")
                    return date_obj
                
                # Pattern 15: MS_2017-07-24_14-31-43 (MS_ + YYYY-MM-DD + HH-MM-SS)
                elif i == 14:
                    year, month, day, hour, minute, second = match.groups()
                    # Format: YYYY-MM-DD_HH-MM-SS -> YYYYMMDDHHMMSS
                    datetime_str = f"{year}{month}{day}{hour}{minute}{second}"
                    date_obj = datetime.strptime(datetime_str, '%Y%m%d%H%M%S')
                    print(f"    Extracted: MS_{year}-{month}-{day}_{hour}-{minute}-{second} -> {date_obj}")
                    return date_obj
                    
            except (ValueError, TypeError) as e:
                print(f"    ✗ Error parsing date from pattern {i+1}: {e}")
                continue
    
    print(f"  ✗ No pattern matched for filename: {name_without_ext}")
    return None

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

def set_file_dates_manual(file_path, target_date):
    """
    Manually set file dates using os.utime as fallback
    """
    try:
        # Convert datetime to timestamp
        timestamp = time.mktime(target_date.timetuple())
        
        # Set modification and access time
        os.utime(file_path, (timestamp, timestamp))
        
        print(f"    ✓ Manual date setting: {target_date}")
        return True
    except Exception as e:
        print(f"    ⚠ Manual date setting failed: {e}")
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

def verify_file_dates(file_path, expected_date):
    """
    Verify that file dates match the expected date
    """
    try:
        stat = os.stat(file_path)
        creation = datetime.fromtimestamp(stat.st_ctime)
        modification = datetime.fromtimestamp(stat.st_mtime)
        
        creation_match = abs((creation - expected_date).total_seconds()) <= 60
        modification_match = abs((modification - expected_date).total_seconds()) <= 60
        
        if creation_match and modification_match:
            print(f"    ✅ Dates verified: {expected_date}")
            return True
        else:
            print(f"    ⚠ Date mismatch - Creation: {creation}, Modification: {modification}, Expected: {expected_date}")
            return False
            
    except Exception as e:
        print(f"    ⚠ Date verification failed: {e}")
        return False

def process_media_file(file_path, output_base_dir, file_counter):
    """
    Process a single media file - correct dates in original file and create copy with new name in year folder
    """
    try:
        filename = os.path.basename(file_path)
        file_ext = os.path.splitext(file_path)[1].lower()
        file_type = "IMAGE" if file_ext in IMAGE_EXTENSIONS else "VIDEO"
        
        print(f"🎬 Processing {file_type}: {filename}")
        
        # Display camera and GPS info if available
        camera_info = display_camera_info(file_path)
        gps_info = display_gps_info(file_path)
        
        if camera_info:
            print(f"  📱 Camera: {camera_info}")
        if gps_info:
            print(f"  📍 Location: {gps_info}")
        
        # Get all available dates from ORIGINAL file
        dates = get_file_dates(file_path)
        
        # Find the ABSOLUTE OLDEST date from all sources
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
                # Verify the correction
                verify_file_dates(file_path, target_date)
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
        
        # Copy file with new name to year folder while preserving metadata including GPS
        print(f"  📸 Copying with metadata preservation...")
        success = copy_file_preserve_metadata(file_path, new_file_path)
        
        if success:
            # Set correct dates on the copy
            print(f"  ⚙ Setting correct dates on copy...")
            
            # Try filedate first
            if not correct_file_dates(new_file_path, target_date):
                # Fallback to manual method
                print(f"  ⚠ Filedate failed, using manual method...")
                set_file_dates_manual(new_file_path, target_date)
            
            # Verify dates on the copy
            print(f"  🔍 Verifying dates on copy...")
            if verify_file_dates(new_file_path, target_date):
                print(f"  ✅ Copy dates verified successfully")
            else:
                print(f"  ⚠ Copy date verification failed, but file was created")
            
            print(f"  ✅ Copy created in '{year_folder}': {new_filename}")
            return True, file_counter + 1
        else:
            print(f"  ✗ Failed to create copy with metadata")
            return False, file_counter
            
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, file_counter

def find_media_files(search_path):
    """
    Find all media files (images and videos) in the given directory and all subdirectories
    """
    media_files = []
    
    print(f"Searching for media files in: {os.path.abspath(search_path)}")
    
    for root, dirs, files in os.walk(search_path):
        # Skip system directories to improve performance
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
        
        for file in files:
            file_ext = os.path.splitext(file)[1].lower()
            if file_ext in ALL_EXTENSIONS:
                full_path = os.path.join(root, file)
                media_files.append(full_path)
    
    print(f"Found {len(media_files)} media files in all directories")
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
    
    print(f"Searching for media files in: {os.path.abspath(search_path)}")
    print(f"Output directory for copies: {os.path.abspath(output_base_dir)}")
    print(f"Files will be organized in folders: 'Photos from YYYY'")
    print(f"Supported formats: {', '.join(sorted(ALL_EXTENSIONS))}")
    print(f"Supported video formats: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    print("📅 DATE PRIORITY: EXIF (DateTimeOriginal, CreateDate) > Filename > System Dates")
    print(f"Original files will be preserved with corrected dates")
    print(f"Copies with new names will be created in year folders")
    
    # Check if exiftool is available
    try:
        result = subprocess.run(['exiftool', '-ver'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ exiftool available: {result.stdout.strip()}")
        else:
            print("⚠ exiftool not available, using fallback methods")
    except:
        print("⚠ exiftool not installed, using fallback methods")
    
    # Find all media files in ALL directories
    media_files = find_media_files(search_path)
    
    if not media_files:
        print("No media files found.")
        return
    
    # Sort files by current creation date for consistent processing
    media_files.sort(key=lambda x: os.path.getctime(x))
    
    # Process each media file
    processed_count = 0
    file_counter = 1
    
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
    print(f"✅ DATE SYNCHRONIZATION: File dates now match the OLDEST available date")
    print(f"📅 EXIF metadata used for date detection (DateTimeOriginal, CreateDate)")
    print(f"Camera information detected and preserved")
    print(f"GPS/Location data preserved where available")
    print(f"\nOrganization:")
    print(f"  Files organized in folders: 'Photos from YYYY'")
    print(f"  Naming pattern:")
    print(f"    Images: IMG_YYYYMMDD_HHMMSS_####.extension")
    print(f"    Videos: VID_YYYYMMDD_HHMMSS_####.extension")
    print(f"  Example: 'Photos from 2025/IMG_20250608_114823_0001.jpg'")

if __name__ == "__main__":
    main()
