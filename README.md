# Hands Detector

A hand detection app that uses your webcam to track your hands. Includes a couple of games you can play with hand gestures.

This app uses **MediaPipe** for hand tracking, which provides real-time hand detection and landmark tracking.

## Requirements

- **Python 3.11** (other versions might work but 3.11 is tested)
- **Windows** (Linux/Mac support coming later)
- A webcam

## Installation

### Step 1: Install Python dependencies

Open a terminal in the project folder and run:

```bash
pip install -r requirements.txt
```

If `pip` doesn't work, try using Python directly:

```bash
python -m pip install -r requirements.txt
```

Or if Python isn't in your PATH, use the full path:

```bash
F:\Python-311\python.exe -m pip install -r requirements.txt
```

This will install:
- MediaPipe (hand detection)
- OpenCV (camera and video processing)
- NumPy (math stuff)
- Pygame (sound for piano game)

### Step 2: Configure Python path

If Python isn't in your system PATH, you need to tell the script where to find it:

1. Open `run.bat` in a text editor
2. Look for the line that says `F:\Python-311\python.exe` (around line 20)
3. Replace `F:\Python-311\python.exe` with your actual Python installation path
4. Save the file

The script will try to find Python automatically, but if it fails, this is your backup.

### Step 3: Configure games (optional)

Open `config.json` and you'll see a `GAMES` section:

```json
"GAMES": {
    "piano_game": false,
    "coins_game": true
}
```

- Set `piano_game` to `true` to play the piano with your fingers
- Set `coins_game` to `true` to play the coin collecting game

**Important**: Only enable **one game at a time**. Enabling multiple games simultaneously can cause bugs and weird behavior.

### Step 4: Enable GPU mode (recommended)

For better performance and smoother tracking, it's recommended to enable GPU mode. In `config.json`, set:

```json
"gpu_mode": true
```

This will use your GPU to accelerate MediaPipe's hand detection, making the app run much more smoothly. If you don't have a compatible GPU or experience issues, you can set it to `false` to use CPU mode instead.

## Running the App

### Option 1: Double-click `run.bat`

The easiest way. Just double-click the `run.bat` file and it should start.

### Option 2: Command line

```bash
python main.py
```

Or if Python isn't in PATH:

```bash
F:\Python-311\python.exe main.py
```

## Controls

While the app is running:

- **`q`** - Quit the application
- **`d`** or **Right Arrow** - Switch to next camera (if you have multiple)
- **`a`** or **Left Arrow** - Switch to previous camera
- **`0-9`** - Select a specific camera by number

## Games

### Piano Game

When enabled, each finger plays a different note. Lower your fingers to play notes. Each hand has 5 different notes (10 total).

### Coins Game

Collect yellow coins with your hands while avoiding the black bouncing ball. Each coin gives you 1 point. Touch the black ball and you lose - the game will restart automatically after 5 seconds.

## Troubleshooting

- **Camera not found**: Make sure your webcam is connected and not being used by another app
- **Python not found**: Check the Python path in `run.bat` or add Python to your system PATH
- **Import errors**: Make sure you installed all requirements with `pip install -r requirements.txt`
- **Games not working**: Make sure only one game is enabled in `config.json`

