from tkinter import *
import tkinter as tk
from PIL import Image, ImageTk


class DisplayCanvas(Frame):

    def __init__(self, master, page_height, page_width, **kw):
        Frame.__init__(self, master, **kw)
        self.x = self.y = 0
        self.canvas = Canvas(master, height=page_height, width=page_width, bg='#404040', highlightbackground='#353535',
                             relief=SUNKEN, highlightthickness=0)

        self.sbarv = Scrollbar(self.master, orient=VERTICAL, bg='#404040', highlightbackground='#353535')
        self.sbarh = Scrollbar(self.master, orient=HORIZONTAL, bg='#404040', highlightbackground='#353535')
        self.sbarv.config(command=self.canvas.yview)
        self.sbarh.config(command=self.canvas.xview)

        self.canvas.config(yscrollcommand=self.sbarv.set)
        self.canvas.config(xscrollcommand=self.sbarh.set)

        self.canvas.grid(row=0, column=0, sticky='nsew')
        self.sbarv.grid(row=0, column=1, stick='ns')
        self.sbarh.grid(row=1, column=0, sticky='ew')

        self.canvas.rowconfigure(0, weight=1)
        self.canvas.rowconfigure(1, weight=1)
        self.canvas.columnconfigure(1, weight=1)
        # self.canvas.pack(fill=BOTH,expand=True)

        top = self.winfo_toplevel()
        top.bind('<Left>', self.on_left)
        top.bind('<Right>', self.on_right)
        top.bind('<Up>', self.on_up)
        top.bind('<Down>', self.on_down)

        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)
        self.canvas.bind("<Motion>", self.on_move)
        self.canvas.bind("<Configure>", self.on_resize)

        self.rect = None
        self.image = None
        self.image_obj = None
        self.pil_image = None
        self.draw = False
        self.rectangles = {}
        self.btn_rect = {}

        self.start_x = None
        self.start_y = None
        self.viewer = None
        self.img = Image.open('widgets/quit-icon-5.png')
        self.img = self.img.resize((20, 20), Image.ANTIALIAS)
        self.photoImg = ImageTk.PhotoImage(self.img)
        self.buttonTXT = 0
        self.btntag_list = {}

        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.addtag_all("all")
        self.width = self.master.winfo_screenwidth()
        self.height = self.master.winfo_screenheight()

    def on_button_press(self, event, rectangle=False):
        if rectangle:
            temp = list(self.btn_rect)
            widget = event.widget
            event_coord = widget.canvasy(event.y)
            rect_tag = self.btn_rect[min(temp, key=lambda x: abs(x - event_coord))][0]
            but_tag = self.btn_rect[min(temp, key=lambda x: abs(x - event_coord))][1]
            self.canvas.delete(rect_tag)
            self.canvas.delete(but_tag)
            current_page = self.viewer.pageidx
            for rect in list(self.rectangles[current_page]):
                if rect[0] == rect_tag:
                    del self.rectangles[current_page][self.rectangles[current_page].index(rect)]
                    break
            temp_idx = 0

            for attr in self.viewer.pdf_to_csv:
                if attr[-2] == rect_tag:
                    attr[-1] = 0
                    temp_idx = attr[0]
                    break
            for idx, pdf_attribute in enumerate(self.viewer.pdf_attributes):
                if idx == temp_idx:
                    if pdf_attribute[-1][3] in self.viewer.marked:
                        del self.viewer.marked[self.viewer.marked.index(pdf_attribute[-1][3])]

        else:
            self.start_x = self.canvas.canvasx(event.x)
            self.start_y = self.canvas.canvasy(event.y)

            if not self.rect and self.draw:
                self.rect = self.canvas.create_rectangle(self.x, self.y, 1, 1, outline=self.viewer.rectangle_color)

    def on_move_press(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        w, h = self.canvas.winfo_width(), self.canvas.winfo_height()
        if event.x > 0.9 * w:
            self.on_right()
        elif event.x < 0.1 * w:
            self.on_left()
        if event.y > 0.9 * h:
            self.on_down()
        elif event.y < 0.1 * h:
            self.on_up()

        if self.draw:
            self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_left(self, event=None):
        self.canvas.xview_scroll(-1, 'units')

    def on_right(self, event=None):
        self.canvas.xview_scroll(1, 'units')

    def on_up(self, event=None):
        self.canvas.yview_scroll(-1, 'units')

    def on_down(self, event=None):
        self.canvas.yview_scroll(1, 'units')

    def on_button_release(self, event):
        self.rect_tag = self.rect
        if self.rect:
            coords = self.viewer._extract_text_coords()

            coords = self.get_rect_coords(coords)
            self.canvas.coords(self.rect, coords[0], coords[1], coords[2], coords[3])
            rectangle = [self.rect, coords[0], coords[1], coords[2], coords[3], self.viewer.rectangle_color]
            current_page = self.viewer.pageidx
            self.rectangles[current_page] = self.rectangles.get(current_page, [])
            self.rectangles[current_page].append(rectangle)

            self.rect = None

    def draw_rectangles(self, current_page):
        if current_page in self.rectangles:
            for rectangle in self.rectangles[current_page]:
                new_tag = self.canvas.create_rectangle(rectangle[1], rectangle[2], rectangle[3], rectangle[4],
                                                       outline=rectangle[5])
                if rectangle[2] in self.btn_rect:
                    self.btn_rect[rectangle[2]][0] = new_tag

                for attr in self.viewer.pdf_to_csv:
                    if attr[3] == rectangle[0]:
                        attr[3] = new_tag
                        break
                rectangle[0] = new_tag
                if self.rect_id in self.btntag_list:
                    self.btn_rect[rectangle[2]][1] = self.btntag_list[self.rect_id]

    def update_image(self, image):
        self.pil_image = image
        self.image = ImageTk.PhotoImage(image)
        if self.image_obj is None:
            self.image_obj = self.canvas.create_image(1, 1, image=self.image, anchor=CENTER)
        else:
            self.canvas.itemconfig(self.image_obj, image=self.image)
        self.sbarv.config(command=self.canvas.yview)
        self.sbarh.config(command=self.canvas.xview)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.canvas.xview_moveto(0.0)
        self.canvas.yview_moveto(0.0)

    def reset(self):
        self.canvas.delete("all")
        self.image_obj = self.canvas.create_image(1, 1, image=self.image, anchor=CENTER)
        self.sbarv.config(command=self.canvas.yview)
        self.sbarh.config(command=self.canvas.xview)
        self.canvas.config(yscrollcommand=self.sbarv.set)
        self.canvas.config(xscrollcommand=self.sbarh.set)
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
        self.rect = None

    def clear(self):
        self.canvas.delete("all")
        self.image_obj = None
        self.rectangles={}
        self.viewer.marked=[]
        self.viewer.text_size=0
        self.viewer.text_font=''

    def get_rect(self):
        w, h = self.pil_image.size
        x0, y0 = self.canvas.coords(self.image_obj)
        minx = x0 - w / 2.0
        miny = y0 - h / 2.0
        if self.rect:
            rect = self.canvas.coords(self.rect)
            rect = [rect[0] + abs(minx), rect[1] + abs(miny), rect[2] + abs(minx), rect[3] + abs(miny)]
            return rect
        else:
            return None

    def get_rect_coords(self, rect):
        x0, y0, x1, y1 = rect
        page = self.viewer.page
        px0, py0 = page.page.bbox[:2]
        rx0, ry0 = page.root.bbox[:2]
        _x0 = float((x0 * page.scale) - px0 + rx0)
        _y0 = float((y0 * page.scale) - py0 + px0)
        _x1 = float((x1 * page.scale) - px0 + rx0)
        _y1 = float((y1 * page.scale) - py0 + px0)
        w, h = self.pil_image.size
        x0, y0 = self.canvas.coords(self.image_obj)
        minx = (x0 - w) / 2.0
        miny = (y0 - h) / 2.0
        if rect:
            rect = [_x0 - abs(minx), _y0 - abs(miny), _x1 - abs(minx), _y1 - abs(miny)]
            return rect
        else:
            return None

    def quit_binder(self, rect_tag, x, y):
        if rect_tag not in self.btntag_list:
            self.buttonTXT = self.canvas.create_image(x - 10, y - 10, image=self.photoImg,
                                                      anchor=tk.NW)

            self.btn_rect[y] = [rect_tag, self.buttonTXT]

            self.canvas.tag_bind(self.buttonTXT, "<ButtonPress-1>",
                                 lambda event: self.on_button_press(event, rectangle=True))
            self.btntag_list[rect_tag] = self.buttonTXT
            return

    def on_move(self, event):
        page_id = self.viewer.pageidx
        widget = event.widget
        x_coord = widget.canvasx(event.x)
        y_coord = widget.canvasy(event.y)
        if page_id in self.rectangles:
            for rect in self.rectangles[page_id]:
                if int(y_coord) in range(int(rect[2]), int(rect[4])) and int(x_coord) in range(int(rect[1]),
                                                                                               int(rect[3])):
                    self.rect_id = rect[0]
                    self.quit_binder(rect[0], rect[3], rect[2])
                    break

                if rect[0] in self.btntag_list:
                    self.canvas.delete(self.btntag_list[rect[0]])
                    self.btntag_list.pop(rect[0])

    def on_resize(self, event):
        # determine the ratio of old width/height to new width/height
        wscale = float(event.width) / self.width
        hscale = float(event.height) / self.height
        self.width = event.width
        self.height = event.height

        # resize the canvas
        self.canvas.config(width=self.width, height=self.height)
        # rescale all the objects tagged with the "all" tag
        self.canvas.scale("all", 0, 0, wscale, hscale)
        return
