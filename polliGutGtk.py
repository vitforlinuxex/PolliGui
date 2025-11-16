"""
crea un programma in python e pygtk per creare immagini tramite image.pollinations.ai/prompt il programma deve avere:
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

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

import requests
from io import BytesIO
from PIL import Image
import subprocess
import os
import sys
import platform

class ImageGeneratorApp(Gtk.Window):
    STYLE_OPTIONS = ['none', 'oil painting', 'watercolor', 'photorealistic', 'sketch', 'cyberpunk', 'fantasy']
    TYPE_OPTIONS = ['none', 'portrait', 'landscape', 'abstract', 'anime', 'concept art', 'pixel art']
    MODEL_OPTIONS = ['flux', 'turbo']
    BASE_URL = "https://image.pollinations.ai/prompt/"
    MAX_DIRECT_SIZE = 1024
    REDUCE_AFTER_SIZE = 768  # If width or height > 768, resize automatically with PIL maintaining aspect ratio

    def __init__(self):
        super().__init__(title="Pollinations.ai Image Generator (PyGTK)")
        self.set_border_width(10)
        self.set_default_size(800, 600)

        self.img_data = None
        self.img_pixbuf = None
        self.img_pil = None  # PIL Image for resizing & copying
        self.img_path_tmp = None

        # Main vertical layout
        vbox_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.add(vbox_main)

        # Prompt label + multi-line TextView with scrollbar
        lbl_prompt = Gtk.Label(label="Prompt:")
        lbl_prompt.set_halign(Gtk.Align.START)
        vbox_main.pack_start(lbl_prompt, False, False, 0)

        self.txt_prompt = Gtk.TextView()
        self.txt_prompt.set_wrap_mode(Gtk.WrapMode.WORD)
        # Set fixed height approx 3 lines - calculating line height dynamically is tricky, use approx 72 px (3x24)
        self.txt_prompt.set_size_request(-1, 72)
        scroll_prompt = Gtk.ScrolledWindow()
        scroll_prompt.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll_prompt.set_min_content_height(72)
        scroll_prompt.add(self.txt_prompt)
        vbox_main.pack_start(scroll_prompt, False, True, 0)

        # Horizontal box for width & height
        hbox_size = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox_main.pack_start(hbox_size, False, False, 0)

        lbl_width = Gtk.Label(label="Width (px):")
        lbl_width.set_halign(Gtk.Align.START)
        lbl_height = Gtk.Label(label="Height (px):")
        lbl_height.set_halign(Gtk.Align.START)

        self.spin_width = Gtk.SpinButton()
        self.spin_width.set_adjustment(Gtk.Adjustment(512, 64, 5000, 1, 10, 0))
        self.spin_width.set_value(512)

        self.spin_height = Gtk.SpinButton()
        self.spin_height.set_adjustment(Gtk.Adjustment(512, 64, 5000, 1, 10, 0))
        self.spin_height.set_value(512)

        hbox_size.pack_start(lbl_width, False, False, 0)
        hbox_size.pack_start(self.spin_width, False, False, 0)
        hbox_size.pack_start(lbl_height, False, False, 0)
        hbox_size.pack_start(self.spin_height, False, False, 0)

        # HBox for style, type, watermark, model
        hbox_options = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox_main.pack_start(hbox_options, False, False, 0)

        # Style dropdown
        lbl_style = Gtk.Label(label="Style:")
        lbl_style.set_halign(Gtk.Align.START)
        self.combo_style = Gtk.ComboBoxText()
        for style in self.STYLE_OPTIONS:
            self.combo_style.append_text(style)
        self.combo_style.set_active(0)
        hbox_options.pack_start(lbl_style, False, False, 0)
        hbox_options.pack_start(self.combo_style, False, False, 0)

        # Type dropdown
        lbl_type = Gtk.Label(label="Type:")
        lbl_type.set_halign(Gtk.Align.START)
        self.combo_type = Gtk.ComboBoxText()
        for t in self.TYPE_OPTIONS:
            self.combo_type.append_text(t)
        self.combo_type.set_active(0)
        hbox_options.pack_start(lbl_type, False, False, 0)
        hbox_options.pack_start(self.combo_type, False, False, 0)

        # No watermark checkbox
        self.chk_nologo = Gtk.CheckButton(label="No watermark")
        hbox_options.pack_start(self.chk_nologo, False, False, 0)

        # Model dropdown
        lbl_model = Gtk.Label(label="Model:")
        lbl_model.set_halign(Gtk.Align.START)
        self.combo_model = Gtk.ComboBoxText()
        for model in self.MODEL_OPTIONS:
            self.combo_model.append_text(model)
        self.combo_model.set_active(0)
        hbox_options.pack_start(lbl_model, False, False, 0)
        hbox_options.pack_start(self.combo_model, False, False, 0)

        # Horizontal box for buttons: Generate, Open in Gimp, Save, Close, Copy image
        hbox_buttons = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vbox_main.pack_start(hbox_buttons, False, False, 0)

        self.btn_generate = Gtk.Button(label="Generate Image")
        self.btn_generate.connect("clicked", self.on_generate_clicked)
        hbox_buttons.pack_start(self.btn_generate, False, False, 0)

        self.btn_open_gimp = Gtk.Button(label="Open in Gimp")
        self.btn_open_gimp.set_sensitive(False)
        self.btn_open_gimp.connect("clicked", self.on_open_gimp_clicked)
        hbox_buttons.pack_start(self.btn_open_gimp, False, False, 0)

        self.btn_save = Gtk.Button(label="Save Image")
        self.btn_save.set_sensitive(False)
        self.btn_save.connect("clicked", self.on_save_clicked)
        hbox_buttons.pack_start(self.btn_save, False, False, 0)

        self.btn_copy = Gtk.Button(label="Copy Image")
        self.btn_copy.set_sensitive(False)
        self.btn_copy.connect("clicked", self.on_copy_clicked)
        hbox_buttons.pack_start(self.btn_copy, False, False, 0)

        self.btn_quit = Gtk.Button(label="Close")
        self.btn_quit.connect("clicked", self.on_close_clicked)
        hbox_buttons.pack_start(self.btn_quit, False, False, 0)

        # Image viewer
        frame_img = Gtk.Frame(label="Generated Image")
        frame_img.set_shadow_type(Gtk.ShadowType.IN)
        vbox_main.pack_start(frame_img, True, True, 0)

        self.img_widget = Gtk.Image()
        align_center = Gtk.Alignment.new(0.5, 0.5, 0, 0)
        align_center.add(self.img_widget)
        frame_img.add(align_center)

        self.show_all()

    def get_prompt_text(self):
        buf = self.txt_prompt.get_buffer()
        start_iter = buf.get_start_iter()
        end_iter = buf.get_end_iter()
        return buf.get_text(start_iter, end_iter, True).strip()

    def build_url(self):
        prompt = self.get_prompt_text()
        if not prompt:
            return None
        width = self.spin_width.get_value_as_int()
        height = self.spin_height.get_value_as_int()

        style = self.combo_style.get_active_text()
        type_ = self.combo_type.get_active_text()
        nologo = self.chk_nologo.get_active()
        model = self.combo_model.get_active_text()

        # Compose prompt for URL, add style and type as suffix if not 'none'
        prompt_full = prompt
        if style != "none":
            prompt_full += f", {style}"
        if type_ != "none":
            prompt_full += f", {type_}"

        # URL encode prompt for safer urls
        from urllib.parse import quote_plus
        encoded_prompt = quote_plus(prompt_full)

        url = f"{self.BASE_URL}{encoded_prompt}?width={width}&height={height}"

        if nologo:
            url += "&nologo=true"

        if model and model in ["flux", "turbo"]:
            url += f"&model={model}"

        return url, width, height

    def on_generate_clicked(self, widget):
        self.btn_generate.set_sensitive(False)
        self.btn_generate.set_label("Generating...")

        # Async to avoid UI block
        GLib.idle_add(self.generate_image)

    def generate_image(self):
        url_width_ok = self.spin_width.get_value_as_int()
        url_height_ok = self.spin_height.get_value_as_int()
        data = self.build_url()
        if data is None:
            self._generation_failed("Prompt cannot be empty")
            return False
        url, req_width, req_height = data

        tries = 3
        exception = None
        image_bytes = None

        print("[DEBUG] Generating URL:", url)

        while tries > 0:
            try:
                r = requests.get(url, timeout=30)
                if r.status_code == 200:
                    image_bytes = r.content
                    break
                else:
                    exception = Exception(f"HTTP status {r.status_code}")
            except Exception as e:
                exception = e
            tries -= 1

        if not image_bytes:
            print("[DEBUG] Generation failed after 3 retries:", exception)
            self._generation_failed(f"Failed to download image: {exception}")
            return False

        try:
            # Load bytes in PIL Image
            self.img_pil = Image.open(BytesIO(image_bytes)).convert("RGBA")

            # If requested size > 768x768, resize PIL image keeping aspect ratio to requested size (but not to requested width AND height bluntly)
            max_req = max(req_width, req_height)
            if max_req > self.REDUCE_AFTER_SIZE:
                # Calculate aspect ratio and scale image to fit within (req_width, req_height) while keeping proportions
                img_w, img_h = self.img_pil.size
                # Target size as width and height indicated (requested in URL)
                # But instructed: if the requested size exceeds 768x768 reduce the image to the indicated values maintaining proportions
                # So scale factor is min(req_width/img_w, req_height/img_h)
                factor = min(req_width / img_w, req_height / img_h)
                if factor < 1:
                    new_w = int(img_w * factor)
                    new_h = int(img_h * factor)
                    self.img_pil = self.img_pil.resize((new_w, new_h), Image.LANCZOS)
                # Else requested size is >768 but image is smaller? Should not happen, but keep it as above.

            # Convert PIL image to GdkPixbuf for GTK display
            self.img_pixbuf = self.pil_image_to_pixbuf(self.img_pil)

            # Set image widget
            self.img_widget.set_from_pixbuf(self.img_pixbuf)

            # Enable buttons
            self.btn_open_gimp.set_sensitive(True)
            self.btn_save.set_sensitive(True)
            self.btn_copy.set_sensitive(True)

            # Save temporary image for opening in Gimp and other
            self.save_temp_image()

        except Exception as e:
            print("[DEBUG] Exception during image processing:", e)
            self._generation_failed(f"Failed to process image: {e}")
            return False

        self.btn_generate.set_sensitive(True)
        self.btn_generate.set_label("Generate Image")
        return False

    def _generation_failed(self, message):
        # Display dialog for error
        dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, "Image Generation Failed")
        dialog.format_secondary_text(message)
        dialog.run()
        dialog.destroy()
        self.btn_generate.set_sensitive(True)
        self.btn_generate.set_label("Generate Image")

    def pil_image_to_pixbuf(self, pil_img):
        # Convert PIL RGBA to pixbuf
        data = pil_img.tobytes()
        w, h = pil_img.size
        pixbuf = GdkPixbuf.Pixbuf.new_from_data(
            data,
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            w,
            h,
            w * 4,
        )
        return pixbuf

    def save_temp_image(self):
        # Save a temporary PNG image in writeable location for Gimp/open/save/copy
        import tempfile
        if self.img_pil is None:
            return
        if self.img_path_tmp and os.path.exists(self.img_path_tmp):
            try:
                os.remove(self.img_path_tmp)
            except Exception:
                pass
        fd, path = tempfile.mkstemp(prefix="pollinations_", suffix=".png")
        os.close(fd)
        self.img_pil.save(path, "PNG")
        self.img_path_tmp = path

    def on_open_gimp_clicked(self, widget):
        if not self.img_path_tmp or not os.path.exists(self.img_path_tmp):
            self._generation_failed("No image available to open in Gimp")
            return

        # Command differs per OS for Gimp:
        # Attempt to run 'gimp' from PATH; user must have Gimp installed
        try:
            if platform.system() == "Windows":
                # Windows: try 'gimp-2.10.exe' or 'gimp.exe' maybe installed in PATH
                try:
                    subprocess.Popen(["gimp-2.10.exe", self.img_path_tmp])
                except FileNotFoundError:
                    subprocess.Popen(["gimp.exe", self.img_path_tmp])
            else:
                # Unix / Mac
                subprocess.Popen(["gimp", self.img_path_tmp])
        except FileNotFoundError:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK,
                                   "Gimp not found. Please install Gimp or add it to system PATH.")
            dialog.run()
            dialog.destroy()

    def on_save_clicked(self, widget):
        if self.img_pil is None:
            self._generation_failed("No image available to save")
            return

        dialog = Gtk.FileChooserDialog(
            title="Save Image",
            parent=self,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_SAVE, Gtk.ResponseType.OK,
        )
        dialog.set_current_name("image.png")

        filter_png = Gtk.FileFilter()
        filter_png.set_name("PNG Image")
        filter_png.add_mime_type("image/png")
        dialog.add_filter(filter_png)

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All files")
        filter_all.add_pattern("*")
        dialog.add_filter(filter_all)

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if not filename.lower().endswith(".png"):
                filename += ".png"
            try:
                self.img_pil.save(filename, "PNG")
            except Exception as e:
                self._generation_failed(f"Failed to save image: {e}")
        dialog.destroy()

    def on_close_clicked(self, widget):
        # Cleanup temp image
        if self.img_path_tmp and os.path.exists(self.img_path_tmp):
            try:
                os.remove(self.img_path_tmp)
            except Exception:
                pass
        Gtk.main_quit()

    def on_copy_clicked(self, widget):
        if self.img_pixbuf is None:
            return

        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)

        # Copy image pixbuf to clipboard
        try:
            clipboard.set_image(self.img_pixbuf)
            clipboard.store()
        except Exception as e:
            dialog = Gtk.MessageDialog(self, 0, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK,
                                   "Failed to copy image to clipboard")
            dialog.format_secondary_text(str(e))
            dialog.run()
            dialog.destroy()

def main():
    app = ImageGeneratorApp()
    app.connect("destroy", Gtk.main_quit)
    Gtk.main()


if __name__ == "__main__":
    main()
