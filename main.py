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

# Supported file extensions - MOV jest już na liście
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.heic', '.bmp', '.tiff', '.tif', '.webp', '.raw', '.arw', '.cr2', '.nef', '.gif'}
VIDEO_EXTENSIONS = {'.mov', '.mp4', '.avi', '.mkv', '.wmv', '.flv', '.webm', '.m4v', '.3gp'}  # .mov jest tutaj
ALL_EXTENSIONS = IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)

def get_gps_info(exif_data):
    """
    Extract GPS information from EXIF data
    Returns dictionary with GPS coordinates or None if no GPS data
    """
    try:
        if 'GPSInfo' not in exif_data:
            return None
        
        gps_info = {}
        gps_data = exif_data['GPSInfo']
        
        # Extract GPS tags
        for tag, value in gps_data.items():
            tag_name = GPSTAGS.get(tag, tag)
            gps_info[tag_name] = value
        
        # Convert to decimal coordinates if possible
        gps_coords = convert_gps_coordinates(gps_info)
        if gps_coords:
            gps_info['decimal_coordinates'] = gps_coords
            gps_info['google_maps_url'] = f"https://maps.google.com/?q={gps_coords[0]},{gps_coords[1]}"
        
        return gps_info
    except Exception as e:
        print(f"    ⚠ Error extracting GPS info: {e}")
        return None

def convert_gps_coordinates(gps_info):
    """
    Convert GPS coordinates from EXIF format to decimal degrees
    """
    try:
        # GPSLatitude and GPSLongitude should be available
        if 'GPSLatitude' not in gps_info or 'GPSLongitude' not in gps_info:
            return None
        
        # Get reference directions
        lat_ref = gps_info.get('GPSLatitudeRef', 'N')
        lon_ref = gps_info.get('GPSLongitudeRef', 'E')
        
        # Convert latitude
        lat = gps_info['GPSLatitude']
        lat_deg = float(lat[0])
        lat_min = float(lat[1])
        lat_sec = float(lat[2])
        decimal_lat = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
        if lat_ref == 'S':
            decimal_lat = -decimal_lat
        
        # Convert longitude
        lon = gps_info['GPSLongitude']
        lon_deg = float(lon[0])
        lon_min = float(lon[1])
        lon_sec = float(lon[2])
        decimal_lon = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)
        if lon_ref == 'W':
            decimal_lon = -decimal_lon
        
        return (decimal_lat, decimal_lon)
        
    except Exception as e:
        print(f"    ⚠ Error converting GPS coordinates: {e}")
        return None

def get_exif_metadata(image):
    """
    Extract EXIF metadata from PIL Image including GPS data
    """
    try:
        exif_data = {}
        if hasattr(image, '_getexif') and image._getexif() is not None:
            for tag_id, value in image._getexif().items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
            
            # Extract GPS information
            gps_info = get_gps_info(exif_data)
            if gps_info:
                exif_data['GPSInfo'] = gps_info
                
        return exif_data
    except Exception as e:
        print(f"    ⚠ Error extracting EXIF: {e}")
        return {}

def display_camera_info(file_path):
    """
    Display camera/model information from file metadata
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.webp']:
            with Image.open(file_path) as img:
                exif_data = get_exif_metadata(img)
                
                make = exif_data.get('Make', '')
                model = exif_data.get('Model', '')
                software = exif_data.get('Software', '')
                
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
    Display GPS/location information from file metadata
    """
    try:
        file_ext = os.path.splitext(file_path)[1].lower()
        
        if file_ext in ['.jpg', '.jpeg', '.tiff', '.tif', '.png', '.webp']:
            with Image.open(file_path) as img:
                exif_data = get_exif_metadata(img)
                
                if 'GPSInfo' in exif_data and 'decimal_coordinates' in exif_data['GPSInfo']:
                    gps_data = exif_data['GPSInfo']
                    coords = gps_data['decimal_coordinates']
                    
                    # Format coordinates for display
                    lat = coords[0]
                    lon = coords[1]
                    lat_dir = "N" if lat >= 0 else "S"
                    lon_dir = "E" if lon >= 0 else "W"
                    
                    return f"{abs(lat):.6f}°{lat_dir}, {abs(lon):.6f}°{lon_dir}"
        
        return None
        
    except Exception as e:
        return None

