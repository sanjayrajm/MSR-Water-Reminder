import os
import sys
import time
import cv2
import subprocess
import tkinter as tk
from datetime import datetime
from PIL import Image, ImageTk
from ultralytics import YOLO

APP_NAME = "MSR Water Reminder"
REMINDER_MINUTES = 60
CAMERA_INDEX = 0

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_FOLDER = os.path.join(os.path.expanduser("~"), "WaterReminder", "Captured")
os.makedirs(SAVE_FOLDER, exist_ok=True)
MODEL_PATH = os.path.join(BASE_DIR, "yolo11n.pt")


def enable_startup():
    if getattr(sys, "frozen", False):
        command = f'"{sys.executable}"'
    else:
        pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
        script = os.path.abspath(__file__)
        command = f'"{pythonw}" "{script}"'
    registry_command = (
        'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" '
        f'/v "{APP_NAME}" /t REG_SZ /d \'{command}\' /f'
    )
    subprocess.run(registry_command, shell=True, creationflags=subprocess.CREATE_NO_WINDOW, check=False)


class WaterReminder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.withdraw()
        self.camera = None
        self.camera_running = False
        self.reminder_window = None
        self.camera_label = None
        self.status_label = None
        self.captured = False
        self.reminder_open = False
        self.model = None
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        if self.face_cascade.empty():
            raise RuntimeError("OpenCV face detector could not be loaded.")
        enable_startup()
        self.load_model()
        self.next_reminder = time.time() + REMINDER_MINUTES * 60
        self.check_reminder()
        self.root.mainloop()

    def load_model(self):
        try:
            self.model = YOLO(MODEL_PATH if os.path.exists(MODEL_PATH) else "yolo11n.pt")
        except Exception as exc:
            print(f"YOLO load error: {exc}")
            self.model = None

    def check_reminder(self):
        now = time.time()
        if now >= self.next_reminder and not self.reminder_open:
            self.show_reminder()
            self.next_reminder = now + REMINDER_MINUTES * 60
        self.root.after(1000, self.check_reminder)

    def show_reminder(self):
        self.reminder_open = True
        self.captured = False
        self.reminder_window = tk.Toplevel(self.root)
        window = self.reminder_window
        window.attributes("-fullscreen", True)
        window.attributes("-topmost", True)
        window.configure(bg="black")
        window.protocol("WM_DELETE_WINDOW", self.close_reminder)
        tk.Label(window, text="DRINK WATER", font=("Segoe UI", 36, "bold"), fg="white", bg="black").pack(pady=(25, 5))
        tk.Label(window, text="Show your face and water bottle", font=("Segoe UI", 18), fg="white", bg="black").pack(pady=(0, 10))
        self.camera_label = tk.Label(window, bg="black")
        self.camera_label.pack(expand=True)
        self.status_label = tk.Label(window, text="Opening camera...", font=("Segoe UI", 18, "bold"), fg="white", bg="black")
        self.status_label.pack(pady=15)
        tk.Button(window, text="X", font=("Segoe UI", 18, "bold"), fg="white", bg="#222222", activebackground="#444444", activeforeground="white", border=0, command=self.close_reminder).place(x=20, y=20, width=60, height=60)
        self.start_camera()

    def start_camera(self):
        if self.camera_running:
            return
        self.camera = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.camera.isOpened():
            self.status_label.config(text="CAMERA NOT FOUND")
            self.camera.release()
            self.camera = None
            return
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.camera_running = True
        self.update_camera()

    def update_camera(self):
        if not self.camera_running or self.camera is None:
            return
        ok, frame = self.camera.read()
        if not ok:
            self.root.after(100, self.update_camera)
            return
        frame = cv2.flip(frame, 1)
        face_detected = False
        bottle_detected = False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces):
            face_detected = True
            for x, y, w, h in faces:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 255), 2)
                cv2.putText(frame, "FACE", (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if self.model is not None:
            try:
                results = self.model(frame, verbose=False, conf=0.40)
                for result in results:
                    for box in result.boxes:
                        class_id = int(box.cls[0])
                        confidence = float(box.conf[0])
                        class_name = str(self.model.names[class_id]).lower()
                        if class_name == "bottle":
                            bottle_detected = True
                            x1, y1, x2, y2 = map(int, box.xyxy[0])
                            cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 255, 255), 3)
                            cv2.putText(frame, f"BOTTLE {confidence:.0%}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            except Exception as exc:
                print(f"Detection error: {exc}")
        if face_detected and bottle_detected:
            self.status_label.config(text="FACE + BOTTLE DETECTED")
            if not self.captured:
                self.capture_photo(frame)
        elif face_detected:
            self.status_label.config(text="FACE DETECTED - SHOW WATER BOTTLE")
        elif bottle_detected:
            self.status_label.config(text="BOTTLE DETECTED - SHOW YOUR FACE")
        else:
            self.status_label.config(text="SHOW YOUR FACE + WATER BOTTLE")
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(rgb)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        image.thumbnail((int(sw * 0.75), int(sh * 0.65)), Image.Resampling.LANCZOS)
        photo = ImageTk.PhotoImage(image)
        self.camera_label.configure(image=photo)
        self.camera_label.image = photo
        self.root.after(30, self.update_camera)

    def capture_photo(self, frame):
        if self.captured:
            return
        self.captured = True
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filepath = os.path.join(SAVE_FOLDER, f"water_{timestamp}.jpg")
        if cv2.imwrite(filepath, frame):
            self.status_label.config(text="WATER RECORDED!")
            self.root.after(1500, self.close_reminder)
        else:
            self.status_label.config(text="PHOTO SAVE FAILED")
            self.captured = False

    def close_reminder(self):
        self.camera_running = False
        if self.camera is not None:
            try:
                self.camera.release()
            except Exception:
                pass
            self.camera = None
        if self.reminder_window is not None:
            try:
                self.reminder_window.destroy()
            except Exception:
                pass
            self.reminder_window = None
        self.reminder_open = False
        self.next_reminder = time.time() + REMINDER_MINUTES * 60


if __name__ == "__main__":
    WaterReminder()
