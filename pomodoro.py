import math
import os
import time
import ctypes
import tkinter as tk
import winsound

from PIL import Image, ImageDraw, ImageFont, ImageTk
from screeninfo import get_monitors


def set_dpi_awareness():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def set_app_user_model_id():
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            "Pomodoro.Taskbar.Timer"
        )
    except Exception:
        pass


class BreakOverlayManager:
    def __init__(self, root):
        self.root = root
        self.windows = []
        self.labels = []

    def _format_mmss(self, total_sec: int) -> str:
        minutes = total_sec // 60
        seconds = total_sec % 60
        return f"{minutes:02d}:{seconds:02d}"

    def show(self, remaining_sec: int):
        self.hide()

        try:
            monitors = get_monitors()
        except Exception:
            monitors = []

        if not monitors:
            class DummyMonitor:
                x = 0
                y = 0
                width = self.root.winfo_screenwidth()
                height = self.root.winfo_screenheight()

            monitors = [DummyMonitor()]

        text = f"Break Time\n{self._format_mmss(remaining_sec)}"

        for monitor in monitors:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            win.geometry(
                f"{monitor.width}x{monitor.height}+{monitor.x}+{monitor.y}"
            )
            win.configure(bg="black")

            try:
                win.attributes("-topmost", True)
                win.attributes("-alpha", 0.90)
            except Exception:
                pass

            frame = tk.Frame(win, bg="black")
            frame.place(relx=0.5, rely=0.5, anchor="center")

            label = tk.Label(
                frame,
                text=text,
                fg="white",
                bg="black",
                font=("Segoe UI", 36, "bold"),
                justify="center",
            )
            label.pack()

            win.bind("<Button>", lambda e: "break")
            win.bind("<Key>", lambda e: "break")

            try:
                win.focus_force()
            except Exception:
                pass

            self.windows.append(win)
            self.labels.append(label)

    def update(self, remaining_sec: int):
        text = f"Break Time\n{self._format_mmss(remaining_sec)}"
        for label in self.labels:
            try:
                label.config(text=text)
            except Exception:
                pass

    def hide(self):
        for win in self.windows:
            try:
                win.destroy()
            except Exception:
                pass
        self.windows.clear()
        self.labels.clear()


