from tkinter import Tk
from pdfviewer.pdfviewer import PDFViewer

root = Tk()
def callback():
    pdf._to_file()
    root.destroy()

root.protocol("WM_DELETE_WINDOW", callback)
pdf = PDFViewer()
root.mainloop()
