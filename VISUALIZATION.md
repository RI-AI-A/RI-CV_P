# Real-Time Visualization Features

The CV service now displays a professional real-time visualization window with the following features:

## 🎨 Visual Elements

### 1. **Info Panel** (Top of screen)
- System title: "Retail Intelligence - Computer Vision System"
- Active track count
- Branch ID
- Semi-transparent black background

### 2. **Region of Interest (ROI)**
- Green semi-transparent overlay (10% opacity)
- Thick green border (3px)
- "Region of Interest" label with background

### 3. **Person Detection & Tracking**
Each detected person shows:
- **Bounding box** with color-coded status:
  - 🟢 **Green**: Person ENTERED the ROI
  - 🔴 **Red**: Person PASSED by without entering
  - 🟡 **Yellow**: Person currently IN ROI
  - 🔵 **Blue**: Person being TRACKED outside ROI
  
- **Labels** (stacked above bounding box):
  - Track ID (e.g., "ID:1")
  - Confidence score (e.g., "Conf:0.85")
  - Status (ENTERED/PASSED/IN ROI/TRACKING)
  - Customer UUID (first 8 characters)

- **Center point**: Colored dot with white outline

### 4. **Legend** (Top right)
- Color-coded legend explaining status colors
- Green = Entered
- Red = Passed
- Yellow = In ROI

## ⌨️ Keyboard Controls

- **Q**: Quit the application
- **P**: Pause/Resume (press any key to continue)

## 🎯 Use Cases

### For Frontend Integration
The visualization logic can be extracted and used to:
1. Stream processed frames to web frontend via WebSocket
2. Generate annotated video files for review
3. Create real-time dashboards
4. Export frames for training data

### For Demonstration
- Perfect for graduation project presentations
- Shows all CV capabilities in real-time
- Professional appearance with clear labeling
- Easy to understand color coding

## 📊 What You'll See

When running `./test_cv.sh`, you'll see:
1. Video playback with YOLO detections
2. People tracked with unique IDs
3. ROI boundary clearly marked
4. Status changes as people move (TRACKING → IN ROI → ENTERED/PASSED)
5. Confidence scores for each detection
6. Active track count updating in real-time

## 🔧 Technical Details

- **Frame Rate**: Processes at video FPS (typically 25-30 FPS)
- **Resolution**: Maintains original video resolution (1920x1080 for sample video)
- **Overlay**: Uses OpenCV's `addWeighted` for semi-transparent effects
- **Text Rendering**: Anti-aliased text with background rectangles for readability
- **Color Space**: BGR (OpenCV standard)

## 💡 Tips

- The visualization window will appear automatically when you run the CV service
- If the window doesn't appear, check your DISPLAY environment variable
- For headless servers, you can disable visualization by commenting out the `cv2.imshow()` line
- The visualization doesn't affect the core CV processing or API communication
