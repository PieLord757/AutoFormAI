# AI Batch Form Filler

Generate multiple automated responses to Google Forms using AI.

## Features

- ✅ **Batch Processing**: Generate 1-1000+ responses in one run
- ✅ **Rate Limiting**: Automatic delays to respect API limits (15 RPM default)
- ✅ **Progress Tracking**: Real-time progress indicators
- ✅ **Variation**: Responses vary between runs using temperature and variation seeds
- ✅ **Error Handling**: Continues on failure, reports success/failure counts
- ✅ **Output File**: Saves all URLs to a file (default: `responses.txt`)

## Installation

```bash
pip install -r requirements.txt
```

Make sure you have your `GEMINI_API_KEY` set in `.env`:

```
GEMINI_API_KEY=your_api_key_here
```

## Usage

### Basic Usage (Single Response)
```bash
python python/ai_batch_form.py --form-url "YOUR_GOOGLE_FORM_URL"
```

### Batch Processing (50 Responses)
```bash
python python/ai_batch_form.py --form-url "YOUR_FORM_URL" --batch 50
```

### Custom Output File
```bash
python python/ai_batch_form.py --form-url "YOUR_FORM_URL" --batch 100 --output my_responses.txt
```

### Adjust Variation (Higher Temperature = More Random)
```bash
python python/ai_batch_form.py --form-url "YOUR_FORM_URL" --batch 50 --temperature 1.5
```

### Custom Rate Limiting
```bash
python python/ai_batch_form.py --form-url "YOUR_FORM_URL" --batch 50 --delay 5
```

## CLI Arguments

| Argument | Description | Default |
|----------|-------------|---------|
| `--form-url` | Google Form URL to process | Required |
| `--batch` | Number of responses to generate | 1 |
| `--output` | Output file path | `responses.txt` |
| `--delay` | Delay between API requests (seconds) | 4.0 |
| `--temperature` | AI randomness level (0.0-2.0) | 1.2 |
| `--model-name` | AI model to use | `gemini-2.0-flash-exp` |

## API Usage Limits

**Google Gemini 2.0 Flash (Free Tier):**
- 15 requests per minute (RPM)
- 1,500 requests per day (RPD)
- ~1 million tokens per day

**Recommendations:**
- For 50 responses: ~4 minutes (with default 4s delay)
- For 100 responses: ~7 minutes
- For 1,500 responses: ~100 minutes (~1.5 hours)

## Examples

### Generate 50 varied responses quickly
```bash
python python/ai_batch_form.py \
  --form-url "https://docs.google.com/forms/d/e/YOUR_FORM_ID/viewform" \
  --batch 50 \
  --temperature 1.5 \
  --delay 4
```

### Generate 500 responses overnight
```bash
python python/ai_batch_form.py \
  --form-url "YOUR_FORM_URL" \
  --batch 500 \
  --output overnight_responses.txt \
  --delay 4
```

## Output Format

The script generates a file with one pre-filled Google Form URL per line:

```
https://docs.google.com/forms/d/e/FORM_ID/viewform?entry.123=Answer1&entry.456=Answer2...
https://docs.google.com/forms/d/e/FORM_ID/viewform?entry.123=Answer3&entry.456=Answer4...
https://docs.google.com/forms/d/e/FORM_ID/viewform?entry.123=Answer5&entry.456=Answer6...
```

Each URL can be opened in a browser to submit that response to the form.

## Tips for Best Results

1. **Higher Temperature (1.2-1.8)**: More variation between responses
2. **Lower Temperature (0.5-0.9)**: More consistent, predictable responses
3. **Respect Rate Limits**: Keep delay at 4s or higher to avoid API throttling
4. **Monitor Progress**: The script shows real-time progress and failures
5. **Check Output**: Preview first few URLs to verify responses look correct

## Troubleshooting

**All responses are identical:**
- Increase `--temperature` (try 1.5-1.8)
- The variation seed should help, but higher temperature increases randomness

**API errors:**
- Check your `GEMINI_API_KEY` is valid
- Increase `--delay` if hitting rate limits
- Make sure you haven't exceeded daily quota (1,500 requests/day)

**"Form not found" errors:**
- Verify the form URL is public and accessible
- Make sure URL includes `/viewform` at the end
- Test URL in browser first

## Comparison: Single vs Batch Script

| Feature | `ai_form.py` | `ai_batch_form.py` |
|---------|--------------|---------------------|
| Single response | ✅ | ✅ |
| Batch processing | ❌ | ✅ |
| Rate limiting | ❌ | ✅ |
| Progress tracking | ❌ | ✅ |
| Output to file | ❌ | ✅ |
| Response variation | Limited | ✅ Enhanced |

Use `ai_form.py` for testing/debugging single responses.  
Use `ai_batch_form.py` for production batch generation.