def copy_file_preserve_metadata(source_path, dest_path):
    """
    Copy file while preserving all possible metadata
    """
    try:
        file_ext = os.path.splitext(source_path)[1].lower()
        
        print(f"    📁 Copying {file_ext} file...")
        
        # Dla plików MOV i GIF używamy shutil.copy2 który kopiuje metadane
        if file_ext in ['.mov', '.gif']:
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Copied {file_ext.upper()} with basic metadata")
            return True
        
        # For images with EXIF data (JPEG, TIFF)
        if file_ext in ['.jpg', '.jpeg', '.tiff', '.tif']:
            try:
                with Image.open(source_path) as img:
                    # Preserve EXIF data including GPS
                    exif_data = img.info.get('exif')
                    if exif_data:
                        # Save with original EXIF data (includes GPS)
                        img.save(dest_path, exif=exif_data)
                        
                        # Display camera and GPS info if available
                        camera_info = display_camera_info(source_path)
                        gps_info = display_gps_info(source_path)
                        
                        if camera_info:
                            print(f"    📱 Camera: {camera_info}")
                        if gps_info:
                            print(f"    📍 Location: {gps_info}")
                            print(f"    ✓ Copied with EXIF metadata (including GPS)")
                        else:
                            print(f"    ✓ Copied with EXIF metadata")
                    else:
                        shutil.copy2(source_path, dest_path)
                        print(f"    ✓ Copied with basic metadata")
            except Exception as e:
                print(f"    ⚠ EXIF copy failed, using basic copy: {e}")
                shutil.copy2(source_path, dest_path)
        
        # For PNG files (limited EXIF support)
        elif file_ext == '.png':
            try:
                with Image.open(source_path) as img:
                    # PNG has limited EXIF support, but we try to preserve what we can
                    exif_data = img.info.get('exif')
                    if exif_data:
                        img.save(dest_path, "PNG", exif=exif_data)
                        print(f"    ✓ Copied PNG with EXIF metadata")
                    else:
                        img.save(dest_path, "PNG")
                        print(f"    ✓ Copied PNG with basic metadata")
            except Exception as e:
                print(f"    ⚠ PNG copy failed, using basic copy: {e}")
                shutil.copy2(source_path, dest_path)
        
        # For WebP files
        elif file_ext == '.webp':
            try:
                with Image.open(source_path) as img:
                    # WebP supports some EXIF data including GPS
                    exif_data = img.info.get('exif')
                    if exif_data:
                        img.save(dest_path, "WEBP", exif=exif_data)
                        
                        # Display GPS info if available
                        gps_info = display_gps_info(source_path)
                        if gps_info:
                            print(f"    📍 Location: {gps_info}")
                            print(f"    ✓ Copied WebP with EXIF metadata (including GPS)")
                        else:
                            print(f"    ✓ Copied WebP with EXIF metadata")
                    else:
                        img.save(dest_path, "WEBP")
                        print(f"    ✓ Copied WebP with basic metadata")
            except Exception as e:
                print(f"    ⚠ WebP copy failed, using basic copy: {e}")
                shutil.copy2(source_path, dest_path)
        
        # For HEIC files - preserve metadata if possible
        elif file_ext == '.heic':
            try:
                # For HEIC, we use basic copy but note about GPS preservation
                shutil.copy2(source_path, dest_path)
                
                # Check if original has GPS data
                gps_info = display_gps_info(source_path)
                if gps_info:
                    print(f"    📍 Location: {gps_info}")
                    print(f"    ⚠ HEIC copied directly (GPS data should be preserved)")
                else:
                    print(f"    ⚠ HEIC copied directly (install pyheif for better metadata handling)")
            except Exception as e:
                print(f"    ⚠ HEIC copy failed: {e}")
                return False
        
        # For other video files
        elif file_ext in VIDEO_EXTENSIONS:
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Copied video ({file_ext}) with basic metadata")
            
        # For other files
        else:
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Copied with basic metadata")
            
        return True
            
    except Exception as e:
        print(f"    ✗ Metadata copy failed: {e}")
        # Fallback to basic copy
        try:
            shutil.copy2(source_path, dest_path)
            print(f"    ✓ Fallback: copied with basic metadata")
            return True
        except Exception as e2:
            print(f"    ✗ Complete copy failure: {e2}")
            return False

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
    Find the ABSOLUTE OLDEST date from all available sources:
    - filename date
    - creation date  
    - modification date
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
    
    # Find the ABSOLUTE OLDEST date
    oldest_date = min(all_dates)
    
    # Report which source provided the oldest date
    if filename_date and filename_date == oldest_date:
        print(f"  ✅ Using filename datetime (OLDEST: {oldest_date})")
    elif creation and creation == oldest_date:
        print(f"  ✅ Using creation date (OLDEST: {oldest_date})")
    elif modification and modification == oldest_date:
        print(f"  ✅ Using modification date (OLDEST: {oldest_date})")
    
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
        
        creation = dates.get('creation')
        modification = dates.get('modification')
        filename_date = dates.get('filename')
        
        print(f"  Creation date:    {creation}")
        print(f"  Modification date: {modification}")
        if filename_date:
            print(f"  Filename datetime: {filename_date}")
        
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
                    print(f"  Found: {file}")
    
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
    print(f"Supported video formats: {', '.join(sorted(VIDEO_EXTENSIONS))}")
    print(f"Metadata preservation: EXIF data including GPS coordinates for supported formats")
    print(f"Supported filename patterns: 15 different datetime formats")
    print(f"Date priority: ABSOLUTE OLDEST date from filename/creation/modification")
    print(f"Original files will be preserved with corrected dates")
    print(f"Copies with new names will be created in year folders")
    
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
    print(f"Camera information detected and preserved")
    print(f"GPS/Location data preserved where available")
    print(f"\nOrganization:")
    print(f"  Files organized in folders: 'Photos from YYYY'")
    print(f"  Naming pattern:")
    print(f"    Images: IMG_YYYYMMDD_HHMMSS_####.extension")
    print(f"    Videos: VID_YYYYMMDD_HHMMSS_####.extension")
    print(f"  Example: 'Photos from 2023/IMG_20230710_162352_0001.jpg'")

if __name__ == "__main__":
    main()