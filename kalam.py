import sounddevice as sd
import queue
import json
import sys
import os
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox, filedialog
from vosk import Model, KaldiRecognizer
from datetime import datetime
import numpy as np
import wave
from pydub import AudioSegment
import tempfile

MODEL_PATH = "vosk-model-ar-0.22-linto-1.1.0"  # النموذج الصغير أسرع
if not os.path.exists(MODEL_PATH):
    messagebox.showerror("خطأ", f"النموذج غير موجود: {MODEL_PATH}")
    sys.exit()

model = Model(MODEL_PATH)
recognizer = KaldiRecognizer(model, 16000)
recognizer.SetWords(True)
q = queue.Queue()
stop_flag = False
volume_level = 1.0

def callback(indata, frames, time, status):
    global volume_level
    if status:
        print(status, file=sys.stderr)
    audio = np.frombuffer(indata, dtype=np.int16)
    audio = np.clip(audio * volume_level, -32768, 32767).astype(np.int16)
    q.put(audio.tobytes())

def transcribe_live():
    global stop_flag
    session_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_file = f"transcription_{session_time}.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        try:
            with sd.RawInputStream(samplerate=16000, blocksize=4000, dtype='int16',
                                   channels=1, callback=callback):
                while not stop_flag:
                    data = q.get()
                    if recognizer.AcceptWaveform(data):
                        result = json.loads(recognizer.Result())
                        text = result.get("text", "").strip()
                        if text:
                            text_box.insert(tk.END, text + "\n")
                            text_box.see(tk.END)
                            f.write(text + "\n")
        except Exception as e:
            messagebox.showerror("خطأ", str(e))
    status_label.config(text="تم الإيقاف")

def start_transcription():
    global stop_flag
    stop_flag = False
    threading.Thread(target=transcribe_live, daemon=True).start()
    status_label.config(text="🎤 يتم التسجيل الآن...")

def stop_transcription():
    global stop_flag
    stop_flag = True
    status_label.config(text="💾 جاري الحفظ...")

def set_volume(val):
    global volume_level
    volume_level = float(val) / 100.0

def transcribe_from_file():
    file_path = filedialog.askopenfilename(filetypes=[("Audio Files", "*.wav *.mp3 *.m4a *.ogg")])
    if not file_path:
        return

    # تحويل الملف إلى wav بالمواصفات المطلوبة
    try:
        audio = AudioSegment.from_file(file_path)
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    except Exception as e:
        messagebox.showerror("خطأ", f"تعذر قراءة الملف الصوتي:\n{str(e)}")
        return

    with tempfile.NamedTemporaryFile(suffix=".wav") as temp_wav:
        audio.export(temp_wav.name, format="wav")

        recognizer.Reset()
        text_box.insert(tk.END, f"\n📂 تحليل الملف: {os.path.basename(file_path)}\n")
        text_box.see(tk.END)

        wf = wave.open(temp_wav.name, "rb")

        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if recognizer.AcceptWaveform(data):
                result = json.loads(recognizer.Result())
                text = result.get("text", "").strip()
                if text:
                    text_box.insert(tk.END, text + "\n")
                    text_box.see(tk.END)

        final_res = json.loads(recognizer.FinalResult())
        if final_res.get("text", "").strip():
            text_box.insert(tk.END, final_res["text"] + "\n")
            text_box.see(tk.END)

        wf.close()
        status_label.config(text="✅ تم الانتهاء من تحليل الملف")

# واجهة المستخدم
root = tk.Tk()
root.title("تسجيل/تحويل الكلام إلى نص مع رفع ملف صوتي")
root.geometry("700x500")

start_button = tk.Button(root, text="ابدأ التسجيل", command=start_transcription, bg="green", fg="white", font=("Arial", 12))
start_button.pack(pady=5)

stop_button = tk.Button(root, text="أوقف التسجيل", command=stop_transcription, bg="red", fg="white", font=("Arial", 12))
stop_button.pack(pady=5)

file_button = tk.Button(root, text="📂 رفع ملف صوتي", command=transcribe_from_file, bg="blue", fg="white", font=("Arial", 12))
file_button.pack(pady=5)

volume_label = tk.Label(root, text="🔊 مستوى الصوت", font=("Arial", 12))
volume_label.pack(pady=5)

volume_slider = tk.Scale(root, from_=0, to=200, orient=tk.HORIZONTAL, length=300, command=set_volume)
volume_slider.set(100)
volume_slider.pack(pady=5)

status_label = tk.Label(root, text="📌 في انتظار بدء التسجيل أو رفع ملف...", fg="blue", font=("Arial", 12))
status_label.pack(pady=5)

text_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, font=("Arial", 12))
text_box.pack(expand=True, fill="both")

root.mainloop()