class PomodoroTaskbarApp:
    def __init__(self, work_minutes=25, break_minutes=3):
        self.work_seconds = work_minutes * 60
        self.break_seconds = break_minutes * 60

        self.mode = "work"
        self.remaining = self.work_seconds
        self.paused = False
        self.running = True

        self.root = tk.Tk()
        self.root.title("Pomodoro - Work - Remaining 25:00")
        self.root.geometry("300x145")
        self.root.resizable(False, False)

        self.overlay = BreakOverlayManager(self.root)

        self.icon_refs = []
        self.last_tick = time.monotonic()

        self._build_ui()
        self._update_all_visuals()

        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_taskbar)

        self.root.after(200, self.minimize_to_taskbar)
        self.root.after(200, self._tick)

    def _build_ui(self):
        self.root.configure(bg="#111111")

        self.status_label = tk.Label(
            self.root,
            text="Work Session",
            fg="white",
            bg="#111111",
            font=("Segoe UI", 12, "bold"),
        )
        self.status_label.pack(pady=(12, 4))

        self.time_label = tk.Label(
            self.root,
            text="25:00",
            fg="white",
            bg="#111111",
            font=("Segoe UI", 28, "bold"),
        )
        self.time_label.pack(pady=(0, 10))

        button_frame = tk.Frame(self.root, bg="#111111")
        button_frame.pack(pady=(0, 10))

        self.pause_button = tk.Button(
            button_frame,
            text="Pause",
            width=10,
            command=self.toggle_pause,
        )
        self.pause_button.grid(row=0, column=0, padx=4, pady=4)

        self.restart_cycle_button = tk.Button(
            button_frame,
            text="Restart Cycle",
            width=12,
            command=self.restart_cycle,
        )
        self.restart_cycle_button.grid(row=0, column=1, padx=4, pady=4)

        self.restart_work_button = tk.Button(
            button_frame,
            text="Restart Work",
            width=12,
            command=self.restart_work,
        )
        self.restart_work_button.grid(row=1, column=0, padx=4, pady=4)

        self.hide_button = tk.Button(
            button_frame,
            text="Hide",
            width=10,
            command=self.minimize_to_taskbar,
        )
        self.hide_button.grid(row=1, column=1, padx=4, pady=4)

        self.quit_button = tk.Button(
            self.root,
            text="Quit",
            width=10,
            command=self.quit_app,
        )
        self.quit_button.pack(pady=(0, 10))

    def _format_mmss(self, total_sec: int) -> str:
        minutes = total_sec // 60
        seconds = total_sec % 60
        return f"{minutes:02d}:{seconds:02d}"

    def _display_minutes(self) -> str:
        minutes = math.ceil(self.remaining / 60)
        return str(max(0, minutes))

    def _window_title(self) -> str:
        mode_text = "Work" if self.mode == "work" else "Break"
        paused_text = " - Paused" if self.paused else ""
        return (
            f"Pomodoro - {mode_text}{paused_text} - Remaining "
            f"{self._format_mmss(self.remaining)}"
        )

    def _load_font(self, size: int):
        candidates = [
            r"C:\Windows\Fonts\segoeuib.ttf",
            r"C:\Windows\Fonts\arialbd.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
            r"C:\Windows\Fonts\arial.ttf",
        ]
        for path in candidates:
            if os.path.exists(path):
                try:
                    return ImageFont.truetype(path, size=size)
                except Exception:
                    pass
        return ImageFont.load_default()

    def _create_base_icon(self, size: int = 256) -> Image.Image:
        image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        margin = int(size * 0.10)
        ring_width = max(10, int(size * 0.11))
        bbox = [margin, margin, size - margin, size - margin]

        draw.arc(
            bbox,
            start=0,
            end=359,
            fill=(110, 110, 110, 140),
            width=ring_width,
        )

        if self.mode == "work":
            total = self.work_seconds
            ring_color = (230, 90, 70, 255)
        else:
            total = self.break_seconds
            ring_color = (70, 180, 110, 255)

        ratio = max(0.0, min(1.0, self.remaining / total))
        end_angle = -90 + (360 * ratio)

        if ratio > 0:
            draw.arc(
                bbox,
                start=-90,
                end=end_angle,
                fill=ring_color,
                width=ring_width,
            )

        text = self._display_minutes()
        font_size = int(size * (0.34 if len(text) == 1 else 0.26))
        font = self._load_font(font_size)

        try:
            text_bbox = draw.textbbox((0, 0), text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
        except Exception:
            text_width, text_height = draw.textsize(text, font=font)

        text_x = (size - text_width) / 2
        text_y = (size - text_height) / 2 - (size * 0.03)

        draw.text(
            (text_x + 4, text_y + 4),
            text,
            font=font,
            fill=(0, 0, 0, 180),
        )
        draw.text(
            (text_x, text_y),
            text,
            font=font,
            fill=(255, 255, 255, 255),
        )

        return image

    def _update_taskbar_icon(self):
        base = self._create_base_icon(256)
        sizes = [16, 24, 32, 48, 64]
        self.icon_refs = []

        for size in sizes:
            resized = base.resize((size, size), Image.LANCZOS)
            tk_icon = ImageTk.PhotoImage(resized)
            self.icon_refs.append(tk_icon)

        self.root.iconphoto(False, *self.icon_refs)

    def _update_window_labels(self):
        mode_text = "Work Session" if self.mode == "work" else "Break Time"
        if self.paused:
            mode_text += " - Paused"

        self.status_label.config(text=mode_text)
        self.time_label.config(text=self._format_mmss(self.remaining))
        self.pause_button.config(text="Resume" if self.paused else "Pause")
        self.root.title(self._window_title())

    def _update_all_visuals(self):
        self._update_window_labels()
        self._update_taskbar_icon()

        if self.mode == "break":
            self.overlay.update(self.remaining)

    def minimize_to_taskbar(self):
        try:
            self.root.iconify()
        except Exception:
            pass

    def toggle_pause(self):
        self.paused = not self.paused
        self._update_all_visuals()

    def restart_cycle(self):
        if self.mode == "work":
            self.remaining = self.work_seconds
        else:
            self.remaining = self.break_seconds
            self.overlay.show(self.remaining)

        self.paused = False
        self.last_tick = time.monotonic()
        self._update_all_visuals()

    def restart_work(self):
        self.mode = "work"
        self.remaining = self.work_seconds
        self.paused = False
        self.overlay.hide()
        self.last_tick = time.monotonic()
        self._update_all_visuals()

    def quit_app(self):
        self.running = False
        self.overlay.hide()
        self.root.destroy()

    def _switch_to_break(self):
        self.mode = "break"
        self.remaining = self.break_seconds
        self.paused = False

        try:
            winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
        except Exception:
            pass

        self.overlay.show(self.remaining)
        self._update_all_visuals()

    def _switch_to_work(self):
        self.mode = "work"
        self.remaining = self.work_seconds
        self.paused = False

        try:
            winsound.MessageBeep(winsound.MB_OK)
        except Exception:
            pass

        self.overlay.hide()
        self._update_all_visuals()

    def _tick(self):
        if not self.running:
            return

        now = time.monotonic()
        elapsed_whole_seconds = int(now - self.last_tick)

        if elapsed_whole_seconds >= 1:
            self.last_tick += elapsed_whole_seconds

            for _ in range(elapsed_whole_seconds):
                if not self.paused:
                    self.remaining -= 1

                    if self.remaining <= 0:
                        if self.mode == "work":
                            self._switch_to_break()
                        else:
                            self._switch_to_work()

            self._update_all_visuals()

        self.root.after(200, self._tick)

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    set_dpi_awareness()
    set_app_user_model_id()

    app = PomodoroTaskbarApp(work_minutes=25, break_minutes=3)
    app.run()