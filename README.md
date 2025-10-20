# Media Date Organizer

A script for automatically correcting date metadata in multimedia files and organizing them into folders by year.

## 📋 Description

Media Date Organizer is an advanced Python tool that:
- **Corrects dates** in file metadata (creation and modification)
- **Organizes files** into folders by year
- **Renames files** to a standardized format
- **Supports various filename formats** with embedded dates

## ✨ Features

### 🔧 Date Correction
- Automatically detects the oldest available date
- Prioritizes the filename date if it is older than the system date
- Corrects both the creation and modification dates
- Preserves the original files with corrected metadata

### 📁 File Organization
- Creates `Photos from YEAR` folders (e.g., `Photos from 2023`)
- Automatically sorts by year
- Unique file naming with a counter

### 📸 Supported Formats
**Images:** JPG, JPEG, PNG, HEIC, BMP, TIFF, WEBP, RAW
**Videos:** MOV, MP4, AVI, MKV, WMV, FLV, WEBM, M4V, 3GP

## 🚀 Installation

### Requirements
- Python 3.6+
- `filedate` library

### Dependency Installation
```bash
pip install filedate
```

## 📖 Usage

### Basic Usage
```bash
python media_date_organizer.py --output ./organized_photos
```

### With a specified source folder
```bash
python media_date_organizer.py --path ./source_photos --output ./organized_photos
```

### Parameters
- `--path` - Path to Search (default: current folder)
- `--output` - Output folder (required)

## 🎯 Supported filename patterns

The script recognizes dates from the following filename formats:

### Full date with time
- `IMG20230710162352.jpg` → 2023-07-10 16:23:52
- `VID20240731092916.mp4` → 2024-07-31 09:29:16

### Date and time separated
- `IMG_20230525_101125.jpg` → 2023-05-25 10:11:25
- `PXL_20230525_101125.jpg` → 2023-05-25 10:11:25
- `20230525_101125.jpg` → 2023-05-25 10:11:25

### Date Only
- `IMG-20230525-WA0000.jpg` → 2023-05-25 00:00:00
- `IMG2023052512345.jpg` → 2023-05-25 00:00:00

### Special Formats
- `Screenshot_20230525-101125.jpg`
- `FB_IMG_20230525101125.jpg`
- `Signal-2023-05-25-10-11-25-123.jpg`

## 📊 Example in action

### Before processing
```
source_photos/
├── IMG20230710162352.jpg
├── IMG_20230815_143022.jpg
├── vacation_photo.jpg (system date: 2023-12-25)
└── VID20240120120000.mp4
```

### After processing
```
organized_photos/
├── Photos from 2023/
│ ├── IMG_20230710_162352_0001.jpg
│ ├── IMG_20230815_143022_0002.jpg
│ └── IMG_20231225_000000_0003.jpg
└── Photos from 2024/
└── VID_20240120_120000_0004.mp4
```

## ⚙️ Operational Logic

### Date Priorities
1. **Date from the file name** - if it is older than the system date
2. **Oldest system date** - if the name does not contain a date
3. **Current date** - as a last resort

### Output File Name Structure
- **Images:** `IMG_YYYYMMDD_HHMMSS_####.ext`
- **Video:** `VID_YYYYMMDD_HHMMSS_####.ext`

Example: `IMG_20230710_162352_0001.jpg`

## 🛠️ Development

### Adding New Patterns
Patterns are defined in the `DATE_PATTERNS` variable using regular expressions.

### Extending Functionality
The script can be easily extended with:
- Support for additional file formats
- New naming patterns
- Alternative organization strategies

## 📄 License

MIT License - free to use, modify, and distribute.

## 🤝 Contributing

We encourage you to submit issues and pull requests!

--

**Note:** The script creates copies of the files in a new structure; the original files remain unchanged (except for date metadata).
