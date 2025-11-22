from tkinter import ttk

def setup_styles(root):
    style = ttk.Style(master=root)
    style.theme_use("default")

    style.configure("Card.TLabelframe", padding=(12, 10))
    style.configure("Card.TLabelframe.Label", font=("Segoe UI", 11, "bold"))

    style.configure("Key.TLabel", foreground="#999", font=("Segoe UI", 10))
    style.configure("Val.TLabel", font=("Consolas", 12))
