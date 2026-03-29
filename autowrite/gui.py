import os

os.environ["TF_USE_LEGACY_KERAS"] = "1"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
import logging
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
logging.getLogger("tensorflow").setLevel(logging.ERROR)
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter import PhotoImage  # To handle the image
from autowrite.handwriting_synthesis import Hand
from tkinter.colorchooser import askcolor
from tkinter import filedialog
import autowrite.handwriting_synthesis.config


def process_text(
    input_text,
    output_dir,
    alphabet,
    max_line_length,
    lines_per_page,
    biases,
    styles,
    stroke_colors,
    stroke_widths,
    page,
):
    """
    Processes text input, sanitizes, wraps, paginates it,
    and generates handwriting SVG files.
    """

    # Split input text into lines, preserving empty lines
    lines = [line.strip() if line.strip() else "." for line in input_text.split("\n")]
    # convert stroke colors values from text counterpart to hexadecimal (black blue red and green only)
    stroke_colors = {
        "Black": "#000000",
        "Blue": "#0000FF",
        "Red": "#FF0000",
        "Green": "#008000",
    }[stroke_colors]

    # Sanitize lines
    sanitized_lines = [
        "".join(char if char in alphabet else " " for char in line) for line in lines
    ]

    # Wrap lines
    wrapped_lines = []
    for line in sanitized_lines:
        words = line.split()
        current_line = ""
        for word in words:
            if len(current_line) + len(word) + 1 > max_line_length:
                wrapped_lines.append(current_line.strip())
                current_line = word
            else:
                current_line += " " + word
        if current_line:
            wrapped_lines.append(current_line.strip())

    # Paginate lines
    pages = [
        wrapped_lines[i : i + lines_per_page]
        for i in range(0, len(wrapped_lines), lines_per_page)
    ]

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate handwriting SVG files
    # def write(self, filename, lines, biases=None, styles=None, stroke_colors=None, stroke_widths=None, page=None):
    hand = Hand()
    for page_num, page_lines in enumerate(pages):
        filename = os.path.join(output_dir, f"result_page_{page_num + 1}.svg")
        hand.write(
            filename=filename,
            lines=page_lines,
            biases=[biases] * len(page_lines),
            styles=[styles] * len(page_lines),
            stroke_colors=[stroke_colors] * len(page_lines),
            stroke_widths=[stroke_widths] * len(page_lines),
            page=page,
        )
        print(f"Page {page_num + 1} written to {filename}")


margin_left_line = None
margin_top_line = None
page_preview = None
selected_page_color = "white"  # Default page color
selected_margin_color = "red"  # Default margin color
selected_line_color = "lightgray"  # Default line color
overflow = False

last_preview_dir = None


