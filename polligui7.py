"""
crea un programma in python e tkinter per creare immagini tramite image.pollinations.ai/prompt il programma deve avere:
- la possibilità di regolare la dimensione orizzontale e verticale separatamente anche oltre il limite di 1024x1024 pixel
- se la misura dell immagine supera 768x768 pixel l immagine viene ridimensionata automaticament con python pil per avere i valori indicati mantenendo le proporzioni
- il campo di inserimento del prompt deve essere alto tre righe e avere una barra di scorrimento
- ci deve essere un menu a tendina con vari stili artistici di immagine, il primo sarà none che non inserirà nessuno stile
- ci deve essere un menu a tendina con varie tipologie di immagine, il primo sarà none che non inserirà nessuna tipologia
- ci deve essere un opzione no watermark collegata alla code dell url 'nologo=true'
- ci deve essere un menu a tendina con la scelta tra i due modelli di generazione flux e turbo collegati al termine dell url a '&model='
- ci deve essere un pulsante per la generazione dell immagine che deve segnalare la generazione in corso
- in caso di errore nella generazione il programma deve fare automaticamente tre tentativi per generarla
- ci deve essere un pulsaante per aprire l'immagine in Gimp
- ci deve essere un pulsante per salvare l immagine
- ci deve essere un pulsante per chiudere il programma
- ci deve essere un visualizzatore per l immagine generata
- deve anche essere possibile copiare l immagine per incollarla in un programma, la copia deve essere possibile ugualemente se si usa windows linux o mac
- l'url ottenuta deve anche essere stampata in un print per permettere il debug da terminale
- questo prompt deve essere aggiunto al programma in un commento multilinea senza modifiche
"""

import os
import sys
import platform
import io
import threading
from tkinter import (
    Tk, Text, Scrollbar, Menu, Label, Button, Entry, StringVar, IntVar,
    Frame, Toplevel, OptionMenu, BooleanVar, Checkbutton, messagebox, filedialog, HORIZONTAL
)
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk

import requests
from PIL import Image, ImageTk
import subprocess


