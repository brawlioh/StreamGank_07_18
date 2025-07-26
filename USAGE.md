# StreamGank Automated Video Generator - Usage Guide

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Method 1: Use the setup script
python setup.py

# Method 2: Manual installation
pip install -r requirements.txt
python -m playwright install
```

### 2. Set Up Environment Variables

Create a `.env` file in your project directory:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key

# HeyGen Configuration
HEYGEN_API_KEY=your_heygen_api_key

# Creatomate Configuration
CREATOMATE_API_KEY=your_creatomate_api_key

# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
```

## 📋 Usage Options

### Full End-to-End Workflow (Default)

```bash
# Basic usage (defaults: FR, Netflix, Horror, TV Series, 3 movies)
python automated_video_generator.py --all

# Custom parameters
python automated_video_generator.py --country FR --platform Netflix --genre Horreur --content-type Film --num-movies 3

# With output file
python automated_video_generator.py --all --output results.json
```

### Process Existing HeyGen Videos

```bash
# From JSON file
python automated_video_generator.py --process-heygen heygen_videos.json

# From command line JSON
python automated_video_generator.py --heygen-ids '{"movie1":"video_id_1","movie2":"video_id_2","movie3":"video_id_3"}'
```

## 🔧 Key Features

### ✅ What's New (Using HeyGen Status API)

-   **Direct HeyGen URL retrieval** using `https://api.heygen.com/v1/video_status.get?video_id=`
-   **No intermediate downloads** - passes URLs directly to Creatomate
-   **Faster processing** with reduced latency
-   **Better reliability** with comprehensive error handling

### 🎬 Full Workflow Steps

1. **Screenshot Capture**: Mobile format screenshots from StreamGank
2. **Database Query**: Extract top movies by IMDB score with strict filtering
3. **AI Script Generation**: Create tailored scripts for each video segment
4. **HeyGen Video Creation**: Generate avatar videos using AI
5. **Status Monitoring**: Wait for HeyGen completion using official API
6. **Creatomate Integration**: Create final video using direct URLs
7. **Results**: Complete video ready for publication

### 📊 Database Integration

-   **Strict filtering**: Matches StreamGank parameters exactly
-   **IMDB sorting**: Returns highest-rated movies first
-   **Multi-table joins**: movies ↔ movie_localizations ↔ movie_genres
-   **Fallback handling**: Graceful degradation if database unavailable

## 📁 File Structure

```
StreamGank_07_18/
├── automated_video_generator.py       # Main script with full workflow
├── automated_video_generator_concise.py  # Simplified version
├── streamgank_helpers.py              # 🆕 Country-specific mapping helpers
├── requirements.txt                   # Python dependencies
├── setup.py                          # Automated setup script
├── USAGE.md                          # This usage guide
├── .env                              # Environment variables (create this)
├── screenshots/                      # Generated screenshots
├── videos/                           # Generated videos and scripts
└── output/                           # Results and logs
```

### 🆕 StreamGank Helpers Module

The new `streamgank_helpers.py` contains centralized mapping functions:

**Core Functions:**

-   `build_streamgank_url()` - Complete URL builder with localization
-   `get_genre_mapping_by_country()` - Genre name translations
-   `get_platform_mapping_by_country()` - Platform name mappings
-   `get_content_type_mapping_by_country()` - Content type mappings

**Utility Functions:**

-   `get_supported_countries()` - List of supported country codes
-   `get_available_genres_for_country()` - Available genres per country
-   `get_all_mappings_for_country()` - All mappings for a country

**Supported Countries:**

-   **🇫🇷 FR**: Full French localization (Horreur, Comédie, etc.)
-   **🇺🇸 US/GB/UK/CA/AU**: English localization

**Benefits:**

-   ✅ Modular and reusable across projects
-   ✅ Centralized mapping logic
-   ✅ Easy to extend for new countries
-   ✅ Cross-language support (English ↔ French)

## 🔍 Troubleshooting

### Common Issues

1. **ModuleNotFoundError**: Run `python setup.py` to install all dependencies
2. **Playwright browser errors**: Run `python -m playwright install`
3. **API key errors**: Check your `.env` file configuration
4. **Database connection**: Verify SUPABASE_URL and SUPABASE_KEY

### Script Exits with "No Movies Found"

**Behavior**: The script now stops execution immediately if no movies are found matching your criteria.

**Error Messages**:

```
❌ NO MOVIES FOUND in database matching criteria: country=XX, genre=YY, platform=ZZ, content_type=WW
🛑 STOPPING SCRIPT EXECUTION - No content available for video generation
💡 Try different filter criteria (country, genre, platform, or content-type)
```

**Solutions**:

-   Try different filter combinations (country, genre, platform, content-type)
-   Use `--debug` flag to see available database content
-   Check if your Supabase database connection is working
-   Verify that data exists for your chosen criteria

**Note**: The script no longer uses simulated/fallback data when no real movies are found. This ensures that your videos are based on actual database content only.

### Debug Mode

```bash
python automated_video_generator.py --all --debug
```

## 📖 Examples

### Example 1: French Horror Films on Netflix

```bash
python automated_video_generator.py --country FR --platform Netflix --genre Horreur --content-type Film
```

### Example 2: Process Existing HeyGen Videos

```json
// heygen_videos.json
{
    "movie1": "abc123def456",
    "movie2": "def456ghi789",
    "movie3": "ghi789jkl012"
}
```

```bash
python automated_video_generator.py --process-heygen heygen_videos.json --output final_results.json
```

## 🎯 Expected Output

-   **Screenshots**: Mobile-format StreamGank captures
-   **Movie Data**: Top-rated movies with complete metadata
-   **Scripts**: AI-generated promotional content
-   **HeyGen Videos**: Professional avatar presentations
-   **Final Video**: Complete promotional video via Creatomate

## 🆘 Support

Check the console output for detailed logging and error messages. All operations include comprehensive progress feedback and error handling.
