# Vizard AI Integration Testing Guide

## Prerequisites
1. **API Key**: Add your Vizard AI API key to `.env` file using `./add_vizard_key.sh`
2. **Environment Setup**: Ensure all Python dependencies are installed
3. **YouTube URL**: Have a valid YouTube trailer URL ready for testing

## Testing Steps

### 1. Basic API Connectivity Test
```bash
python -c "from ai.vizard_client import VizardAIClient; import os; client = VizardAIClient(os.environ.get('VIZARD_API_KEY')); print('API Key Set:', bool(client.api_key)); print('API Endpoint:', client.API_ENDPOINT)"
```

### 2. Single Component Test
Test just the highlight extraction component:
```bash
python -c "from ai.extract_highlights import extract_highlights_with_vizard; clips = extract_highlights_with_vizard('https://www.youtube.com/watch?v=sefHlA4neas', 'Test Movie', 1, 2, 'temp_clips'); print(f'Extracted {len(clips)} clips')"
```

### 3. Full Integration Test
Run the full integration test with debug information:
```bash
./vizard_direct_api_test.sh --debug https://www.youtube.com/watch?v=sefHlA4neas
```

### 4. Main Workflow Test
Test Vizard AI integration in the main StreamGank workflow:
```bash
python main.py --country US --platform Netflix --genre Action --content-type movie --use-vizard-ai --num-movies 1
```

## Troubleshooting

### Common Issues
1. **API Key Errors**: Ensure VIZARD_API_KEY is correctly set in `.env`
2. **HTTP Errors**: Check network connectivity to Vizard API
3. **Project Creation Failures**: Verify YouTube URL is valid and accessible
4. **Timeout Issues**: Some trailer processing may take longer than expected

### Debug Commands
Generate detailed API logs:
```bash
VIZARD_DEBUG=1 ./vizard_direct_api_test.sh --debug https://www.youtube.com/watch?v=sefHlA4neas
```

## Expected Output
A successful test should:
1. Connect to Vizard API
2. Create a project with the YouTube URL
3. Wait for processing to complete
4. Download highlight clips
5. Upload clips to Cloudinary
6. Display Cloudinary URLs
