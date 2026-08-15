# MSR Water Reminder

A Windows background water reminder built with Python.

## Features

- Runs in the Windows background
- Registers itself in Windows Startup Apps
- Configurable reminder interval
- Full-screen drinking-water reminder
- Live webcam preview
- Face detection
- Water-bottle detection with YOLO
- Automatically captures a photo when both face and bottle are visible
- Saves photos locally
- Releases the camera after the reminder

## Installation

```bat
python -m pip install -r requirements.txt
python water_reminder.py
```

The first run downloads the YOLO model automatically.

## Reminder interval

Edit `REMINDER_MINUTES` in `water_reminder.py`. Use `1` for testing and `60` for hourly reminders.

## Captured photos

Saved locally to `C:\Users\<your-user>\WaterReminder\Captured`.

## Privacy

The camera is opened only when a reminder is displayed. Captures are stored locally and are not uploaded by this application.

## License

MIT License.
