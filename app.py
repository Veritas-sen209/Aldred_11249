import tkinter as tk
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont
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
        self.display_image = None
        self.draw = None

        self.history = []
        self.redo_stack = []

        self.tk_image = None
        self.scale = 1.0

        self.setup_ui()

    def setup_ui(self):
        toolbar = tk.Frame(self.root)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        tk.Button(toolbar, text="Load Image", command=self.load_image).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Rectangle", command=lambda: self.set_tool("rect")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Line", command=lambda: self.set_tool("line")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Circle", command=lambda: self.set_tool("circle")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Text", command=lambda: self.set_tool("text")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Measure", command=lambda: self.set_tool("measure")).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Undo", command=self.undo).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Redo", command=self.redo).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Reset", command=self.reset).pack(side=tk.LEFT)
        tk.Button(toolbar, text="Save image", command=self.save_image).pack(side=tk.LEFT)

        self.canvas = tk.Canvas(self.root, width=CANVAS_WIDTH, height=CANVAS_HEIGHT, bg="gray")
        self.canvas.pack()
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

    def set_tool(self, tool):
        self.tool = tool
        self.measure_points.clear()

    def save_state(self):
        if self.image:
            self.history.append(self.image.copy())
            self.redo_stack.clear()

    def load_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg *.jpeg")])
        if not path:
            return
        self.image = Image.open(path).convert("RGB")
        self.original_image = self.image.copy()
        self.draw = ImageDraw.Draw(self.image)
        self.history.clear()
        self.redo_stack.clear()
        self.refresh_canvas()

    def refresh_canvas(self):
        if not self.image:
            return

        # Scale image to fit canvas
        img_w, img_h = self.image.size
        scale_w = CANVAS_WIDTH / img_w
        scale_h = CANVAS_HEIGHT / img_h
        self.scale = min(scale_w, scale_h)

        new_w = int(img_w * self.scale)
        new_h = int(img_h * self.scale)
        self.display_image = self.image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_image = ImageTk.PhotoImage(self.display_image)

        self.canvas.delete("all")
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_image)

    def canvas_to_image(self, x, y):
        return int(x / self.scale), int(y / self.scale)

    def on_mouse_down(self, event):
        if not self.image:
            return
        ix, iy = self.canvas_to_image(event.x, event.y)
        self.start_x, self.start_y = ix, iy

        if self.tool == "text":
            text = simpledialog.askstring("Text", "Enter label:")
            if text:
                self.save_state()
                font = ImageFont.load_default()
                self.draw.text((ix, iy), text, fill="red", font=font)
                self.refresh_canvas()

        if self.tool == "measure":
            self.measure_points.append((ix, iy))
            if len(self.measure_points) == 2:
                self.draw_measurement()

    def on_mouse_drag(self, event):
        if not self.image or self.tool not in ["rect", "line", "circle"]:
            return

        if self.temp_item:
            self.canvas.delete(self.temp_item)

        x, y = event.x, event.y

        if self.tool == "rect":
            self.temp_item = self.canvas.create_rectangle(
                self.start_x * self.scale, self.start_y * self.scale, x, y, outline="green"
            )
        elif self.tool == "line":
            self.temp_item = self.canvas.create_line(
                self.start_x * self.scale, self.start_y * self.scale, x, y, fill="blue"
            )
        elif self.tool == "circle":
            r = math.hypot(x - self.start_x * self.scale, y - self.start_y * self.scale)
            self.temp_item = self.canvas.create_oval(
                self.start_x * self.scale - r, self.start_y * self.scale - r,
                self.start_x * self.scale + r, self.start_y * self.scale + r,
                outline="white"
            )

    def on_mouse_up(self, event):
        if not self.image or self.tool not in ["rect", "line", "circle"]:
            return
        self.save_state()
        ix, iy = self.canvas_to_image(event.x, event.y)

        if self.tool == "rect":
            self.draw.rectangle([self.start_x, self.start_y, ix, iy], outline="green", width=5)
        elif self.tool == "line":
            self.draw.line([self.start_x, self.start_y, ix, iy], fill="blue", width=3)
        elif self.tool == "circle":
            r = int(math.hypot(ix - self.start_x, iy - self.start_y))
            self.draw.ellipse([self.start_x - r, self.start_y - r, self.start_x + r, self.start_y + r],
                              outline="white", width=5)

        self.temp_item = None
        self.refresh_canvas()

    def draw_measurement(self):
        (x1, y1), (x2, y2) = self.measure_points
        dist = math.hypot(x2 - x1, y2 - y1)

        self.draw.line([x1, y1, x2, y2], fill="red", width=5)
        font = ImageFont.load_default()
        self.draw.text(((x1 + x2)//2, (y1 + y2)//2), f"{dist:.2f}px", fill="blue", font=font)
        self.measure_points.clear()
        self.refresh_canvas()

    def undo(self):
        if not self.history:
            return
        self.redo_stack.append(self.image.copy())
        self.image = self.history.pop()
        self.draw = ImageDraw.Draw(self.image)
        self.refresh_canvas()

    def redo(self):
        if not self.redo_stack:
            return
        self.history.append(self.image.copy())
        self.image = self.redo_stack.pop()
        self.draw = ImageDraw.Draw(self.image)
        self.refresh_canvas()

    def reset(self):
        if not self.original_image:
            return
        self.image = self.original_image.copy()
        self.draw = ImageDraw.Draw(self.image)
        self.history.clear()
        self.redo_stack.clear()
        self.refresh_canvas()

    def save_image(self):
        if not self.image:
            return
        path = filedialog.asksaveasfilename(defaultextension=".png",
                                            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if path:
            self.image.save(path)
            messagebox.showinfo("Saved", "Annotated image saved successfully.")

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageAnnotator(root)
    root.mainloop()
