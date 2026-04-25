import customtkinter as ctk

app = ctk.CTk()

tabview = ctk.CTkTabview(app)
tabview.pack(padx=20, pady=20)

tabview.add("Tab 1")
tabview.add("Tab 2")
tabview.add("Tab 3")

def on_tab_change(*args):
    current_tab = tabview.get()
    for name, btn in tabview._segmented_button._buttons_dict.items():
        if name == current_tab:
            btn.configure(text_color=("#ffffff", "#e8edeb"))
        else:
            btn.configure(text_color=("#121715", "#e8edeb"))

tabview.configure(command=on_tab_change)
# call initially
on_tab_change()

app.after(2000, app.destroy)
app.mainloop()
