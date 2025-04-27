# DTS to EAC3 Converter API

A FastAPI-based service that automatically converts DTS audio tracks to EAC3 format in video files while preserving the original bitrate.

## Features

- Convert DTS audio tracks to EAC3 while keeping other streams intact
- Process single files or entire directories recursively
- Maintain original audio bitrate
- Real-time conversion status tracking
- Telegram notifications support
- RESTful API interface

## Prerequisites

- Python 3.8+
- FFmpeg with DTS and EAC3 support

## Installation

1. Clone the repository:
```bash
git clone https://github.com/anasrih/dts-converter.git
cd dts-converter
```

2. Run the setup script to create virtual environment and install dependencies:
```bash
chmod +x setup.sh
./setup.sh
```

The setup script will:
- Check for required system dependencies (Python3, pip, ffmpeg)
- Create a Python virtual environment
- Install all required Python packages
- Create a startup script

## Usage

1. Start the API server using the provided startup script:
```bash
./start_api.sh
```

This script automatically:
- Activates the virtual environment
- Starts the FastAPI server with uvicorn
- Enables auto-reload for development
- Makes the API available on all network interfaces (0.0.0.0)

2. The API will be available at:
- API endpoint: `http://localhost:8000`
- Interactive documentation: `http://localhost:8000/docs`

### API Endpoints

- `POST /convert/`
  - Convert a single file or directory
  - Body: `{"path": "/path/to/video/or/directory"}`

- `GET /conversions/`
  - List all conversions with their status

### Example API Calls

Convert a single file:
```bash
curl -X POST "http://localhost:8000/convert/" -H "Content-Type: application/json" -d '{"path":"/path/to/video.mkv"}'
```

Get conversion status:
```bash
curl "http://localhost:8000/conversions/"
```

## Features Details

- Automatic detection of DTS audio tracks
- Preserves all other streams (video, subtitles, other audio tracks)
- Maintains original metadata
- Progress tracking with unique conversion IDs
- Real-time status updates
- Telegram notifications for conversion events

## Configuration

### Telegram Notifications

To enable Telegram notifications:
1. Edit `dts_to_eac3.py`
2. Set your `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`
3. Set `SEND_TELEGRAM_NOTIFICATION` to "O" to enable notifications

## Error Handling

- Validates input files
- Checks for video file compatibility
- Reports detailed conversion errors
- Preserves original files in case of failure


## Acknowledgments

- FFmpeg for video processing capabilities
- FastAPI for the web framework
- Telegram API for notifications

## Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request