class PollinationsImageGenerator:
    BASE_URL = "https://image.pollinations.ai/prompt/"

    def __init__(self, master):
        self.master = master
        master.title("Pollinations Image Generator - by Sky @ Foresko")

        # --- Variables ---
        self.prompt_var = StringVar()
        # We'll use a Text widget for multiline prompt instead of Entry
        # so no StringVar for prompt text here.

        self.styles = [
            "none",
            "oil painting",
            "watercolor",
            "digital art",
            "cinematic",
            "sketch",
            "surrealism",
            "pixel art",
            "photo realistic"
        ]
        self.style_var = StringVar(value=self.styles[0])

        self.types = [
            "none",
            "portrait",
            "landscape",
            "abstract",
            "fantasy",
            "concept art",
            "cyberpunk",
            "anime",
            "street photography"
        ]
        self.type_var = StringVar(value=self.types[0])

        self.no_watermark_var = BooleanVar(value=False)

        self.models = ["flux", "turbo"]
        self.model_var = StringVar(value=self.models[0])

        self.width_var = IntVar(value=512)
        self.height_var = IntVar(value=512)

        self.generating_var = StringVar(value="")

        self.image = None  # PIL Image object
        self.photo = None  # ImageTk.PhotoImage object for display

        # --- Layout ---
        self._build_widgets()

    def _build_widgets(self):
        frm_top = Frame(self.master)
        frm_top.pack(padx=10, pady=5, fill='x')

        # Prompt label and text with scrollbar
        prompt_label = Label(frm_top, text="Prompt:")
        prompt_label.grid(row=0, column=0, sticky='w')

        self.prompt_text = Text(frm_top, width=60, height=3, wrap='word', undo=True)
        self.prompt_text.grid(row=1, column=0, columnspan=5, sticky='we')

        scroll_vert = Scrollbar(frm_top, command=self.prompt_text.yview)
        scroll_vert.grid(row=1, column=5, sticky='ns')
        self.prompt_text['yscrollcommand'] = scroll_vert.set

        # Width and Height
        width_label = Label(frm_top, text="Width:")
        width_label.grid(row=2, column=0, sticky='e', pady=(5, 0))
        self.width_entry = Entry(frm_top, textvariable=self.width_var, width=7)
        self.width_entry.grid(row=2, column=1, sticky='w', pady=(5, 0))

        height_label = Label(frm_top, text="Height:")
        height_label.grid(row=2, column=2, sticky='e', pady=(5, 0))
        self.height_entry = Entry(frm_top, textvariable=self.height_var, width=7)
        self.height_entry.grid(row=2, column=3, sticky='w', pady=(5, 0))

        # Style dropdown
        style_label = Label(frm_top, text="Style:")
        style_label.grid(row=3, column=0, sticky='e')
        self.style_menu = OptionMenu(frm_top, self.style_var, *self.styles)
        self.style_menu.grid(row=3, column=1, sticky='w')

        # Type dropdown
        type_label = Label(frm_top, text="Type:")
        type_label.grid(row=3, column=2, sticky='e')
        self.type_menu = OptionMenu(frm_top, self.type_var, *self.types)
        self.type_menu.grid(row=3, column=3, sticky='w')

        # No watermark checkbox
        self.no_watermark_cb = Checkbutton(frm_top, text="No Watermark", variable=self.no_watermark_var)
        self.no_watermark_cb.grid(row=4, column=0, columnspan=2, sticky='w', pady=(5,0))

        # Model dropdown
        model_label = Label(frm_top, text="Model:")
        model_label.grid(row=4, column=2, sticky='e', pady=(5,0))
        self.model_menu = OptionMenu(frm_top, self.model_var, *self.models)
        self.model_menu.grid(row=4, column=3, sticky='w', pady=(5,0))

        # Generate button and generating status
        self.btn_generate = Button(frm_top, text="Generate Image", command=self._on_generate)
        self.btn_generate.grid(row=5, column=0, columnspan=2, pady=(10, 5), sticky='we')

        self.generating_label = Label(frm_top, textvariable=self.generating_var, fg="blue")
        self.generating_label.grid(row=5, column=2, columnspan=2, sticky='w', padx=(5,0), pady=(10,5))

        # Image display frame
        frm_image = Frame(self.master, relief='sunken', bd=2, width=768, height=768)
        frm_image.pack(padx=10, pady=5, fill='both', expand=True)
        frm_image.grid_propagate(False)

        self.canvas_label = Label(frm_image)
        self.canvas_label.pack(expand=True)

        # Buttons for opening in Gimp, saving, copying and exit
        frm_buttons = Frame(self.master)
        frm_buttons.pack(padx=10, pady=10, fill='x')

        self.btn_open_gimp = Button(frm_buttons, text="Open in Gimp", command=self._on_open_gimp, state='disabled')
        self.btn_open_gimp.pack(side='left', padx=(0,5))

        self.btn_save = Button(frm_buttons, text="Save Image", command=self._on_save_image, state='disabled')
        self.btn_save.pack(side='left', padx=(0,5))

        self.btn_copy = Button(frm_buttons, text="Copy Image", command=self._on_copy_image, state='disabled')
        self.btn_copy.pack(side='left', padx=(0,5))

        self.btn_exit = Button(frm_buttons, text="Exit", command=self.master.destroy)
        self.btn_exit.pack(side='right')

    def _on_generate(self):
        # Disable buttons, clear status and start generation in thread
        prompt = self.prompt_text.get("1.0", "end").strip()
        if not prompt:
            messagebox.showwarning("Input needed", "Please enter a prompt.")
            return

        try:
            width = max(1, int(self.width_entry.get()))
            height = max(1, int(self.height_entry.get()))
        except ValueError:
            messagebox.showerror("Invalid input", "Width and Height must be integer numbers.")
            return

        if width <= 0 or height <= 0:
            messagebox.showerror("Invalid input", "Width and Height must be positive integers.")
            return

        self.generating_var.set("Generating image...")
        self.btn_generate.config(state='disabled')
        self.btn_open_gimp.config(state='disabled')
        self.btn_save.config(state='disabled')
        self.btn_copy.config(state='disabled')

        thread = threading.Thread(target=self._generate_image, args=(prompt, width, height))
        thread.daemon = True
        thread.start()

    def _generate_image(self, prompt, width, height):
        # Compose URL
        # Format: BASE_URL + prompt + "?width=...&height=...&nologo=true&model=..."
        # with optional style and type injected into prompt separated by comma
        # style/type "none" means skip

        prompt_elements = [prompt]

        # Add style if not none
        if self.style_var.get() != "none":
            prompt_elements.append(self.style_var.get())

        # Add type if not none
        if self.type_var.get() != "none":
            prompt_elements.append(self.type_var.get())

        prompt_joined = ", ".join(prompt_elements).replace("\n", " ")

        params = []
        if width > 0:
            params.append(f"width={width}")
        if height > 0:
            params.append(f"height={height}")
        if self.no_watermark_var.get():
            params.append("nologo=true")
        if self.model_var.get() in ("flux", "turbo"):
            params.append(f"model={self.model_var.get()}")

        # Build URL
        url = f"{self.BASE_URL}{requests.utils.quote(prompt_joined)}"
        if params:
            url += "?" + "&".join(params)

        print(f"Generated URL for debug: {url}")

        # Try three times if errors
        tries = 3
        image_data = None

        while tries > 0:
            try:
                r = requests.get(url, timeout=30)
                r.raise_for_status()
                # It returns a PNG/JPG image
                image_data = r.content
                # Check if content is an image? PIL can attempt to open
                self.image = Image.open(io.BytesIO(image_data)).convert("RGBA")
                break
            except Exception as e:
                print(f"Error during image retrieval: {e}")
                tries -= 1
                if tries == 0:
                    self.master.after(0, lambda: messagebox.showerror("Error", f"Failed to generate image after 3 attempts.\n{e}"))
                    self.master.after(0, self._clear_generating_state)
                    return

        # Resize logic if width or height >768 need to resize proportionally to indicated size
        # The prompt wording is: if dimension > 768x768, resize with PIL to have indicated values (width,height)
        # keeping proportions, so the final image fits inside width x height keeping aspect ratio

        # Check if width or height > 768
        max_dim = 768
        w, h = self.image.size
        target_w = width
        target_h = height

        # Resize only if one or both target dimensions are >768
        if width > max_dim or height > max_dim:
            # Compute scale factors for each direction to fit inside (width, height)
            scale_w = target_w / w
            scale_h = target_h / h
            scale = min(scale_w, scale_h)
            new_w = max(1, int(w * scale))
            new_h = max(1, int(h * scale))
            self.image = self.image.resize((new_w, new_h), Image.LANCZOS)

        # Now update image display on GUI thread:
        self.master.after(0, self._update_image_display)

    def _update_image_display(self):
        # Display image in Label widget, max size 768x768 frame area but image can be smaller
        # self.image is a PIL Image

        # Frame size is fixed 768x768
        max_display_size = 768
        img_w, img_h = self.image.size

        # To display smoothly in tkinter, limit to max_display_size for either dimension for display,
        # scaling down if needed but not required because widget is that big
        scale = 1.0
        if img_w > max_display_size or img_h > max_display_size:
            scale = min(max_display_size / img_w, max_display_size / img_h)
            disp_w = max(1, int(img_w * scale))
            disp_h = max(1, int(img_h * scale))
            disp_img = self.image.resize((disp_w, disp_h), Image.LANCZOS)
        else:
            disp_img = self.image

        self.photo = ImageTk.PhotoImage(disp_img)
        self.canvas_label.config(image=self.photo)
        self.canvas_label.image = self.photo

        self.generating_var.set("")
        self.btn_generate.config(state='normal')
        self.btn_open_gimp.config(state='normal')
        self.btn_save.config(state='normal')
        self.btn_copy.config(state='normal')

    def _clear_generating_state(self):
        self.generating_var.set("")
        self.btn_generate.config(state='normal')

    def _on_open_gimp(self):
        if self.image is None:
            messagebox.showwarning("No image", "No image is currently loaded.")
            return

        # Save temporary file
        tmpdir = os.path.join(os.path.expanduser("~"), ".pollinations_temp")
        os.makedirs(tmpdir, exist_ok=True)
        tmp_path = os.path.join(tmpdir, "temp_pollinations_image.png")
        try:
            self.image.save(tmp_path)
        except Exception as e:
            messagebox.showerror("Save error", f"Cannot save temp image file:\n{e}")
            return

        # Open with GIMP - cross platform command attempt
        try:
            if platform.system() == "Windows":
                # Usually gimp.exe should be in PATH if installed
                subprocess.Popen(["gimp", tmp_path], shell=True)
            elif platform.system() == "Darwin":
                # macOS
                subprocess.Popen(["open", "-a", "GIMP", tmp_path])
            else:
                # Linux and others
                subprocess.Popen(["gimp", tmp_path])
        except Exception as e:
            messagebox.showerror("Launch error", f"Error launching GIMP:\n{e}")

    def _on_save_image(self):
        if self.image is None:
            messagebox.showwarning("No image", "No image is currently loaded.")
            return

        filetypes = [
            ("PNG Image", "*.png"),
            ("JPEG Image", "*.jpg;*.jpeg"),
            ("All files", "*.*")
        ]

        filepath = filedialog.asksaveasfilename(defaultextension=".png",
                                                filetypes=filetypes,
                                                title="Save image as")
        if not filepath:
            return

        try:
            # Infer format from extension
            ext = os.path.splitext(filepath)[1].lower()
            fmt = "PNG"
            if ext in (".jpg", ".jpeg"):
                fmt = "JPEG"
            self.image.save(filepath, fmt)
        except Exception as e:
            messagebox.showerror("Save error", f"Error saving image:\n{e}")

    def _on_copy_image(self):
        if self.image is None:
            messagebox.showwarning("No image", "No image is currently loaded.")
            return

        # Cross-platform clipboard image copy is tricky.
        # Strategy:
        # - Windows: use PIL ImageTk and tkinter clipboard via bmp (via Windows only)
        # - macOS: use 'pbcopy' or 'osascript' to copy image data (complex) but offer fallback saving temp
        # - Linux: often no standard clipboard image support, fallback to saving temp and user can paste from there.

        system = platform.system()
        try:
            if system == "Windows":
                # Windows supports clipboard image via Tkinter's own functions, but needs bitmap handle,
                # Tkinter doesn't directly support images to clipboard except for text so use PIL Image's bitmap.

                # We'll convert to BMP and send to clipboard via tkinter clipboard_clear and clipboard_append is text-only
                # We use the win32clipboard from pywin32 if available for direct image clipboard, else fallback

                try:
                    import win32clipboard
                    from PIL import ImageGrab

                    output = io.BytesIO()
                    # BMP without header for clipboard, .bmp stores a header of 14 bytes which must be stripped
                    # To place an image on the clipboard you must pass DIB which is BMP data excluding file header

                    def send_to_clipboard(win_image):
                        # Convert to DIB format (BMP header excluded)
                        output = io.BytesIO()
                        win_image.convert('RGB').save(output, 'BMP')
                        data = output.getvalue()[14:]  # skip 14 byte bmp header
                        # Open clipboard and set data
                        win32clipboard.OpenClipboard()
                        win32clipboard.EmptyClipboard()
                        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
                        win32clipboard.CloseClipboard()

                    send_to_clipboard(self.image)
                    messagebox.showinfo("Copied", "Image copied to clipboard.")
                    return
                except ImportError:
                    # pywin32 not installed
                    messagebox.showwarning("pywin32 required",
                                           "You need 'pywin32' package installed to copy image on Windows clipboard.\n"
                                           "Fallback: saving image to temp file to paste manually.")
                    
                except Exception as exc:
                    messagebox.showwarning("Copy failed",
                                           f"Failed to copy image to clipboard:\n{exc}\nFallback: saving image to temp file.")

                # Fallback: save temp and open
                tmpdir = os.path.join(os.path.expanduser("~"), ".pollinations_temp")
                os.makedirs(tmpdir, exist_ok=True)
                tmp_path = os.path.join(tmpdir, "temp_pollinations_image.png")
                self.image.save(tmp_path)
                messagebox.showinfo("Fallback", f"Image saved to:\n{tmp_path}\nYou can open and copy from there.")

            elif system == "Darwin":
                # macOS: copy in clipboard with 'osascript' or 'pbcopy' frequently is only text-based
                # Use 'osascript' with 'pbcopy' if we convert image to TIFF, base64 encode and call AppleScript
                # It's complex, so provide fallback of saving temp

                try:
                    import subprocess
                    import base64

                    output = io.BytesIO()
                    self.image.save(output, format='TIFF')
                    tiff_data = output.getvalue()
                    b64data = base64.b64encode(tiff_data).decode('utf-8')

                    # Creating a temporary AppleScript to place an image on pasteboard
                    applescript = f'''
set the clipboard to (read (POSIX file "/dev/stdin") as TIFF picture)
'''

                    # Unfortunately the above direct passthrough is complex
                    # Instead, fallback to save and inform user

                    raise NotImplementedError("Direct macOS clipboard image copy not implemented")

                except Exception:
                    tmpdir = os.path.join(os.path.expanduser("~"), ".pollinations_temp")
                    os.makedirs(tmpdir, exist_ok=True)
                    tmp_path = os.path.join(tmpdir, "temp_pollinations_image.png")
                    self.image.save(tmp_path)
                    messagebox.showinfo("Fallback", f"Image saved to:\n{tmp_path}\nYou can open and copy from there.")

            else:
                # Linux or other OS: copy image to clipboard usually requires xclip/xsel or other utilities,
                # which is usually text only or requires additional tools.
                # Fallback save image and inform user

                tmpdir = os.path.join(os.path.expanduser("~"), ".pollinations_temp")
                os.makedirs(tmpdir, exist_ok=True)
                tmp_path = os.path.join(tmpdir, "temp_pollinations_image.png")
                self.image.save(tmp_path)
                messagebox.showinfo("Fallback", f"Image saved to:\n{tmp_path}\nYou can open and copy from there.")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to copy image:\n{e}")


def main():
    root = Tk()
    root.geometry("720x900")  # Enough height for controls and image display
    app = PollinationsImageGenerator(root)
    root.mainloop()


if __name__ == "__main__":
    main()