def save_preview():
    global last_preview_dir
    if not last_preview_dir:
        messagebox.showwarning("Warning", "No preview generated yet.")
        return

    import glob
    import shutil

    svg_files = glob.glob(f"{last_preview_dir}/*.svg")
    png_files = glob.glob(f"{last_preview_dir}/*.png")
    gcode_files = glob.glob(f"{last_preview_dir}/*.gcode")

    if not svg_files and not png_files and not gcode_files:
        messagebox.showwarning("Warning", "No preview files found.")
        return

    output_dir = filedialog.askdirectory(title="Select Output Directory for Preview")
    if not output_dir:
        return

    try:
        import os

        for f in svg_files + png_files + gcode_files:
            shutil.copy2(f, output_dir)
            print(f"Saved {os.path.basename(f)} to {output_dir}")
        messagebox.showinfo(
            "Success",
            f"Saved {len(svg_files + png_files + gcode_files)} preview files to {output_dir}",
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to save preview: {e}")


def print_gcode():
    update_preview()
    global last_preview_dir
    if not last_preview_dir:
        messagebox.showwarning("Warning", "No preview generated yet.")
        return

    import glob
    import serial
    
    gcode_files = glob.glob(f"{last_preview_dir}/*.gcode")

    if not gcode_files:
        messagebox.showwarning("Warning", "No G-code files found.")
        return

    device_path = '/dev/rfcomm0'
    try:
        # Open serial port with requested parameters
        with serial.Serial(
            port=device_path,
            baudrate=115200,
            parity=serial.PARITY_NONE,
            bytesize=serial.EIGHTBITS,
            stopbits=serial.STOPBITS_ONE,
            timeout=5.0
        ) as dev:
            
            # Create a dialog window to show the printing progress
            print_dialog = tk.Toplevel(root)
            print_dialog.title("Printing G-code")
            print_dialog.geometry("600x400")
            
            is_cancelled = False
            def cancel_print():
                nonlocal is_cancelled
                is_cancelled = True
                print_dialog.destroy()
                
            print_dialog.protocol("WM_DELETE_WINDOW", cancel_print)
            
            cancel_button = ttk.Button(print_dialog, text="CANCEL", command=cancel_print)
            cancel_button.pack(side="top", pady=10)
            
            log_text = tk.Text(print_dialog, wrap="word", state="normal")
            log_text.pack(expand=True, fill="both", padx=10, pady=10)
            
            for gcode_file in gcode_files:
                with open(gcode_file, 'r') as f:
                    for line in f:
                        if is_cancelled:
                            return
                        
                        line_stripped = line.strip()
                        if not line_stripped:
                            continue
                        
                        try:
                            log_text.insert(tk.END, f"SENT: {line_stripped}\n")
                            log_text.see(tk.END)
                            print_dialog.update()
                        except tk.TclError:
                            return # Dialog was destroyed
                        
                        dev.write((line_stripped + '\n').encode('ascii'))
                        dev.flush()
                        
                        # Read response
                        response = dev.readline().decode('ascii', errors='replace').strip()
                        if not response:
                            response = "<TIMEOUT>"
                            
                        if is_cancelled:
                            return
                            
                        try:
                            log_text.insert(tk.END, f"RECV: {response}\n")
                            log_text.see(tk.END)
                            print_dialog.update()
                        except tk.TclError:
                            return # Dialog was destroyed
                        
            if not is_cancelled:
                messagebox.showinfo("Success", f"Successfully sent G-code to {device_path}", parent=print_dialog)
                print_dialog.destroy()
            
    except Exception as e:
        messagebox.showerror("Error", f"Failed to send G-code to {device_path}:\n{e}")

def update_preview():
    canvas.update_idletasks()
    global margin_left_line, margin_top_line, page_preview  # Access the global variables
    global selected_page_color, selected_margin_color, selected_line_color  # Access the selected colors
    global overflow
    global last_preview_dir
    try:
        input_text = text_box.get("1.0", "end-1c")
        if not input_text or input_text.strip() == placeholder:
            messagebox.showwarning("Warning", "Please enter some text to preview.")
            return

        # Get user inputs
        max_line_length = int(max_line_length_entry.get())
        lines_per_page = int(lines_per_page_entry.get())
        handwriting_consistency = float(handwriting_consistency_entry.get())
        styles = int(styles_combobox.get())
        ink_color = color_combobox.get()
        pen_thickness = float(pen_thickness_entry.get())
        line_height = int(line_height_entry.get())
        total_lines_per_page = int(total_lines_entry.get())
        view_height = float(view_height_entry.get())
        view_width = float(view_width_entry.get())
        margin_left = int(margin_left_entry.get()) * -1
        margin_top = int(margin_top_entry.get()) * -1

        autowrite.handwriting_synthesis.config.background = False

        alphabet = [
            "\x00",
            " ",
            "!",
            '"',
            "#",
            "'",
            "(",
            ")",
            ",",
            "-",
            ".",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            ":",
            ";",
            "?",
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "Y",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
        ]

        # Use a temporary directory to generate the preview images
        import tempfile
        import glob
        from PIL import Image, ImageTk

        output_dir = tempfile.mkdtemp()
        last_preview_dir = output_dir

        # Update text box cursor to waiting state to let user know it's generating
        root.config(cursor="watch")
        root.update()

        page = {
            "page_color": selected_page_color,
            "margin_color": selected_margin_color,
            "line_color": selected_line_color,
            "view_height": view_height,
            "view_width": view_width,
            "margin_left": margin_left,
            "margin_top": margin_top,
            "line_height": line_height,
            "total_lines": total_lines_per_page,
        }

        # Process text
        process_text(
            input_text,
            output_dir,
            alphabet,
            max_line_length,
            lines_per_page,
            handwriting_consistency,
            styles,
            ink_color,
            pen_thickness,
            page,
        )

        root.config(cursor="")

        # Find the generated PNG image and display it
        png_files = glob.glob(f"{output_dir}/*.png")
        if png_files:
            image = Image.open(png_files[0])

            canvas_width = canvas.winfo_width()
            canvas_height = canvas.winfo_height()

            img_width, img_height = image.size
            if canvas_width > 1 and canvas_height > 1:
                ratio = min(canvas_width / img_width, canvas_height / img_height)
                new_size = (int(img_width * ratio), int(img_height * ratio))
                image = image.resize(new_size, Image.LANCZOS)

            photo_image = ImageTk.PhotoImage(image)

            canvas.delete("all")
            canvas.create_image(
                canvas_width / 2, canvas_height / 2, image=photo_image, anchor="center"
            )
            canvas.image = photo_image  # Keep reference

    except Exception as e:
        root.config(cursor="")
        print(f"ERROR: {e}")
        messagebox.showerror("Error", str(e))


def on_generate():
    # Ask user to select a directory for saving the files
    output_dir = filedialog.askdirectory(title="Select Output Directory")

    if not output_dir:  # Check if the user canceled the dialog
        messagebox.showwarning(
            "No Directory Selected", "Please select a directory to save the files."
        )
        return
    update_preview()
    if overflow:
        messagebox.showwarning("Overflow", "Too many lines to fit in the given space.")
        return
    try:
        # Get user inputs
        input_text = text_box.get("1.0", tk.END).strip()
        # output_dir = os.path.join(os.path.dirname(__file__), "img")
        # os.makedirs(output_dir, exist_ok=True)

        # Parameters
        max_line_length = int(max_line_length_entry.get())
        lines_per_page = int(lines_per_page_entry.get())
        handwriting_consistency = float(handwriting_consistency_entry.get())
        styles = int(styles_combobox.get())
        ink_color = color_combobox.get()
        pen_thickness = float(pen_thickness_entry.get())
        line_height = int(line_height_entry.get())
        total_lines_per_page = int(total_lines_entry.get())
        view_height = float(view_height_entry.get())
        view_width = float(view_width_entry.get())
        margin_left = int(margin_left_entry.get()) * -1
        margin_top = int(margin_top_entry.get()) * -1

        autowrite.handwriting_synthesis.config.background = False

        if total_lines_per_page < lines_per_page:
            messagebox.showwarning(
                "Input Error",
                "Total Lines Per Page must not be lesser than Lines Written Per Page.",
            )
            return

        # Page layout
        page = [
            line_height,
            total_lines_per_page,
            view_height,
            view_width,
            margin_left,
            margin_top,
            selected_page_color,
            selected_margin_color,
            selected_line_color,
        ]

        # Alphabet
        alphabet = [
            "\x00",
            " ",
            "!",
            '"',
            "#",
            "'",
            "(",
            ")",
            ",",
            "-",
            ".",
            "0",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            ":",
            ";",
            "?",
            "A",
            "B",
            "C",
            "D",
            "E",
            "F",
            "G",
            "H",
            "I",
            "J",
            "K",
            "L",
            "M",
            "N",
            "O",
            "P",
            "R",
            "S",
            "T",
            "U",
            "V",
            "W",
            "Y",
            "a",
            "b",
            "c",
            "d",
            "e",
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
        ]

        # Process text
        process_text(
            input_text,
            output_dir,
            alphabet,
            max_line_length,
            lines_per_page,
            handwriting_consistency,
            styles,
            ink_color,
            pen_thickness,
            page,
        )
        messagebox.showinfo("Success", "Handwriting SVG files generated successfully!")

    except Exception as e:
        print(f"ERROR: {e}")
        messagebox.showerror("Error", str(e))


# Update the style value label when the style selection changes


def update_style_label(event=None):
    # Get the selected style
    selected_style = styles_combobox.get()

    # Construct the image file path based on the selected style
    image_path = os.path.join(os.path.dirname(__file__), "assets", f"font{selected_style}.png")

    try:
        # Load the image
        style_image = PhotoImage(file=image_path)

        # Update the image label
        style_value_label.config(image=style_image)
        style_value_label.image = (
            style_image  # Keep a reference to the image to prevent garbage collection
        )

    except Exception as e:
        # If the image doesn't exist or there is an error, show a default message
        style_value_label.config(text="Image not found")
        print(f"Error loading image: {e}")


placeholder = "Enter your text here."


# Text input box with placeholder functionality
def on_focus_in(event):
    if text_box.get("1.0", "end-1c") == placeholder:
        text_box.delete("1.0", "end")
        text_box.config(fg="black")  # Restore text color when typing starts


def on_focus_out(event):
    if not text_box.get("1.0", "end-1c"):
        text_box.insert("1.0", placeholder)
        text_box.config(fg="grey")  # Change placeholder color


# Create the main window
root = tk.Tk()
root.title("AutoWrite - Handwriting Synthesis")
root.geometry("1920x1080")
root.resizable(True, True)
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(0, weight=2, uniform="col")
root.grid_columnconfigure(1, weight=4, uniform="col")
root.grid_columnconfigure(2, weight=4, uniform="col")

# Frame for parameter inputs (left)
param_frame = tk.Frame(root)
param_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")

# Text input box (middle)
text_box = tk.Text(
    root, wrap="word", width=40, height=10, fg="grey"
)  # Set initial color to grey for placeholder
text_box.insert("1.0", placeholder)  # Insert placeholder text
text_box.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")

text_box.bind("<FocusIn>", on_focus_in)
text_box.bind("<FocusOut>", on_focus_out)

# Add the banner image at the top of the parameter frame
# Parameter input fields
fields = [
    ("Line Length (characters)", "50"),
    ("Total Lines Per Page", "30"),
    ("Lines Written Per Page", "30"),
    ("Handwriting Consistency", "0.98"),
    ("Pen Thickness", "0.5"),
    ("Line Height", "32"),
    ("Margin Left", "32"),
    ("Margin Top", "32"),
]
entries = {}

for i, (label, default) in enumerate(fields):
    tk.Label(param_frame, text=f"{label}:").grid(
        row=i + 2, column=0, padx=5, pady=5, sticky="e"
    )
    entry = ttk.Entry(param_frame)
    entry.insert(0, default)
    entry.grid(
        row=i + 2, column=1, padx=5, pady=5, sticky="ew"
    )  # Added sticky="ew" for stretch
    entries[label] = entry

# Map entries to variables
max_line_length_entry = entries["Line Length (characters)"]
lines_per_page_entry = entries["Lines Written Per Page"]
handwriting_consistency_entry = entries["Handwriting Consistency"]
pen_thickness_entry = entries["Pen Thickness"]
line_height_entry = entries["Line Height"]
total_lines_entry = entries["Total Lines Per Page"]
margin_left_entry = entries["Margin Left"]
margin_top_entry = entries["Margin Top"]

# Styles dropdown (combobox)
tk.Label(param_frame, text="Writing Style:").grid(
    row=len(fields) + 2, column=0, padx=5, pady=5, sticky="e"
)
styles_combobox = ttk.Combobox(
    param_frame, values=[str(i) for i in range(1, 13)], state="readonly"
)
styles_combobox.set("1")  # Default value
styles_combobox.grid(row=len(fields) + 2, column=1, padx=5, pady=5, sticky="ew")

# Colour dropdown (combobox)
tk.Label(param_frame, text="Ink Colour:").grid(
    row=len(fields) + 3, column=0, padx=5, pady=5, sticky="e"
)
color_combobox = ttk.Combobox(
    param_frame, values=["Black", "Blue", "Red", "Green"], state="readonly"
)
color_combobox.set("Blue")  # Default value
color_combobox.grid(row=len(fields) + 3, column=1, padx=5, pady=5, sticky="ew")

# Page size radio buttons
page_size_frame = tk.Frame(param_frame)
page_size_frame.grid(row=len(fields) + 4, column=0, columnspan=2, pady=5, sticky="ew")

tk.Label(page_size_frame, text="Page Size:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
page_size_var = tk.StringVar(value="a5")

# Custom size entries
custom_size_frame = tk.Frame(param_frame)
custom_size_frame.grid(row=len(fields) + 5, column=0, columnspan=2, pady=5, sticky="ew")

tk.Label(custom_size_frame, text="View Width (mm):").grid(row=0, column=0, padx=5, pady=5, sticky="e")
view_width_entry = ttk.Entry(custom_size_frame, width=8)
view_width_entry.insert(0, "148")
view_width_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

tk.Label(custom_size_frame, text="View Height (mm):").grid(row=0, column=2, padx=5, pady=5, sticky="e")
view_height_entry = ttk.Entry(custom_size_frame, width=8)
view_height_entry.insert(0, "210")
view_height_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

view_width_entry.config(state="disabled")
view_height_entry.config(state="disabled")

page_sizes = {
    "a6": (105, 148),
    "a5": (148, 210),
    "a4": (210, 297),
    "letter": (215.9, 279.4),
    "custom": (148, 210)
}

def on_page_size_change():
    size = page_size_var.get()
    if size == "custom":
        view_width_entry.config(state="normal")
        view_height_entry.config(state="normal")
        # default to a5 if custom is selected and empty/disabled previously
        if not view_width_entry.get():
            view_width_entry.insert(0, "148")
            view_height_entry.insert(0, "210")
    else:
        view_width_entry.config(state="normal")
        view_height_entry.config(state="normal")
        view_width_entry.delete(0, tk.END)
        view_height_entry.delete(0, tk.END)
        w, h = page_sizes[size]
        view_width_entry.insert(0, str(w))
        view_height_entry.insert(0, str(h))
        view_width_entry.config(state="disabled")
        view_height_entry.config(state="disabled")

col_idx = 1
for size_name in ["a6", "a5", "a4", "letter", "custom"]:
    rb = ttk.Radiobutton(page_size_frame, text=size_name.capitalize(), variable=page_size_var, value=size_name, command=on_page_size_change)
    rb.grid(row=0, column=col_idx, padx=5, pady=5)
    col_idx += 1

# Buttons for preview and generate
button_frame = tk.Frame(param_frame)
button_frame.grid(
    row=len(fields) + 6, column=0, columnspan=2, pady=5, padx=0, sticky="ew"
)

# Configure columns to expand equally
button_frame.grid_columnconfigure(0, weight=1, uniform="button")
button_frame.grid_columnconfigure(1, weight=1, uniform="button")

# Add Preview and Generate buttons
preview_button = ttk.Button(button_frame, text="Preview", command=update_preview)
preview_button.grid(row=0, column=0, sticky="ew", padx=5)

generate_button = ttk.Button(button_frame, text="Generate", command=on_generate)
generate_button.grid(row=0, column=1, sticky="ew", padx=5)


# Create a frame for the style display (below the buttons in the left section)
style_frame = tk.Frame(param_frame)
style_frame.grid(row=len(fields) + 7, column=0, columnspan=2, pady=10)

# Label to show the selected style value (now will display an image)
style_value_label = tk.Label(style_frame)
style_value_label.grid(row=0, column=1, padx=10, pady=5, sticky="w")

# Bind the update_style_label function to the combobox event
styles_combobox.bind("<<ComboboxSelected>>", update_style_label)

# Initialize the style display with the default selected style (usually "1")
root.after(100, update_style_label)

# Display values on right side (bottom section)
value_frame = tk.Frame(root)
value_frame.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")

# Add Canvas to draw the white rectangle in the bottom section of input_frame
canvas = tk.Canvas(value_frame, bg="white")
canvas.pack(fill="both", expand=True, pady=5)

preview_button_frame = tk.Frame(value_frame)
preview_button_frame.pack(side="bottom", pady=5)

save_preview_button = ttk.Button(preview_button_frame, text="Save Preview", command=save_preview)
save_preview_button.pack(side="left", padx=5)

print_button = ttk.Button(preview_button_frame, text="PRINT", command=print_gcode)
print_button.pack(side="left", padx=5)


root.after(100, update_preview)

# Run the GUI
if __name__ == "__main__":
    root.mainloop()

def main():
    try:
        root.mainloop()
    except Exception:
        pass
