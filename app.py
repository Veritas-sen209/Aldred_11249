import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
import cv2
import numpy as np
import math

CANVAS_WIDTH = 900
CANVAS_HEIGHT = 600


class ImageAnnotator:
    def __init__(self, root):
        self.root = root
        self.root.title("Image Annotation Tool")

        self.tool = None
        self.start_x = self.start_y = None
        self.temp_item = None
        self.measure_points = []

        self.image = None
        self.original_image = None
        self.history = []
        self.redo_stack = []

        self.scale = 1.0

        self.setup_ui()

    def setup_ui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="Load", command=self.load_image).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Rectangle", command=lambda: self.set_tool("rect")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Line", command=lambda: self.set_tool("line")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Circle", command=lambda: self.set_tool("circle")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Text", command=lambda: self.set_tool("text")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Measure", command=lambda: self.set_tool("measure")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Redo", command=self.redo).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Reset", command=self.reset).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Save", command=self.save_image).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="gray")
        self.canvas.pack()

        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def set_tool(self, tool):
        self.tool = tool
        self.measure_points.clear()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path:
            return

        self.image = cv2.imread(path)
        self.original_image = self.image.copy()
        self.history.clear()
        self.redo_stack.clear()

        self.refresh_canvas()

    def save_state(self):
        self.history.append(self.image.copy())
        self.redo_stack.clear()

    def canvas_to_image(self, x, y):
        return int(x / self.scale), int(y / self.scale)

    def on_mouse_down(self, event):
        if self.image is None:
            return

        ix, iy = self.canvas_to_image(event.x, event.y)
        self.start_x, self.start_y = ix, iy

        if self.tool == "text":
            text = simpledialog.askstring("Text", "Enter label:")
            if text:
                self.save_state()
                cv2.putText(self.image, text, (ix, iy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                self.refresh_canvas()

        if self.tool == "measure":
            self.measure_points.append((ix, iy))
            if len(self.measure_points) == 2:
                self.draw_measurement()

    def on_mouse_drag(self, event):
        if self.image is None or self.tool not in ["rect", "line", "circle"]:
            return

        if self.temp_item:
            self.canvas.delete(self.temp_item)

        x, y = event.x, event.y

        if self.tool == "rect":
            self.temp_item = self.canvas.create_rectangle(
                self.start_x * self.scale, self.start_y * self.scale, x, y, outline="white")

        elif self.tool == "line":
            self.temp_item = self.canvas.create_line(
                self.start_x * self.scale, self.start_y * self.scale, x, y, fill="red")

        elif self.tool == "circle":
            r = math.hypot(x - self.start_x * self.scale, y - self.start_y * self.scale)
            self.temp_item = self.canvas.create_oval(
                self.start_x * self.scale - r, self.start_y * self.scale - r,
                self.start_x * self.scale + r, self.start_y * self.scale + r,
                outline="blue")

    def on_mouse_up(self, event):
        if self.image is None or self.tool not in ["rect", "line", "circle"]:
            return

        self.save_state()
        ix, iy = self.canvas_to_image(event.x, event.y)

        if self.tool == "rect":
            cv2.rectangle(self.image, (self.start_x, self.start_y), (ix, iy), (255, 255, 255), 3)

        elif self.tool == "line":
            cv2.line(self.image, (self.start_x, self.start_y), (ix, iy), (0, 0, 255), 3)

        elif self.tool == "circle":
            r = int(math.hypot(ix - self.start_x, iy - self.start_y))
            cv2.circle(self.image, (self.start_x, self.start_y), r, (255, 0, 0), 3)

        self.canvas.delete(self.temp_item)
        self.temp_item = None
        self.refresh_canvas()

    def draw_measurement(self):
        self.save_state()
        (x1, y1), (x2, y2) = self.measure_points
        dist = math.hypot(x2 - x1, y2 - y1)

        cv2.line(self.image, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.putText(self.image, f"{dist:.1f}px",
                    ((x1 + x2) // 2, (y1 + y2) // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)

        self.measure_points.clear()
        self.refresh_canvas()

    def undo(self):
        if not self.history:
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.history.pop()
        self.refresh_canvas()

    def redo(self):
        if not self.redo_stack:
            return
        self.history.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.refresh_canvas()

    def reset(self):
        if self.original_image is None:
            return
        self.image = self.original_image.copy()
        self.history.clear()
        self.redo_stack.clear()
        self.refresh_canvas()

    def refresh_canvas(self):
        h, w = self.image.shape[:2]
        self.scale = min(CANVAS_WIDTH / w, CANVAS_HEIGHT / h)

        resized = cv2.resize(self.image, (int(w * self.scale), int(h * self.scale)))
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)

        self.tk_image = tk.PhotoImage(data=cv2.imencode(".png", rgb)[1].tobytes())
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def save_image(self):
        if self.image is None:
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")]
        )
        if path:
            cv2.imwrite(path, self.image)
            messagebox.showinfo("Saved", "Image saved successfully.")


if __name__ == "__main__":
    root = tk.Tk()
    app = ImageAnnotator(root)
    root.mainloop()
