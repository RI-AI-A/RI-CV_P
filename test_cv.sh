#!/bin/bash
# Run CV service with sample video - simplified version

echo "🎥 Starting CV Service with sample video..."
echo ""

# Activate virtual environment
source venv/bin/activate

# Set environment variables
export CV_BRANCH_ID="branch_001"
export CV_VIDEO_SOURCE="$(pwd)/data/retail_sample.mp4"
export CV_ROI_COORDINATES="400,200,1500,900"
export YOLO_MODEL_PATH="yolov8n.pt"
export YOLO_CONFIDENCE_THRESHOLD="0.5"
export TRACKER_TYPE="bytetrack"
export TRACKER_MAX_AGE="30"
export TRACKER_MIN_HITS="3"
export API_BASE_URL="http://localhost:8000"
export LOG_LEVEL="INFO"
export DATABASE_URL="postgresql+asyncpg://retail_user:retail_pass@localhost:5432/retail_intel"

echo "✅ Configuration:"
echo "  Video: $CV_VIDEO_SOURCE"
echo "  ROI: $CV_ROI_COORDINATES"
echo "  Branch: $CV_BRANCH_ID"
echo "  API: $API_BASE_URL"
echo ""
echo "🚀 Starting CV processing..."
echo "   (First run will download YOLOv8 model ~6MB)"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Run CV service
python -m cv_service.stream_processor
