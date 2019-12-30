import io
import csv
import pdfplumber
import PyPDF2
import pytesseract
from tkinter import *
from tkinter import filedialog, simpledialog, messagebox
from PIL import Image
from pdfviewer.config import *
from pdfviewer.hoverbutton import HoverButton
from pdfviewer.helpbox import HelpBox
from pdfviewer.menubox import MenuBox
from pdfviewer.labelbox import LabelBox
from pdfviewer.display_canvas import DisplayCanvas
from pdfviewer.pdf_attributes import get_pdf_attributes
from decimal import Decimal


class PDFViewer(Frame):

    def __init__(self, master=None, **kw):

        Frame.__init__(self, master, **kw)
        self.pdf = None
        self.page = None
        self.paths = list()
        self.pathidx = -1
        self.total_pages = 0
        self.pageidx = 0
        self.scale = 1.0
        self.rotate = 0
        self.save_path = None
        self.pdf_attributes = []
        self.pdf_to_csv = []
        self.labels = ["page_no", "line", "is_paragraph_end", "is_heading", "is_header", "is_footer", "is_bullet_head",
                       "is_bullet_body", "is_image_caption", "is_table_caption", "is_table_content", "is_toc",
                       "is_toc_heading", "is_page_no", "is_doc_title", "pdf_attribute"]
        self.rectangle_color = None
        self.rectangle_label = None
        self._init_ui()
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()
        self.text_font = None
        self.text_size = None
        self.text = None
        self.rect = None
        self.marked = []

    def _init_ui(self):
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        h = hs - 100
        w = int(h / 1.414) + 100
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)
        self.master.geometry('%dx%d+%d+%d' % (ws, hs, x, y))
        self.master.resizable(width=1, height=1)
        self.master.title("PDFViewer")
        self.master.rowconfigure(0, weight=1)
        self.master.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        self.configure(bg=BACKGROUND_COLOR, bd=0)

        tool_frame = Frame(self, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        pdf_frame = Frame(self, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)

        tool_frame.grid(row=0, column=0, sticky='news')
        pdf_frame.grid(row=0, column=1, sticky='news')
        # Tool Frame
        tool_frame.columnconfigure(0, weight=0)
        tool_frame.rowconfigure(0, weight=1)
        tool_frame.rowconfigure(1, weight=0)
        tool_frame.rowconfigure(2, weight=1)
        tool_frame.rowconfigure(3, weight=1)
        tool_frame.rowconfigure(4, weight=0)
        tool_frame.rowconfigure(5, weight=1)
        tool_frame.rowconfigure(6, weight=0)
        tool_frame.rowconfigure(7, weight=1)

        options = MenuBox(tool_frame, image_path=os.path.join('', 'widgets/options.png'))
        options.grid(row=0, column=0)

        options.add_item('Open Files...', self._open_file)
        options.add_item('Save File...', self._to_file, seperator=True)

        options.add_item('Exit', self.master.quit)

        tools = Frame(tool_frame, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        tools.grid(row=2, column=0)
        HoverButton(tools, image_path=os.path.join('', 'widgets/clear.png'), command=lambda: self._clear(True),
                    width=50, height=50, bg=BACKGROUND_COLOR, bd=0, tool_tip="Clear",
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(pady=2)
        HoverButton(tools, image_path=os.path.join('', 'widgets/open_file.png'), command=self._open_file,
                    width=50, height=50, bg=BACKGROUND_COLOR, bd=0, tool_tip="Open Files",
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(pady=2)
        HoverButton(tools, image_path=os.path.join('', 'widgets/open_dir.png'), command=self._to_file,
                    width=50, height=50, bg=BACKGROUND_COLOR, bd=0, tool_tip="Save Files",
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(pady=2)

        HoverButton(tool_frame, image_path=os.path.join('', 'widgets/help.png'), command=self._help,
                    width=50, height=50, bg=BACKGROUND_COLOR, bd=0, tool_tip="Help",
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).grid(row=7, column=0, sticky='s')

        labels_frame = Frame(tool_frame, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        labels_frame.grid(row=4, column=0)

        HoverButton(labels_frame, text="Heading", command=lambda: self._extract_text("is_heading", "firebrick1"),
                    bg=BACKGROUND_COLOR, bd=0, keep_pressed=True,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR, fg="firebrick1").pack(pady=2)
        HoverButton(labels_frame, text="Paragraph", command=lambda: self._extract_text("is_paragraph_end", "SeaGreen1"),
                    bg=BACKGROUND_COLOR, bd=0, keep_pressed=True,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR, fg="SeaGreen1").pack(pady=2)
        HoverButton(labels_frame, text="Title", command=lambda: self._extract_text("is_doc_title", "DeepSkyBlue2"),
                    bg=BACKGROUND_COLOR, bd=0, keep_pressed=True,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR, fg="DeepSkyBlue2").pack(pady=2)
        HoverButton(labels_frame, text="Header", command=lambda: self._extract_text("is_header", "Cyan4"),
                    bg=BACKGROUND_COLOR, bd=0, keep_pressed=True,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR, fg="Cyan4").pack(pady=2)
        HoverButton(labels_frame, text="Footer", command=lambda: self._extract_text("is_footer", "honeydew4"),
                    bg=BACKGROUND_COLOR, bd=0, keep_pressed=True,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR, fg="honeydew4").pack(pady=2)

        findall_mb = Menubutton(tool_frame, text='find_all', bg=BACKGROUND_COLOR, bd=0, fg="firebrick1",
                                highlightthickness=0, activebackground=HIGHLIGHT_COLOR, relief=RAISED)
        findall_mb.grid(row=6, column=0)
        findall_mb.menu = Menu(findall_mb, tearoff=0)
        findall_mb["menu"] = findall_mb.menu

        findall_mb.menu.add_command(label="By font",
                                    command=self.find_all_by_font)
        findall_mb.menu.add_command(label="By size",
                                    command=self.find_all_by_size)

        # PDF Frame
        pdf_frame.columnconfigure(0, weight=1)
        pdf_frame.columnconfigure(1, weight=1)
        pdf_frame.rowconfigure(0, weight=0)
        pdf_frame.rowconfigure(1, weight=1)

        page_tools = Frame(pdf_frame, width=500, height=50, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        page_tools.grid(row=0, column=0, sticky='news')

        page_tools.rowconfigure(0, weight=1)
        page_tools.columnconfigure(0, weight=1)
        page_tools.columnconfigure(1, weight=0)
        page_tools.columnconfigure(2, weight=2)
        page_tools.columnconfigure(3, weight=0)
        page_tools.columnconfigure(4, weight=1)

        nav_frame = Frame(page_tools, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        nav_frame.grid(row=0, column=1, sticky='ns')
        HoverButton(nav_frame, image_path=os.path.join('', 'widgets/prev.png'),
                    command=self._prev_page, bg=BACKGROUND_COLOR, bd=0,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(side=LEFT, expand=True)

        self.page_label = Label(nav_frame, bg=BACKGROUND_COLOR, bd=0, fg='white', font='Arial 8',
                                text="Page {} of {}".format(self.pageidx, self.total_pages))
        self.page_label.pack(side=LEFT, expand=True)

        HoverButton(nav_frame, image_path=os.path.join('', 'widgets/next.png'),
                    command=self._next_page, bg=BACKGROUND_COLOR, bd=0,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(side=LEFT, expand=True)

        zoom_frame = Frame(page_tools, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        zoom_frame.grid(row=0, column=3, sticky='ns')
        HoverButton(zoom_frame, image_path=os.path.join('', 'widgets/fullscreen.png'),
                    command=self._fit_to_screen, bg=BACKGROUND_COLOR, bd=0,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(side=RIGHT, expand=True)

        self.zoom_label = Label(zoom_frame, bg=BACKGROUND_COLOR, bd=0, fg='white', font='Arial 8',
                                text="Zoom {}%".format(int(self.scale * 100)))
        self.zoom_label.pack(side=RIGHT, expand=True)

        HoverButton(zoom_frame, image_path=os.path.join('', 'widgets/zoomout.png'),
                    command=self._zoom_out, bg=BACKGROUND_COLOR, bd=0,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(side=RIGHT, expand=True)
        HoverButton(zoom_frame, image_path=os.path.join('', 'widgets/zoomin.png'),
                    command=self._zoom_in, bg=BACKGROUND_COLOR, bd=0,
                    highlightthickness=0, activebackground=HIGHLIGHT_COLOR).pack(side=RIGHT, expand=True)

        canvas_frame = Frame(pdf_frame, bg=BACKGROUND_COLOR, bd=0, relief=SUNKEN)
        canvas_frame.grid(row=1, column=0, sticky='news')
        canvas_frame.rowconfigure(0, weight=1)
        canvas_frame.rowconfigure(1, weight=1)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.columnconfigure(1, weight=0)
        self.canvas = DisplayCanvas(canvas_frame, page_height=hs - 68,
                                    page_width=ws - 165, highlightthickness=0)
        self.canvas.viewer = self

        self.grid(row=0, column=0, sticky='news')

        self.master.minsize(height=10, width=50)
        self.master.maxsize(height=hs, width=ws)

    def _reject(self):
        if self.pdf is None:
            return
        self.pathidx = min(self.pathidx + 1, len(self.paths))
        if self.pathidx == len(self.paths):
            self._reset()
            return
        self._load_file()

    def _reset(self):
        self.canvas.clear()
        self.pdf = None
        self.page = None
        self.paths = list()
        self.pathidx = -1
        self.total_pages = 0
        self.pageidx = 0
        self.scale = 1.0
        self.rotate = 0
        self.page_label.configure(text="Page {} of {}".format(self.pageidx, self.total_pages))
        self.zoom_label.configure(text="Zoom {}%".format(int(self.scale * 100)))
        self.master.title("PDFViewer")

    def _clear(self, redraw=False):
        if self.pdf is None:
            return
        if redraw:
            self.canvas.rectangles = {}
        self.marked = []
        self.canvas.reset()
        self._update_page()
        for attr in self.pdf_to_csv:
            attr[-1] = 0
        self.update_in_file_attributes(0)

    def _zoom_in(self):
        if self.pdf is None:
            return
        if self.scale == 2.5:
            return
        self.scale += 0.1
        self._update_page()

    def _zoom_out(self):
        if self.pdf is None:
            return
        if self.scale == 0.1:
            return
        self.scale -= 0.1
        self._update_page()

    def _fit_to_screen(self):
        if self.pdf is None:
            return
        if self.scale == 1.0:
            return
        self.scale = 1.0
        self._update_page()

    def _rotate(self):
        if self.pdf is None:
            return
        self.rotate = (self.rotate - 90) % 360
        self._update_page()

    def _next_page(self):
        if self.pdf is None:
            return
        if self.pageidx == self.total_pages:
            return
        self.pageidx += 1
        self.canvas.reset()
        self._update_page()

    def _prev_page(self):
        if self.pdf is None:
            return
        if self.pageidx == 1:
            return
        self.pageidx -= 1
        self.canvas.reset()
        self._update_page()

    def _last_page(self):
        if self.pdf is None:
            return
        if self.pageidx == self.total_pages:
            return
        self.pageidx = self.total_pages
        self._update_page()

    def _first_page(self):
        if self.pdf is None:
            return
        if self.pageidx == 1:
            return
        self.pageidx = 1
        self._update_page()

    def _next_file(self):
        if self.pdf is None:
            return
        if self.pathidx == len(self.paths) - 1:
            messagebox.showwarning("Warning", "Reached the end of list")
            return
        self.pathidx += 1
        self._load_file()

    def _prev_file(self):
        if self.pdf is None:
            return
        if self.pathidx == 0:
            messagebox.showwarning("Warning", "Reached the end of list")
            return
        self.pathidx -= 1
        self._load_file()

    def _update_page(self):
        page = self.pdf.pages[self.pageidx - 1]
        self.page = page.to_image(resolution=int(self.scale * 160))
        image = self.page.original.rotate(self.rotate)
        self.canvas.update_image(image)
        self.canvas.draw_rectangles(self.pageidx)
        self.page_label.configure(text="Page {} of {}".format(self.pageidx, self.total_pages))
        self.zoom_label.configure(text="Zoom {}%".format(int(self.scale * 100)))

    def _search_text(self):
        if self.pdf is None:
            return
        text = simpledialog.askstring('Search Text', 'Enter text to search:')
        if text == '' or text is None:
            return
        page = self.pdf.pages[self.pageidx - 1]
        image = page.to_image(resolution=int(self.scale * 160))
        words = [w for w in page.extract_words() if text.lower() in w['text'].lower()]
        image.draw_rects(words)
        image = image.annotated.rotate(self.rotate)
        self.canvas.update_image(image)

    def intersection_area(self, word1, word2):
        i_x = min(word2[2], word1["x1"]) - max(word1["x0"], word2[0])
        i_y = min(word2[3], word1["bottom"]) - max(word1["top"], word2[1])
        return i_x * i_y

    def return_match(self, pl_dim, start, end):

        if start <= end:
            prev_text = ''
            for idx, pdf_attribute in enumerate(self.pdf_attributes):
                if pdf_attribute[0] < self.pageidx:
                    pass
                elif pdf_attribute[0] == self.pageidx:
                    min_dim = pdf_attribute[-1][3]
                    match = set(
                        [int(min_dim[x]) in range(int(pl_dim[x]) - start, int(pl_dim[x]) + start) for x in range(4)])

                    if all(match):
                        #print("\nMatch : %s\n" % (pdf_attribute[-1][0]))
                        return match, pdf_attribute, idx
                    if self.intersected_word != pdf_attribute[-1][0]:
                        if prev_text + ' ' + pdf_attribute[-1][0] == self.intersected_word:

                            return [True], pdf_attribute, idx
                    prev_text = pdf_attribute[-1][0]


                else:

                    return self.return_match(pl_dim, start + 1, end)

        return [], None, 0

    def _extract_text_coords(self):
        self.canvas.draw = False
        self.master.configure(cursor='')
        rect = self.canvas.get_rect()
        if rect is None:
            return
        rect = self._reproject_bbox(rect)
        page = self.pdf.pages[self.pageidx - 1]
        words = page.extract_words()
        for word in words:
            if not (word["x1"] < rect[0] or word["x0"] > rect[2] or word["top"] > rect[3] or word["bottom"] < rect[1]):
                word["intersect"] = self.intersection_area(word, rect)
            else:
                word["intersect"] = 0
        max_intersect = max(words, key=lambda x: x['intersect'])
        words_in_rect = [word for word in words if
                         word["top"] == max_intersect["top"] and word["bottom"] == max_intersect["bottom"]]
        self.intersected_word = ' '.join([x['text'] for x in words_in_rect])
        pl_dim = (words_in_rect[0]["x0"], page.height - words_in_rect[-1]["bottom"], words_in_rect[-1]["x1"],
                  page.height - words_in_rect[-1]["top"])

        match, pdf_attribute, match_idx = self.return_match(pl_dim, 10, 20)
        if match and all(match):
            # print("pdf \t pdf %s \n match :%s\n\n"%(pdf_attribute,match))
            self.pdf_to_csv.append([match_idx, self.rectangle_label, self.pageidx, self.canvas.rect_tag, '1'])
            self.text_font = pdf_attribute[-1][1]
            self.text_size = pdf_attribute[-1][2]
            self.text_coords = pdf_attribute[-1][3]
            self.marked.append(pdf_attribute[-1][3])
        return [words_in_rect[0]["x0"], words_in_rect[0]["top"], words_in_rect[-1]["x1"],
                words_in_rect[0]["bottom"]]

    def _extract_text(self, label=None, color=None):
        if color:
            if color == self.rectangle_color:
                self.canvas.draw = False
                self.rectangle_color = None
                self.master.configure(cursor='')
                return
            self.rectangle_color = color
            self.rectangle_label = label
        if self.pdf is None:
            return
        if not self.canvas.draw:
            self.canvas.draw = True
            self.master.configure(cursor='cross')
            return

    def _reproject_bbox(self, bbox):
        bbox = [self.page.decimalize(x) for x in bbox]
        x0, y0, x1, y1 = bbox
        px0, py0 = self.page.page.bbox[:2]
        rx0, ry0 = self.page.root.bbox[:2]
        _x0 = (x0 / self.page.scale) - rx0 + px0
        _y0 = (y0 / self.page.scale) - ry0 + py0
        _x1 = (x1 / self.page.scale) - rx0 + px0
        _y1 = (y1 / self.page.scale) - ry0 + py0
        return [_x0, _y0, _x1, _y1]

    def _run_ocr(self):
        if self.pdf is None:
            return
        pdf_pages = list()
        for page in self.pdf.pages:
            image = page.to_image(resolution=100)
            pdf = pytesseract.image_to_pdf_or_hocr(image.original, extension='pdf')
            pdf_pages.append(pdf)

        pdf_writer = PyPDF2.PdfFileWriter()
        for page in pdf_pages:
            pdf = PyPDF2.PdfFileReader(io.BytesIO(page))
            pdf_writer.addPage(pdf.getPage(0))

        dirname = os.path.dirname(self.paths[self.pathidx])
        filename = os.path.basename(self.paths[self.pathidx])

        path = filedialog.asksaveasfilename(title='Save OCR As', defaultextension='.pdf',
                                            initialdir=dirname, initialfile=filename,
                                            filetypes=[('PDF files', '*.pdf'), ('all files', '.*')])
        if path == '' or path is None:
            return

        with open(path, 'wb') as out:
            pdf_writer.write(out)

        self.paths[self.pathidx] = path
        self._load_file()

    @staticmethod
    def _image_to_pdf(path):
        image = Image.open(path)
        pdf = pytesseract.image_to_pdf_or_hocr(image, extension='pdf')

        filename = '.'.join(os.path.basename(path).split('.')[:-1]) + '.pdf'
        dirname = os.path.dirname(path)

        path = filedialog.asksaveasfilename(title='Save Converted PDF As', defaultextension='.pdf',
                                            initialdir=dirname, initialfile=filename,
                                            filetypes=[('PDF files', '*.pdf'), ('all files', '.*')])
        if path == '' or path is None:
            return
        with open(path, 'wb') as out:
            out.write(pdf)
        return path

    def _load_file(self):
        self._clear(True)
        path = self.paths[self.pathidx]
        filename = os.path.basename(path)
        if filename.split('.')[-1].lower() in ['jpg', 'png']:
            path = self._image_to_pdf(path)
        try:
            self.pdf = pdfplumber.open(path)
            self.total_pages = len(self.pdf.pages)
            self.pageidx = 1
            self.scale = 1.0
            self.rotate = 0
            self._update_page()
            self.master.title("PDFViewer : {}".format(path))
            self.pdf_attributes = get_pdf_attributes(path)
            with open('attributes.txt', 'w') as f:
                for item in self.pdf_attributes:
                    f.write("%s\n" % item)
        except (IndexError, IOError, TypeError):
            self._reject()

    def _open_file(self):
        paths = filedialog.askopenfilenames(filetypes=[('PDF files', '*.pdf'),
                                                       ('JPG files', '*.jpg'),
                                                       ('PNG files', '*.png'),
                                                       ('all files', '.*')],
                                            initialdir=os.getcwd(),
                                            title="Select files", multiple=True)
        if not paths or paths == '':
            return
        paths = [path for path in paths if os.path.basename(path).split('.')[-1].lower() in ['pdf', 'jpg', 'png']]
        self.paths = self.paths[:self.pathidx + 1] + list(paths) + self.paths[self.pathidx + 1:]
        self.total_pages = len(self.paths)
        self.pathidx += 1
        self._load_file()

    def update_in_file_attributes(self, status):
        for idx, label, pg_no, rect_tag, status_csv in self.pdf_to_csv:
            if self.pdf_attributes[idx][0] == pg_no:
                self.pdf_attributes[idx][self.labels.index(label)] = status_csv
        if not status:
            # remove selected attributes from main attributes
            self.pdf_to_csv = []

    def _to_file(self):
        #print(self.pdf_to_csv)
        filepath = filedialog.asksaveasfilename(initialdir=os.getcwd(), title="Save files",
                                                initialfile="pdf_extraction",
                                                defaultextension=".csv",
                                                filetypes=[('csv files', '.csv'), ('text files', '.txt')])
        if not filepath or filepath == '':
            # self._clear()
            return
        with open(filepath, "w", newline="", encoding="utf-8") as f:
            self.update_in_file_attributes(1)
            writer = csv.writer(f)
            writer.writerow(self.labels)
            writer.writerows(self.pdf_attributes)
        # self.pdf_to_csv = []
        # self._clear()

    def _open_dir(self):
        dir_name = filedialog.askdirectory(initialdir=os.getcwd(), title="Select Directory Containing Invoices")
        if not dir_name or dir_name == '':
            return
        paths = os.listdir(dir_name)
        paths = [os.path.join(dir_name, path) for path in paths
                 if os.path.basename(path).split('.')[-1].lower() in ['pdf', 'jpg', 'png']]
        self.paths.extend(paths)
        if not self.paths:
            return
        self.total_pages = len(self.paths)
        self.pathidx += 1
        self._load_file()

    def _help(self):
        ws = self.master.winfo_screenwidth()
        hs = self.master.winfo_screenheight()
        w, h = 600, 600
        x = (ws / 2) - (w / 2)
        y = (hs / 2) - (h / 2)
        help_frame = Toplevel(self)
        help_frame.title("Help")
        help_frame.configure(width=w, height=h, bg=BACKGROUND_COLOR, relief=SUNKEN)
        help_frame.geometry('%dx%d+%d+%d' % (w, h, x, y))
        help_frame.minsize(height=h, width=w)
        help_frame.maxsize(height=h, width=w)
        help_frame.rowconfigure(0, weight=1)
        help_frame.columnconfigure(0, weight=1)
        HelpBox(help_frame, width=w, height=h, bg=BACKGROUND_COLOR, relief=SUNKEN).grid(row=0, column=0)

    def find_all_by_size(self):
        current_page = self.pageidx
        if self.rectangle_label == 'is_heading':
            for idx, pdf_attribute in enumerate(self.pdf_attributes):
                if pdf_attribute[-1][2] == self.text_size and self.text_coords != pdf_attribute[-1][3] and \
                        pdf_attribute[0] == current_page and pdf_attribute[-1][3] not in self.marked:
                    coords = list(pdf_attribute[-1][3])
                    coords[1] = pdf_attribute[-1][-2] - coords[1]
                    coords[3] = pdf_attribute[-1][-2] - coords[3]
                    coords = list(map(Decimal, coords))
                    coords = self.canvas.get_rect_coords(coords)
                    self.rect = self.canvas.canvas.create_rectangle(coords[0], coords[1], coords[2], coords[3],
                                                                    outline=self.rectangle_color)
                    rectangle = [self.rect, coords[0], coords[3], coords[2], coords[1], self.rectangle_color]
                    current_page = self.pageidx
                    self.canvas.rectangles[current_page] = self.canvas.rectangles.get(current_page, [])
                    self.canvas.rectangles[current_page].append(rectangle)
                    self.pdf_to_csv.append([idx, self.rectangle_label, self.pageidx, self.rect, '1'])
                    self.marked.append(pdf_attribute[-1][3])


    def find_all_by_font(self):
        current_page = self.pageidx
        if self.rectangle_label == 'is_heading':
            for idx, pdf_attribute in enumerate(self.pdf_attributes):
                if pdf_attribute[-1][1] == self.text_font and self.text_coords[1] != pdf_attribute[-1][3][1] and \
                        self.text_coords[3] != pdf_attribute[-1][3][3] and pdf_attribute[0] == current_page and \
                        pdf_attribute[-1][3] not in self.marked:
                    coords = list(pdf_attribute[-1][3])
                    coords[1] = pdf_attribute[-1][-2] - coords[1]
                    coords[3] = pdf_attribute[-1][-2] - coords[3]
                    coords = list(map(Decimal, coords))
                    coords = self.canvas.get_rect_coords(coords)
                    self.rect = self.canvas.canvas.create_rectangle(coords[0], coords[1], coords[2], coords[3],
                                                                    outline=self.rectangle_color)
                    rectangle = [self.rect, coords[0], coords[3], coords[2], coords[1], self.rectangle_color]
                    current_page = self.pageidx
                    self.canvas.rectangles[current_page] = self.canvas.rectangles.get(current_page, [])
                    self.canvas.rectangles[current_page].append(rectangle)
                    self.pdf_to_csv.append([idx, self.rectangle_label, self.pageidx, self.rect, '1'])
                    self.marked.append(pdf_attribute[-1][3])
