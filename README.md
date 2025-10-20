```markdown
# Media Date Organizer

A powerful Python tool for organizing and synchronizing media file dates with metadata preservation including GPS coordinates and camera information. This tool scans ALL directories and subdirectories to find media files, corrects their dates, and organizes them into year-based folders.

## Features

- **Comprehensive File Discovery**: Scans all directories and subdirectories for media files
- **Smart Date Detection**: Extracts dates from 15 different filename patterns
- **GPS & Camera Metadata**: Preserves EXIF data including GPS coordinates and camera information
- **Date Synchronization**: Uses the ABSOLUTE OLDEST available date from filename, creation, or modification dates
- **File Organization**: Automatically organizes files into "Photos from YYYY" folders
- **Standardized Naming**: Renames files to consistent format: `IMG_YYYYMMDD_HHMMSS_####.ext` for images and `VID_YYYYMMDD_HHMMSS_####.ext` for videos
- **Multi-format Support**: Handles images (JPEG, PNG, HEIC, WebP, etc.) and videos (MOV, MP4, AVI, etc.)
- **Non-destructive**: Original files are preserved with corrected dates, copies are created with new names
- **Optimized Performance**: Skips system directories for faster processing

## Supported File Formats

### Images
- **JPEG/JPG** (full EXIF + GPS support)
- **PNG** (limited EXIF support)
- **HEIC** (basic metadata preservation)
- **WebP** (EXIF + GPS support)
- **TIFF/TIF, BMP, RAW, GIF**

### Videos
- **MOV, MP4, AVI, MKV, WMV, FLV, WebM, M4V, 3GP**

## Supported Filename Patterns

The tool recognizes 15 different datetime patterns in filenames:
- `IMG20230710162352.jpg` (IMG + YYYYMMDDHHMMSS)
- `VID20240731092916.mp4` (VID + YYYYMMDDHHMMSS)
- `IMG_20230525_101125.jpg` (IMG_ + YYYYMMDD + time)
- `PXL_20230525_101125.jpg` (PXL_ + YYYYMMDD + time)
- `Screenshot_20230525-101125.jpg`
- `Signal-2023-05-25-10-11-25-123.jpg`
- And 9 more patterns...

## Installation

1. Clone this repository:
```bash
git clone https://github.com/WiktorProgramista/Media-Date-Organizer.git
cd Media-Date-Organizer
```

2. Install required dependencies:
```bash
pip install Pillow filedate
```

## Usage

### Basic Usage
```bash
python main.py --path /path/to/search --output /path/to/output
```

### Examples

**Process current directory and all subdirectories:**
```bash
python main.py --path . --output ./organized_photos
```

**Process specific folder and all its subdirectories:**
```bash
python main.py --path /Users/username/Pictures --output /Users/username/OrganizedPhotos
```

**Process entire drive:**
```bash
python main.py --path / --output /Volumes/External/OrganizedPhotos
```

### Parameters

- `--path`: Directory to search for media files (default: current directory, searches recursively)
- `--output`: Output directory for organized copies (required)

## How It Works

1. **Recursive Search**: Scans all directories and subdirectories for media files
2. **Date Analysis**: Extracts all available dates from each file:
   - Filename datetime patterns
   - File creation date
   - File modification date
3. **Date Determination**: Finds the ABSOLUTE OLDEST date from all sources
4. **Date Correction**: Corrects dates in original files to match the oldest date
5. **Copy Creation**: Creates copies with standardized names in year-based folders
6. **Metadata Preservation**: Preserves all metadata including GPS coordinates and camera information

## Output Structure

```
output_directory/
├── Photos from 2023/
│   ├── IMG_20230710_162352_0001.jpg
│   ├── VID_20230710_162415_0002.mp4
│   └── IMG_20230711_093000_0003.heic
├── Photos from 2024/
│   ├── IMG_20240115_120000_0001.jpg
│   └── VID_20240115_120030_0002.mov
└── ...
```

## Metadata Preservation

- **GPS Data**: Latitude/longitude coordinates preserved with Google Maps links
- **Camera Info**: Make, model, and software information
- **EXIF Data**: All EXIF metadata preserved for supported formats
- **File Dates**: Creation, modification, and access dates synchronized

## Performance Optimization

The tool automatically skips:
- Hidden directories (starting with `.`)
- `__pycache__` directories
- `node_modules` directories
- Other system directories

## Requirements

- Python 3.6+
- Pillow (PIL) for image processing
- filedate for date manipulation

## Use Cases

- **Photo Library Organization**: Organize years of scattered photos
- **Data Recovery**: Fix dates on recovered media files
- **Device Migration**: Standardize file names when moving between devices
- **Backup Preparation**: Prepare files for cloud backup with proper dates
- **Digital Archiving**: Create organized archives of family photos

## Example Output

```
🎬 Processing IMAGE: DSC_20230525_101125.jpg
  📱 Camera: SONY / ILCE-7M3
  📍 Location: 52.229675°N, 21.012229°E
  Creation date:    2023-05-25 10:11:25
  Modification date: 2023-05-25 10:11:25
  Filename datetime: 2023-05-25 10:11:25
  ✅ Using filename datetime (OLDEST: 2023-05-25 10:11:25)
  ✓ Dates are consistent, no correction needed
  ✓ Created year folder: Photos from 2023
  📸 Copying with metadata preservation...
  ✓ Copied with EXIF metadata (including GPS)
  ✅ Copy created in 'Photos from 2023': IMG_20230525_101125_0001.jpg
```

## License

This project is open source and available under the [MIT License](LICENSE).

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for bugs and feature requests.

## Author

Created by [WiktorProgramista](https://github.com/WiktorProgramista)
```

This README provides comprehensive documentation in English for the updated version of your Media Date Organizer that searches ALL directories. It highlights the key change (recursive search through all folders) while maintaining all the other important information about features, usage, and capabilities.
