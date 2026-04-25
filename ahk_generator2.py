import customtkinter as ctk
from tkinter import filedialog, messagebox

class AHKGeneratorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("AHK v2 Script Generator")
        self.geometry("900x700")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.key_mapping = {
            "Left Click": "LButton",
            "Right Click": "RButton",
            "Middle Click": "MButton",
            "Mouse Button 4": "XButton1",
            "Mouse Button 5": "XButton2",
            "Wheel Up": "WheelUp",
            "Wheel Down": "WheelDown",
            "Shift": "Shift",
            "Ctrl": "Ctrl",
            "Alt": "Alt"
        }

        self.available_keys = (
            list("abcdefghijklmnopqrstuvwxyz0123456789") +
            [f"F{i}" for i in range(1, 13)] +
            ["Space", "Enter", "Tab", "Escape", "Backspace"] +
            list(self.key_mapping.keys())
        )

        self.rows = []

        self.setup_ui()

    def setup_ui(self):
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.pack(pady=10, padx=20, fill="x")

        self.game_label = ctk.CTkLabel(self.header_frame, text="Window/Game Name:", font=("Arial", 14, "bold"))
        self.game_label.pack(side="left", padx=10, pady=10)

        self.game_entry = ctk.CTkEntry(self.header_frame, width=300, placeholder_text="e.g. ahk_exe hl2.exe or Game Title")
        self.game_entry.pack(side="left", padx=10, pady=10)

        self.scroll_frame = ctk.CTkScrollableFrame(self, label_text="Keybind Remapping Rows")
        self.scroll_frame.pack(pady=10, padx=20, fill="both", expand=True)

        self.add_row_btn = ctk.CTkButton(self, text="+ Add New Keybind", command=self.add_keybind_row)
        self.add_row_btn.pack(pady=5)

        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(pady=10, padx=20, fill="x")

        self.preview_btn = ctk.CTkButton(self.bottom_frame, text="Preview Code", command=self.preview_code)
        self.preview_btn.pack(side="left", padx=10, pady=10)

        self.save_btn = ctk.CTkButton(self.bottom_frame, text="Generate & Save .ahk", command=self.save_code)
        self.save_btn.pack(side="left", padx=10, pady=10)

        self.preview_textbox = ctk.CTkTextbox(self, height=150)
        self.preview_textbox.pack(pady=10, padx=20, fill="both")

        self.add_keybind_row()

    def add_keybind_row(self):
        row_frame = ctk.CTkFrame(self.scroll_frame)
        row_frame.pack(fill="x", pady=5, padx=5)

        in_label = ctk.CTkLabel(row_frame, text="Input Key:")
        in_label.pack(side="left", padx=5, pady=5)

        in_combo = ctk.CTkComboBox(row_frame, values=self.available_keys, width=120)
        in_combo.pack(side="left", padx=5, pady=5)

        out_label = ctk.CTkLabel(row_frame, text="Output Action:")
        out_label.pack(side="left", padx=5, pady=5)

        out_combo = ctk.CTkComboBox(row_frame, values=self.available_keys, width=120)
        out_combo.pack(side="left", padx=5, pady=5)

        combo_var = ctk.BooleanVar()
        combo_chk = ctk.CTkCheckBox(row_frame, text="Key Combo", variable=combo_var, width=80)
        combo_chk.pack(side="left", padx=5, pady=5)

        spam_var = ctk.BooleanVar()
        spam_chk = ctk.CTkCheckBox(row_frame, text="Auto-Fire", variable=spam_var, width=80)
        spam_chk.pack(side="left", padx=5, pady=5)

        toggle_var = ctk.BooleanVar()
        toggle_chk = ctk.CTkCheckBox(row_frame, text="Toggle", variable=toggle_var, width=80)
        toggle_chk.pack(side="left", padx=5, pady=5)

        def delete_self():
            row_frame.destroy()
            self.rows.remove(row_data)

        delete_btn = ctk.CTkButton(row_frame, text="X", width=30, fg_color="red", hover_color="darkred", command=delete_self)
        delete_btn.pack(side="right", padx=5, pady=5)

        row_data = {
            "in_combo": in_combo,
            "out_combo": out_combo,
            "is_combo": combo_var,
            "is_spam": spam_var,
            "is_toggle": toggle_var
        }
        self.rows.append(row_data)

    def translate_key(self, key_string):
        return self.key_mapping.get(key_string, key_string)

    def format_combo_keys(self, out_string):
        keys = [k.strip() for k in out_string.split('+')]
        translated_keys = [self.translate_key(k) for k in keys]
        
        down_strokes = "".join([f"{{{k} down}}" for k in translated_keys])
        up_strokes = "".join([f"{{{k} up}}" for k in reversed(translated_keys)])
        
        return f"{down_strokes}{up_strokes}"

    def generate_ahk_code(self):
        game_name = self.game_entry.get().strip()
        
        script = "#Requires AutoHotkey v2.0\n"
        script += "#SingleInstance Force\n\n"
        script += "F12::Suspend\n\n"
        
        if game_name:
            script += f'#HotIf WinActive("{game_name}")\n\n'

        for row in self.rows:
            raw_in = row["in_combo"].get()
            raw_out = row["out_combo"].get()
            is_combo = row["is_combo"].get()
            is_spam = row["is_spam"].get()
            is_toggle = row["is_toggle"].get()

            if not raw_in or not raw_out:
                continue

            ahk_in = self.translate_key(raw_in)
            ahk_out = self.translate_key(raw_out)

            if is_combo:
                send_payload = self.format_combo_keys(raw_out)
            else:
                send_payload = f"{{{ahk_out}}}"

            if is_spam:
                script += f"*{ahk_in}:: {{\n"
                script += f'    while GetKeyState("{ahk_in}", "P") {{\n'
                if is_combo:
                    script += f'        Send("{send_payload}")\n'
                else:
                    script += f'        Send("{{{ahk_out}}}")\n'
                script += '        Sleep(50)\n'
                script += '    }\n'
                script += '}\n\n'

            elif is_toggle:
                script += f"*{ahk_in}:: {{\n"
                script += '    static toggle := false\n'
                script += '    toggle := !toggle\n'
                script += '    if (toggle) {\n'
                
                if is_combo:
                    down_strokes = "".join([f"{{{self.translate_key(k.strip())} down}}" for k in raw_out.split('+')])
                    script += f'        Send("{down_strokes}")\n'
                else:
                    script += f'        Send("{{{ahk_out} down}}")\n'
                
                script += '    } else {\n'
                
                if is_combo:
                    up_strokes = "".join([f"{{{self.translate_key(k.strip())} up}}" for k in reversed(raw_out.split('+'))])
                    script += f'        Send("{up_strokes}")\n'
                else:
                    script += f'        Send("{{{ahk_out} up}}")\n'
                
                script += '    }\n'
                script += '}\n\n'

            else:
                if is_combo:
                    script += f"*{ahk_in}::Send(\"{send_payload}\")\n\n"
                else:
                    script += f"{ahk_in}::{ahk_out}\n\n"

        if game_name:
            script += "#HotIf\n"

        return script

    def preview_code(self):
        code = self.generate_ahk_code()
        self.preview_textbox.delete("1.0", "end")
        self.preview_textbox.insert("1.0", code)

    def save_code(self):
        code = self.generate_ahk_code()
        if not code.strip():
            messagebox.showwarning("Warning", "No code generated to save.")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".ahk",
            filetypes=[("AutoHotkey Scripts", "*.ahk"), ("All Files", "*.*")],
            title="Save AHK Script"
        )
        
        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(code)
                messagebox.showinfo("Success", f"Script saved successfully to:\n{file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file:\n{str(e)}")

if __name__ == "__main__":
    app = AHKGeneratorApp()
    app.mainloop()