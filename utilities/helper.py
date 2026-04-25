import os
import sys
import json
import random
import re
import subprocess
import questionary
from pathlib import Path

# START: CONFIGURATION & CONSTANTS
SAVE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\utilities"
DEFAULT_RENAME_DIR = r"G:\My Drive\My Epic Work"
GS_PATH = r"C:\Program Files\gs\gs10.06.0\bin\gswin64c.exe"
# END: CONFIGURATION


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def parse_dragged_paths(raw_input):
    paths = []

    # PowerShell single-quote format: & 'path one' & 'path two'
    single_quoted = re.findall(r"'((?:[^']|'')+)'", raw_input)
    if single_quoted:
        for p in single_quoted:
            p = p.replace("''", "'").strip()
            if p:
                paths.append(p)
        return paths

    # Standard double-quote format: "path one" "path two"
    double_quoted = re.findall(r'"([^"]+)"', raw_input)
    if double_quoted:
        for p in double_quoted:
            p = p.strip()
            if p:
                paths.append(p)
        return paths

    # Fallback: unquoted space-separated tokens
    for token in raw_input.split():
        token = token.strip()
        if token and token != "&":
            paths.append(token)
    return paths


def get_file_size_exact(file_path):
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def get_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)


def make_output_path(input_path, suffix):
    base, ext = os.path.splitext(input_path)
    return f"{base}_{suffix}{ext}"


# ─────────────────────────────────────────────────────────
# PDF HELPERS
# ─────────────────────────────────────────────────────────

def ask_pdf_input():
    print("\nDrag & drop a PDF file here (or paste its path):")
    raw = input("> ").strip().strip('"').strip("'")
    if not os.path.isfile(raw):
        print(f"[!] File not found: {raw}")
        return None
    if not raw.lower().endswith(".pdf"):
        print("[!] File does not appear to be a PDF.")
        return None
    return raw


def parse_ranges(range_str, total_pages):
    ranges = []
    parts = re.split(r'[,،+]', range_str)
    for part in parts:
        part = part.strip()
        m = re.match(r'^(\d+)\s*[-–]\s*(\d+)$', part)
        if m:
            s, e = int(m.group(1)), int(m.group(2))
            if s < 1 or e > total_pages or s > e:
                print(f"  [!] Invalid range {s}-{e} (PDF has {total_pages} pages). Skipping.")
                continue
            ranges.append((s, e))
        elif re.match(r'^\d+$', part):
            n = int(part)
            if 1 <= n <= total_pages:
                ranges.append((n, n))
            else:
                print(f"  [!] Page {n} out of range. Skipping.")
        else:
            print(f"  [!] Could not parse '{part}'. Skipping.")
    return ranges


def ask_scope(total_pages):
    choice = questionary.select(
        "Apply to:",
        choices=[
            "Full PDF",
            "Specific page ranges"
        ]
    ).ask()
    if choice == "Full PDF":
        return [(1, total_pages)]
    print(f"\nPDF has {total_pages} pages.")
    print("Enter ranges like:  3-43, 654-765  (comma or + separated)")
    raw = input("> ").strip()
    return parse_ranges(raw, total_pages)


def ask_output_mode():
    return questionary.select(
        "Output mode:",
        choices=[
            "Merge all ranges into one file",
            "Separate file per range"
        ]
    ).ask()


def get_pdf_total_pages(path):
    try:
        from pypdf import PdfReader
        return len(PdfReader(path).pages)
    except Exception as e:
        print(f"  [!] Could not open PDF: {e}")
        return None


# ─────────────────────────────────────────────────────────
# COMPRESSION ENGINES
# ─────────────────────────────────────────────────────────

def compress_ghostscript(input_path, output_path):
    cmd = [
        GS_PATH,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/ebook",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        "-dColorImageResolution=150",
        "-dGrayImageResolution=150",
        "-dMonoImageResolution=300",
        "-dDownsampleColorImages=true",
        "-dDownsampleGrayImages=true",
        "-dDownsampleMonoImages=true",
        "-dColorImageDownsampleType=/Bicubic",
        "-dGrayImageDownsampleType=/Bicubic",
        f"-sOutputFile={output_path}",
        input_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [!] Ghostscript error: {result.stderr.strip()}")
        return False
    return True


def compress_fitz(input_path, output_path):
    try:
        import fitz
    except ImportError:
        print("  [!] PyMuPDF not installed. Run: pip install pymupdf")
        return False

    doc = fitz.open(input_path)
    seen_xrefs = set()
    for page in doc:
        for img in page.get_images(full=True):
            xref = img[0]
            if xref in seen_xrefs:
                continue
            seen_xrefs.add(xref)
            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                if pix.width > 1500 or pix.height > 1500:
                    scale = min(1500 / pix.width, 1500 / pix.height)
                    pix = pix.scale_by(scale)
                doc.update_stream(xref, pix.tobytes("jpeg", jpg_quality=75))
            except Exception:
                continue
    doc.save(output_path, garbage=4, deflate=True, deflate_images=True,
             deflate_fonts=True, clean=True)
    doc.close()
    return True


def compress_pikepdf(input_path, output_path):
    try:
        import pikepdf
    except ImportError:
        print("  [!] pikepdf not installed. Run: pip install pikepdf")
        return False

    try:
        from PIL import Image
        import io
        PIL_AVAILABLE = True
    except ImportError:
        PIL_AVAILABLE = False
        print("  [!] Pillow not found — image recompression disabled (structure only). pip install Pillow")

    with pikepdf.open(input_path) as pdf:
        if PIL_AVAILABLE:
            for page in pdf.pages:
                if "/Resources" not in page:
                    continue
                resources = page["/Resources"]
                if "/XObject" not in resources:
                    continue
                xobjects = resources["/XObject"]
                for name in list(xobjects.keys()):
                    xobj = xobjects[name]
                    try:
                        if xobj.get("/Subtype") != "/Image":
                            continue
                        raw = bytes(xobj.read_raw_bytes())
                        img = Image.open(io.BytesIO(raw))
                        w, h = img.size
                        if w > 1500 or h > 1500:
                            scale = min(1500 / w, 1500 / h)
                            img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
                        if img.mode == "RGBA":
                            img = img.convert("RGB")
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=75, optimize=True)
                        buf.seek(0)
                        xobj.write(buf.read(), filter=pikepdf.Name("/DCTDecode"))
                    except Exception:
                        continue
        pdf.save(output_path, compress_streams=True,
                 object_stream_mode=pikepdf.ObjectStreamMode.generate,
                 linearize=True)
    return True


def remove_images_fitz(input_path, output_path):
    try:
        import fitz
    except ImportError:
        print("  [!] PyMuPDF not installed. Run: pip install pymupdf")
        return False

    doc = fitz.open(input_path)
    for page in doc:
        image_list = page.get_images(full=True)
        for img in image_list:
            xref = img[0]
            try:
                page.delete_image(xref)
            except Exception:
                try:
                    doc.update_stream(xref, b"")
                except Exception:
                    pass
    doc.save(output_path, garbage=4, deflate=True, clean=True)
    doc.close()
    return True


def extract_pages_to_pdf(input_path, output_path, ranges):
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("  [!] pypdf not installed. Run: pip install pypdf")
        return False

    reader = PdfReader(input_path)
    writer = PdfWriter()
    for (s, e) in ranges:
        for i in range(s - 1, e):
            writer.add_page(reader.pages[i])
    with open(output_path, "wb") as f:
        writer.write(f)
    return True


def print_compression_result(input_path, output_path):
    if os.path.exists(output_path):
        before = get_size_mb(input_path)
        after = get_size_mb(output_path)
        saved = before - after
        pct = (saved / before * 100) if before > 0 else 0
        print(f"  Before : {before:.2f} MB")
        print(f"  After  : {after:.2f} MB")
        print(f"  Saved  : {saved:.2f} MB  ({pct:.1f}%)")
        print(f"  Output : {output_path}")
    else:
        print("  [!] Output file was not created.")


# ─────────────────────────────────────────────────────────
# SHARED FUNCTION: GENERATE & SAVE JSON
# ─────────────────────────────────────────────────────────

def generate_and_save_competition(file_data_list):
    if not file_data_list:
        print("No data to process.")
        return

    json_output = []
    for i in range(0, len(file_data_list), 2):
        if i + 1 >= len(file_data_list):
            break
        item1 = file_data_list[i]
        item2 = file_data_list[i + 1]
        rating1 = random.uniform(1000.0, 3000.0)
        rating2 = random.uniform(1000.0, 3000.0)
        match_obj = {
            "videos": [item1['name'], item2['name']],
            "rating": [rating1, rating2],
            "file_size": [item1['size'], item2['size']],
            "mode": 1,
            "num_videos": 2,
            "ranking_type": "winner_only",
            "competition_type": "balanced_random"
        }
        json_output.append(match_obj)

    final_json_str = json.dumps(json_output, indent=4)
    print("\n" + final_json_str + "\n")

    save_choice = questionary.confirm("Do you want to save this to a file?").ask()

    if save_choice:
        suffix_choice = questionary.select(
            "Choose filename suffix:",
            choices=["tik", "pic", "Dip"]
        ).ask()

        final_suffix = suffix_choice
        if suffix_choice == "Dip":
            final_suffix = "Dib"

        random_digits = random.randint(1000, 9999)
        filename = f"topcut_elo_videos_{final_suffix}_{random_digits}.json"

        if not os.path.exists(SAVE_DIR):
            try:
                os.makedirs(SAVE_DIR)
            except OSError as e:
                print(f"Error creating directory: {e}")
                return

        full_save_path = os.path.join(SAVE_DIR, filename)
        try:
            with open(full_save_path, 'w', encoding='utf-8') as f:
                f.write(final_json_str)
            print(f"Successfully saved to: {full_save_path}")
        except Exception as e:
            print(f"Error saving file: {e}")


# ─────────────────────────────────────────────────────────
# FEATURE 1: EXTRACT FILE SIZES
# ─────────────────────────────────────────────────────────

def feature_extract_sizes(working_dir):
    print("\n--- Extract File Sizes ---")

    choice = questionary.select(
        "Choose extraction source:",
        choices=[
            "From all files in the Working Directory",
            "Drag & Drop files (or paste paths)"
        ]
    ).ask()

    extracted_data = []

    if choice == "From all files in the Working Directory":
        if not os.path.isdir(working_dir):
            print(f"Error: The directory {working_dir} does not exist.")
            return
        files = [f for f in os.listdir(working_dir) if os.path.isfile(os.path.join(working_dir, f))]
        for f in files:
            full_path = os.path.join(working_dir, f)
            size = get_file_size_exact(full_path)
            extracted_data.append({'name': f, 'size': size})
    else:
        print("\nPlease drag and drop your files here:")
        user_input = input("> ")
        paths = parse_dragged_paths(user_input)
        for p in paths:
            p = p.strip().strip("'").strip('"')
            if os.path.exists(p) and os.path.isfile(p):
                size = get_file_size_exact(p)
                name = os.path.basename(p)
                extracted_data.append({'name': name, 'size': size})

    print("\n--- Output ---")
    if not extracted_data:
        print("No files found.")
    else:
        for item in extracted_data:
            print(f"{item['size']}  ({item['name']})")

    if extracted_data:
        print("\n-------------------------")
        create_now = questionary.confirm("Do you want to create a competition from these files?").ask()
        if create_now:
            generate_and_save_competition(extracted_data)
        else:
            input("\nPress Enter to return to menu...")
    else:
        input("\nPress Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 2: COMPETITION GENERATOR
# ─────────────────────────────────────────────────────────

def feature_create_competition():
    print("\n--- Create Competition JSON ---")
    print("Drag & Drop your files here OR paste file sizes:")
    user_input = input("> ")

    paths = parse_dragged_paths(user_input)
    file_data_list = []

    is_paths = any(os.path.exists(p) for p in paths) if paths else False

    if is_paths:
        for p in paths:
            if os.path.exists(p) and os.path.isfile(p):
                size = get_file_size_exact(p)
                name = os.path.basename(p)
                file_data_list.append({'name': name, 'size': size})
    else:
        clean_input = re.sub(r'[^\d\s]', '', user_input)
        tokens = clean_input.split()
        for t in tokens:
            if t.isdigit():
                size = int(t)
                rand_name = f"{random.randint(1000, 9999)}_video_{random.randint(100000, 999999)}.mp4"
                file_data_list.append({'name': rand_name, 'size': size})

    if not file_data_list:
        print("No valid input found.")
        input("Press Enter...")
        return

    generate_and_save_competition(file_data_list)
    input("\nPress Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 3: REMOVE DUPLICATES
# ─────────────────────────────────────────────────────────

def feature_remove_duplicates(working_dir):
    print("\n--- Remove Duplicates ---")
    if not os.path.isdir(working_dir):
        print("Invalid directory.")
        return

    grouped_files = {}
    pattern = re.compile(r'^(.*?)(\s\(\d+\))?(\.[^.]*)?$')

    files_in_dir = [f for f in os.listdir(working_dir) if os.path.isfile(os.path.join(working_dir, f))]

    for filename in files_in_dir:
        match = pattern.match(filename)
        if match:
            base_name = match.group(1)
            number_part = match.group(2)
            extension = match.group(3) if match.group(3) else ""
            priority = 0
            if number_part:
                num_str = re.search(r'\d+', number_part).group()
                priority = int(num_str)
            full_path = os.path.join(working_dir, filename)
            file_size = get_file_size_exact(full_path)
            unique_key = (base_name, extension, file_size)
            if unique_key not in grouped_files:
                grouped_files[unique_key] = []
            grouped_files[unique_key].append({
                "priority": priority,
                "path": full_path,
                "name": filename
            })

    files_to_delete = []
    for key, file_list in grouped_files.items():
        if len(file_list) > 1:
            file_list.sort(key=lambda x: x["priority"])
            duplicates_to_remove = file_list[1:]
            for dup in duplicates_to_remove:
                files_to_delete.append(dup['path'])

    if not files_to_delete:
        print("\nNo duplicates found.")
        input("\nPress Enter to return to menu...")
        return

    proceed = questionary.confirm(f"Found {len(files_to_delete)} duplicate(s). Delete?").ask()

    if proceed:
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                print(f"  Deleted: {os.path.basename(file_path)}")
            except Exception:
                pass

    input("\nPress Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 4: INTERACTIVE RENAMER
# ─────────────────────────────────────────────────────────

def feature_interactive_renamer():
    current_path = DEFAULT_RENAME_DIR

    if not os.path.exists(current_path):
        print(f"Default path not found: {current_path}")
        print("Falling back to current directory.")
        current_path = os.getcwd()

    while True:
        clear_screen()
        print(f"📂 Current Folder: {current_path}\n")

        try:
            items = os.listdir(current_path)
        except PermissionError:
            print("Permission Denied.")
            input("Press Enter to go back...")
            return

        dirs = sorted([d for d in items if os.path.isdir(os.path.join(current_path, d))])

        nav_choices = [
            questionary.Choice("🎯 [ SELECT THIS FOLDER TO WORK ]", value="SELECT_CURRENT"),
            questionary.Choice("⬆️  [ .. ] (Go Up)", value="GO_UP"),
            questionary.Separator()
        ] + [questionary.Choice(f"📁 {d}", value=d) for d in dirs]

        nav_choices.append(questionary.Separator())
        nav_choices.append(questionary.Choice("❌ Exit to Main Menu", value="EXIT_MENU"))

        selection = questionary.select(
            "Navigate to a folder:",
            choices=nav_choices,
            use_indicator=True
        ).ask()

        if selection == "EXIT_MENU":
            return
        elif selection == "GO_UP":
            current_path = os.path.dirname(current_path)
        elif selection == "SELECT_CURRENT":
            break
        else:
            current_path = os.path.join(current_path, selection)

    clear_screen()
    print(f"🔨 Working in: {current_path}")

    files = sorted([f for f in os.listdir(current_path) if os.path.isfile(os.path.join(current_path, f))])

    numbered_files = []
    regex_pattern = re.compile(r'^(\d+)(\s+.*)$')

    for f in files:
        if regex_pattern.match(f):
            numbered_files.append(f)

    if not numbered_files:
        print("❌ No numbered files found in this folder (e.g., '1 file.txt' or '01 file.txt').")
        input("Press Enter to return...")
        return

    selected_files = questionary.checkbox(
        "Select files to rename (Space to select, Enter to confirm):",
        choices=[questionary.Choice(f, checked=False) for f in numbered_files]
    ).ask()

    if not selected_files:
        print("No files selected.")
        input("Press Enter...")
        return

    action = questionary.select(
        "What do you want to do with the selected files?",
        choices=[
            "1. Shift Numbers (e.g., +1, -2)",
            "2. Add Leading Zeros (e.g., 1 -> 01)"
        ]
    ).ask()

    if not action:
        return

    if action.startswith("1"):
        offset_str = questionary.text("Enter number offset (e.g. 2 for +2, -1 for -1):").ask()
        try:
            offset = int(offset_str)
        except ValueError:
            print("Invalid number.")
            input("Press Enter...")
            return

        if offset == 0:
            print("Offset is 0. Nothing to do.")
            input("Press Enter...")
            return

        print(f"\nPlanning to shift numbers by {offset:+d}...")
        reverse_sort = (offset > 0)

        files_to_process = []
        for filename in selected_files:
            match = regex_pattern.match(filename)
            if match:
                num_str = match.group(1)
                rest_str = match.group(2)
                current_num = int(num_str)
                files_to_process.append({
                    "original": filename,
                    "num_len": len(num_str),
                    "current_num": current_num,
                    "rest": rest_str
                })

        files_to_process.sort(key=lambda x: x["current_num"], reverse=reverse_sort)

        renamed_count = 0
        for item in files_to_process:
            new_num = item["current_num"] + offset
            if new_num < 0:
                print(f"⚠️ Skipping {item['original']}: Resulting number would be negative.")
                continue
            new_num_str = f"{new_num:0{item['num_len']}d}"
            new_filename = f"{new_num_str}{item['rest']}"
            old_path = os.path.join(current_path, item["original"])
            new_path = os.path.join(current_path, new_filename)
            if os.path.exists(new_path):
                print(f"⚠️ Error: Cannot rename {item['original']} to {new_filename}. File already exists!")
                continue
            try:
                os.rename(old_path, new_path)
                print(f"✅ {item['original']} -> {new_filename}")
                renamed_count += 1
            except Exception as e:
                print(f"❌ Failed to rename {item['original']}: {e}")

        print(f"\nDone. Renamed {renamed_count} files.")
        input("Press Enter to return to menu...")

    elif action.startswith("2"):
        print("\nAdding leading zeros...")
        renamed_count = 0

        for filename in selected_files:
            match = regex_pattern.match(filename)
            if match:
                num_str = match.group(1)
                rest_str = match.group(2)
                current_num = int(num_str)
                new_num_str = f"{current_num:02d}"
                new_filename = f"{new_num_str}{rest_str}"
                if new_filename == filename:
                    print(f"⏭️ Skipping {filename}: Already has 2 digits.")
                    continue
                old_path = os.path.join(current_path, filename)
                new_path = os.path.join(current_path, new_filename)
                if os.path.exists(new_path):
                    print(f"⚠️ Error: Cannot rename {filename}. The file '{new_filename}' already exists!")
                    continue
                try:
                    os.rename(old_path, new_path)
                    print(f"✅ {filename} -> {new_filename}")
                    renamed_count += 1
                except Exception as e:
                    print(f"❌ Failed to rename {filename}: {e}")

        print(f"\nDone. Renamed {renamed_count} files.")
        input("Press Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 5: PDF SPLIT
# ─────────────────────────────────────────────────────────

def feature_pdf_split():
    print("\n--- PDF Split ---")

    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        print("[!] pypdf not installed. Run: pip install pypdf")
        input("Press Enter...")
        return

    pdf_path = ask_pdf_input()
    if not pdf_path:
        input("Press Enter...")
        return

    total_pages = get_pdf_total_pages(pdf_path)
    if not total_pages:
        input("Press Enter...")
        return

    print(f"  PDF has {total_pages} pages.")

    scope_choice = questionary.select(
        "What pages do you want to extract?",
        choices=[
            "Full PDF (all pages)",
            "Single range  (e.g. 3-43)",
            "Multiple ranges  (e.g. 3-43, 654-765)"
        ]
    ).ask()

    if scope_choice == "Full PDF (all pages)":
        ranges = [(1, total_pages)]
    else:
        print("\nEnter ranges (comma or + separated, e.g.  3-43, 654-765):")
        raw = input("> ").strip()
        ranges = parse_ranges(raw, total_pages)
        if not ranges:
            print("[!] No valid ranges entered.")
            input("Press Enter...")
            return

    output_mode = "Merge all ranges into one file"
    if len(ranges) > 1:
        output_mode = ask_output_mode()

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    if output_mode == "Merge all ranges into one file" or len(ranges) == 1:
        label = "_".join(f"{s}-{e}" for s, e in ranges)
        out_path = os.path.join(base_dir, f"{base_name}_pages_{label}.pdf")
        reader = PdfReader(pdf_path)
        writer = PdfWriter()
        for (s, e) in ranges:
            for i in range(s - 1, e):
                writer.add_page(reader.pages[i])
        with open(out_path, "wb") as f:
            writer.write(f)
        print(f"\n  ✅ Saved: {out_path}")
        print(f"     Pages: {sum(e - s + 1 for s, e in ranges)}")
    else:
        reader = PdfReader(pdf_path)
        for idx, (s, e) in enumerate(ranges, 1):
            out_path = os.path.join(base_dir, f"{base_name}_pages_{s}-{e}.pdf")
            writer = PdfWriter()
            for i in range(s - 1, e):
                writer.add_page(reader.pages[i])
            with open(out_path, "wb") as f:
                writer.write(f)
            print(f"  ✅ Range {idx} ({s}-{e}) -> {os.path.basename(out_path)}")

    input("\nPress Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 6: PDF TO TEXT
# ─────────────────────────────────────────────────────────

def _build_filter_pattern(raw_query):
    parts = re.split(r'\bOR\b', raw_query)
    sub_patterns = []
    for part in parts:
        phrase = part.strip()
        if phrase:
            sub_patterns.append(re.escape(phrase))
    combined = "|".join(sub_patterns)
    return re.compile(combined, re.IGNORECASE)


def _extract_context_snippets(page_text, pattern, words_around):
    words = page_text.split()
    if not words:
        return []

    word_positions = []
    cursor = 0
    for w in words:
        idx = page_text.find(w, cursor)
        word_positions.append(idx)
        cursor = idx + len(w)

    hit_word_indices = set()
    for m in pattern.finditer(page_text):
        match_start = m.start()
        match_end = m.end()
        for wi, pos in enumerate(word_positions):
            w_end = pos + len(words[wi])
            if pos <= match_end and w_end >= match_start:
                hit_word_indices.add(wi)

    if not hit_word_indices:
        return []

    covered = []
    for hit_wi in sorted(hit_word_indices):
        start_wi = max(0, hit_wi - words_around)
        end_wi = min(len(words) - 1, hit_wi + words_around)
        covered.append((start_wi, end_wi))

    merged = []
    for span in covered:
        if merged and span[0] <= merged[-1][1] + 1:
            merged[-1] = (merged[-1][0], max(merged[-1][1], span[1]))
        else:
            merged.append(list(span))

    snippets = []
    for (s, e) in merged:
        snippets.append(" ".join(words[s:e + 1]))
    return snippets


def _ask_pdf_paths_batch():
    batch_choice = questionary.select(
        "How many PDFs?",
        choices=[
            "Single PDF",
            "Multiple PDFs  (batch)"
        ]
    ).ask()

    if batch_choice == "Single PDF":
        pdf_path = ask_pdf_input()
        if not pdf_path:
            return None, False
        return [pdf_path], False
    else:
        print("\nDrag & drop all PDF files here (or paste paths), then press Enter:")
        raw = input("> ").strip()
        paths = parse_dragged_paths(raw)
        valid = []
        for p in paths:
            p = p.strip().strip('"').strip("'")
            if os.path.isfile(p) and p.lower().endswith(".pdf"):
                valid.append(p)
            else:
                print(f"  [!] Skipping (not a PDF or not found): {p}")
        if not valid:
            print("[!] No valid PDF files found.")
            return None, True
        print(f"  → {len(valid)} PDF(s) loaded.")
        return valid, True


def _get_cache_path(pdf_path):
    base = os.path.splitext(pdf_path)[0]
    return base + ".__pdfcache__.txt"


def _build_cache(pdf_path):
    try:
        from pypdf import PdfReader
        import pypdf
    except ImportError:
        print("  [!] pypdf not installed.")
        return None

    try:
        pypdf.constants.MAX_STRING_LENGTH = 500 * 1024 * 1024
    except Exception:
        pass
    try:
        from pypdf._utils import MAX_OBJECT_SIZE
    except Exception:
        pass

    reader = PdfReader(pdf_path)
    pages_text = []
    skipped = 0
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
            skipped += 1
        pages_text.append(text)

    if skipped:
        print(f"  [!] {skipped} page(s) could not be extracted and were skipped.")

    cache_path = _get_cache_path(pdf_path)
    with open(cache_path, "w", encoding="utf-8") as f:
        import json
        json.dump(pages_text, f, ensure_ascii=False)
    return pages_text


def _load_cache(pdf_path):
    cache_path = _get_cache_path(pdf_path)
    if not os.path.exists(cache_path):
        return None
    try:
        import json
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _get_pages_text(pdf_path, force_rebuild=False):
    if not force_rebuild:
        cached = _load_cache(pdf_path)
        if cached is not None:
            return cached, True
    pages = _build_cache(pdf_path)
    return pages, False


def _process_single_pdf_to_text(pdf_path, ranges, use_filter,
                                 filter_pattern, raw_query,
                                 extract_style, words_around,
                                 pages_text=None):
    if pages_text is None:
        try:
            from pypdf import PdfReader
            import pypdf
        except ImportError:
            return None, 0
        try:
            pypdf.constants.MAX_STRING_LENGTH = 500 * 1024 * 1024
        except Exception:
            pass
        reader = PdfReader(pdf_path)
        def get_page(i):
            try:
                return reader.pages[i].extract_text() or ""
            except Exception:
                return ""
    else:
        get_page = lambda i: pages_text[i] if i < len(pages_text) else ""

    if not use_filter:
        parts = []
        for (s, e) in ranges:
            parts.append(f"\n{'='*60}\n  Pages {s} – {e}\n{'='*60}\n")
            for i in range(s - 1, e):
                parts.append(f"\n--- Page {i+1} ---\n{get_page(i)}")
        return "".join(parts), 0
    else:
        parts = []
        total_hits = 0
        for (s, e) in ranges:
            for i in range(s - 1, e):
                page_num = i + 1
                page_text = get_page(i)
                if not filter_pattern.search(page_text):
                    continue
                total_hits += 1
                parts.append(f"\n{'='*60}")
                parts.append(f"  Page {page_num}  [MATCH]")
                parts.append(f"{'='*60}\n")
                if extract_style.startswith("Full"):
                    parts.append(page_text)
                else:
                    snippets = _extract_context_snippets(page_text, filter_pattern, words_around)
                    for si, snippet in enumerate(snippets, 1):
                        if len(snippets) > 1:
                            parts.append(f"  [Excerpt {si}]")
                        parts.append(f"  ...{snippet}...")
        mode_label = "Full page" if extract_style.startswith("Full") else f"{words_around} words around match"
        header = (
            f"File   : {pdf_path}\n"
            f"Filter : {raw_query}\n"
            f"Mode   : {mode_label}\n"
            f"Pages with matches: {total_hits}\n"
            f"{'─'*60}\n"
        )
        return header + "\n".join(parts), total_hits

def feature_pdf_to_text():
    print("\n--- PDF to Text ---")

    try:
        from pypdf import PdfReader
    except ImportError:
        print("[!] pypdf not installed. Run: pip install pypdf")
        input("Press Enter...")
        return

    pdf_paths, is_batch = _ask_pdf_paths_batch()
    if not pdf_paths:
        input("Press Enter...")
        return

    scope_choice = questionary.select(
        "Which pages to convert?",
        choices=[
            "Full PDF (all pages)",
            "Single range  (e.g. 3-43)",
            "Multiple ranges  (e.g. 3-43, 654-765)"
        ]
    ).ask()

    ranges_per_pdf = {}
    if scope_choice == "Full PDF (all pages)":
        for p in pdf_paths:
            tp = get_pdf_total_pages(p)
            if tp:
                ranges_per_pdf[p] = [(1, tp)]
    else:
        if is_batch:
            print("\nEnter page ranges to apply to ALL PDFs (comma or + separated):")
        else:
            tp = get_pdf_total_pages(pdf_paths[0])
            print(f"\nPDF has {tp} pages. Enter ranges:")
        raw = input("> ").strip()
        for p in pdf_paths:
            tp = get_pdf_total_pages(p)
            if not tp:
                continue
            rngs = parse_ranges(raw, tp)
            if rngs:
                ranges_per_pdf[p] = rngs
            else:
                print(f"  [!] No valid ranges for {os.path.basename(p)} — skipping.")

    if not ranges_per_pdf:
        print("[!] Nothing to process.")
        input("Press Enter...")
        return

    mode_choice = questionary.select(
        "Output mode:",
        choices=[
            "Full text  (no filtering)",
            "Filter by keyword / phrase  (extract context only)"
        ]
    ).ask()

    use_filter = mode_choice.startswith("Filter")
    filter_pattern = None
    raw_query = ""
    extract_style = "Full page"
    words_around = 60

    if use_filter:
        print("\nFilter syntax:")
        print("  Single word/phrase : anemia")
        print("  OR logic           : anemia OR htn OR fatigue")
        print("  Exact phrase       : anemia cause htn")
        print("\nEnter your filter query:")
        raw_query = input("> ").strip()
        if not raw_query:
            print("[!] Empty query — running without filter.")
            use_filter = False
        else:
            filter_pattern = _build_filter_pattern(raw_query)
            extract_style = questionary.select(
                "When a match is found, what to extract?",
                choices=[
                    "Full page",
                    "Words around match  (you set how many)"
                ]
            ).ask()
            if extract_style.startswith("Words"):
                print("\nHow many words BEFORE and AFTER each match?")
                print("  Examples:  30 = ~2 sentences,  60 = ~1 paragraph,  100 = wide context")
                print("  Overlapping matches are merged automatically.")
                raw_n = input("  Words [60]: ").strip()
                words_around = int(raw_n) if raw_n.isdigit() else 60
                print(f"  → {words_around} words before & after. Overlaps merged.")

    output_mode_plain = "Merge all ranges into one file"
    if not use_filter and not is_batch:
        rngs = list(ranges_per_pdf.values())[0]
        if len(rngs) > 1:
            output_mode_plain = ask_output_mode()

    print(f"\n  Processing {len(ranges_per_pdf)} PDF(s)...")

    results = {}
    for pdf_path, ranges in ranges_per_pdf.items():
        pdf_name = os.path.basename(pdf_path)
        pages_text = None

        if use_filter:
            cached_data, from_cache = _get_pages_text(pdf_path)
            if from_cache:
                print(f"  ⚡ {pdf_name} (using cached text) ...", end=" ", flush=True)
            else:
                print(f"  ⏳ {pdf_name} (converting & caching) ...", end=" ", flush=True)
            pages_text = cached_data
        else:
            print(f"  ⏳ {pdf_name} ...", end=" ", flush=True)

        result_content, hit_count = _process_single_pdf_to_text(
            pdf_path, ranges, use_filter,
            filter_pattern, raw_query,
            extract_style, words_around,
            pages_text=pages_text
        )
        results[pdf_path] = {"content": result_content, "hits": hit_count, "name": pdf_name}
        if use_filter:
            print(f"{hit_count} page(s) matched.")
        else:
            print("done.")

    safe_query = re.sub(r'[^\w\s]', '', raw_query).strip().replace(" ", "_")[:40] if raw_query else ""
    mode_tag = "fullpage" if extract_style.startswith("Full") else f"{words_around}words"

    if not use_filter:
        if is_batch:
            for pdf_path, data in results.items():
                base_dir = os.path.dirname(pdf_path)
                base_name = os.path.splitext(data["name"])[0]
                out_path = os.path.join(base_dir, f"{base_name}_text.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(data["content"])
                print(f"  ✅ {data['name']} → {os.path.basename(out_path)}")
        else:
            pdf_path = list(results.keys())[0]
            data = results[pdf_path]
            base_dir = os.path.dirname(pdf_path)
            base_name = os.path.splitext(data["name"])[0]
            ranges = ranges_per_pdf[pdf_path]
            if output_mode_plain == "Merge all ranges into one file" or len(ranges) == 1:
                label = "_".join(f"{s}-{e}" for s, e in ranges)
                out_path = os.path.join(base_dir, f"{base_name}_text_{label}.txt")
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(data["content"])
                print(f"\n  ✅ Saved: {out_path}")
            else:
                reader = PdfReader(pdf_path)
                for idx, (s, e) in enumerate(ranges, 1):
                    out_path = os.path.join(base_dir, f"{base_name}_text_{s}-{e}.txt")
                    parts = [f"\n--- Page {i+1} ---\n{reader.pages[i].extract_text() or ''}" for i in range(s-1, e)]
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write("".join(parts))
                    print(f"  ✅ Range {idx} ({s}-{e}) → {os.path.basename(out_path)}")
    else:
        if is_batch:
            save_choice = questionary.select(
                "Save filtered results as:",
                choices=[
                    "Separate file per PDF",
                    "One combined file  (sections per PDF)"
                ]
            ).ask()

            first_pdf = list(results.keys())[0]
            output_dir = os.path.dirname(first_pdf)

            if save_choice == "Separate file per PDF":
                for pdf_path, data in results.items():
                    base_dir = os.path.dirname(pdf_path)
                    base_name = os.path.splitext(data["name"])[0]
                    out_path = os.path.join(base_dir, f"{base_name}_filtered_{safe_query}_{mode_tag}.txt")
                    with open(out_path, "w", encoding="utf-8") as f:
                        f.write(data["content"])
                    print(f"  ✅ {data['name']} → {os.path.basename(out_path)}  ({data['hits']} pages matched)")
            else:
                combined_path = os.path.join(output_dir, f"COMBINED_filtered_{safe_query}_{mode_tag}.txt")
                with open(combined_path, "w", encoding="utf-8") as f:
                    f.write(f"Combined Filter Results\n")
                    f.write(f"Query  : {raw_query}\n")
                    f.write(f"Mode   : {'Full page' if extract_style.startswith('Full') else f'{words_around} words around match'}\n")
                    f.write(f"PDFs   : {len(results)}\n")
                    f.write("=" * 60 + "\n\n")
                    for pdf_path, data in results.items():
                        f.write(f"\n{'#'*60}\n")
                        f.write(f"  SOURCE: {data['name']}  ({data['hits']} pages matched)\n")
                        f.write(f"{'#'*60}\n")
                        f.write(data["content"])
                        f.write("\n")
                print(f"  ✅ Combined file saved: {combined_path}")
        else:
            pdf_path = list(results.keys())[0]
            data = results[pdf_path]
            base_dir = os.path.dirname(pdf_path)
            base_name = os.path.splitext(data["name"])[0]
            ranges = ranges_per_pdf[pdf_path]
            label = "_".join(f"{s}-{e}" for s, e in ranges)
            out_path = os.path.join(base_dir, f"{base_name}_filtered_{safe_query}_{mode_tag}_{label}.txt")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(data["content"])
            print(f"\n  ✅ Saved: {out_path}")

    input("\nPress Enter to return to menu...")


# ─────────────────────────────────────────────────────────
# FEATURE 7: PDF COMPRESS / REDUCE SIZE
# ─────────────────────────────────────────────────────────

def feature_pdf_compress():
    print("\n--- PDF Compress / Reduce Size ---")

    pdf_path = ask_pdf_input()
    if not pdf_path:
        input("Press Enter...")
        return

    total_pages = get_pdf_total_pages(pdf_path)
    if not total_pages:
        input("Press Enter...")
        return

    print(f"  PDF has {total_pages} pages.  Size: {get_size_mb(pdf_path):.2f} MB")

    method = questionary.select(
        "Choose reduction method:",
        choices=[
            "1. Remove images completely",
            "2. Compress (choose engine)",
            "3. Both: Remove images + Compress"
        ]
    ).ask()

    engine = None
    if method in ("2. Compress (choose engine)", "3. Both: Remove images + Compress"):
        engine = questionary.select(
            "Choose compression engine:",
            choices=[
                "Ghostscript  (best quality/size ratio)",
                "PyMuPDF / fitz  (fast, good quality)",
                "pikepdf  (lossless structure optimize)"
            ]
        ).ask()

    scope_choice = questionary.select(
        "Apply to:",
        choices=[
            "Full PDF",
            "Specific page ranges"
        ]
    ).ask()

    if scope_choice == "Full PDF":
        ranges = [(1, total_pages)]
        output_mode = "Merge all ranges into one file"
    else:
        print(f"\nPDF has {total_pages} pages.")
        print("Enter ranges (comma or + separated, e.g.  3-43, 654-765):")
        raw = input("> ").strip()
        ranges = parse_ranges(raw, total_pages)
        if not ranges:
            print("[!] No valid ranges entered.")
            input("Press Enter...")
            return
        output_mode = ask_output_mode() if len(ranges) > 1 else "Merge all ranges into one file"

    base_dir = os.path.dirname(pdf_path)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    tmp_dir = os.path.join(base_dir, "__pdf_tmp__")
    os.makedirs(tmp_dir, exist_ok=True)

    def run_engine(src, dst, eng):
        if eng and "Ghostscript" in eng:
            return compress_ghostscript(src, dst)
        elif eng and "fitz" in eng:
            return compress_fitz(src, dst)
        elif eng and "pikepdf" in eng:
            return compress_pikepdf(src, dst)
        return False

    def process_single(src, dst, meth, eng):
        if meth == "1. Remove images completely":
            return remove_images_fitz(src, dst)
        elif meth == "2. Compress (choose engine)":
            return run_engine(src, dst, eng)
        elif meth == "3. Both: Remove images + Compress":
            tmp_no_img = os.path.join(tmp_dir, "step1_no_images.pdf")
            ok = remove_images_fitz(src, tmp_no_img)
            if not ok:
                return False
            return run_engine(tmp_no_img, dst, eng)
        return False

    method_tag = method.split(".")[0].strip()
    engine_tag = ""
    if engine:
        if "Ghostscript" in engine:
            engine_tag = "_gs"
        elif "fitz" in engine:
            engine_tag = "_fitz"
        elif "pikepdf" in engine:
            engine_tag = "_pikepdf"

    is_full = (ranges == [(1, total_pages)])

    if is_full:
        suffix = f"reduced_m{method_tag}{engine_tag}"
        out_path = make_output_path(pdf_path, suffix)
        print(f"\n  Processing full PDF...")
        ok = process_single(pdf_path, out_path, method, engine)
        if ok:
            print_compression_result(pdf_path, out_path)
        else:
            print("  [!] Processing failed.")
    elif output_mode == "Merge all ranges into one file":
        tmp_extracted = os.path.join(tmp_dir, "extracted_ranges.pdf")
        ok = extract_pages_to_pdf(pdf_path, tmp_extracted, ranges)
        if not ok:
            print("  [!] Could not extract pages.")
            input("Press Enter...")
            return
        label = "_".join(f"{s}-{e}" for s, e in ranges)
        out_path = os.path.join(base_dir, f"{base_name}_pages_{label}_reduced_m{method_tag}{engine_tag}.pdf")
        print(f"\n  Processing merged ranges...")
        ok = process_single(tmp_extracted, out_path, method, engine)
        if ok:
            print_compression_result(pdf_path, out_path)
        else:
            print("  [!] Processing failed.")
    else:
        from pypdf import PdfReader, PdfWriter
        reader = PdfReader(pdf_path)
        for idx, (s, e) in enumerate(ranges, 1):
            tmp_range = os.path.join(tmp_dir, f"range_{s}_{e}.pdf")
            writer = PdfWriter()
            for i in range(s - 1, e):
                writer.add_page(reader.pages[i])
            with open(tmp_range, "wb") as f:
                writer.write(f)
            out_path = os.path.join(base_dir, f"{base_name}_pages_{s}-{e}_reduced_m{method_tag}{engine_tag}.pdf")
            print(f"\n  Processing range {idx} ({s}-{e})...")
            ok = process_single(tmp_range, out_path, method, engine)
            if ok:
                print_compression_result(tmp_range, out_path)
            else:
                print(f"  [!] Failed for range {s}-{e}.")

    try:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

    input("\nPress Enter to return to menu...")

# ─────────────────────────────────────────────────────────
# FEATURE 8: TAGS & NAMES MANAGER (COPY / REMOVE)
# ─────────────────────────────────────────────────────────

def feature_tags_manager():
    import shutil # تم استدعاء المكتبة هنا لعدم الحاجة لتعديل بداية الملف
    
    print("\n--- Tags & Names Manager ---")
    
    # المسارات الثابتة بناءً على طلبك
    JSON_PATHS = [
        r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo pic.json",
        r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_A1000 elo tik.json",
        r"C:\Users\Stark\Download\myhome\video_rating_app\utilities\elo_videos_Dib.json"
    ]
    SOURCE_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"
    TARGET_DIR = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\Tags Copy"

    # التأكد من وجود مجلد الهدف، وإذا لم يكن موجوداً نقوم بإنشائه
    os.makedirs(TARGET_DIR, exist_ok=True)

    action = questionary.select(
        "ما الذي تريد فعله؟",
        choices=[
            "1. نسخ الصور/الفيديوهات بناءً على الوسوم (Tags) أو الاسم",
            "2. حذف وسوم معينة بناءً على الملفات الموجودة في مجلد Tags Copy",
            "رجوع"
        ]
    ).ask()

    if action == "رجوع" or not action:
        return

    # اختيار ملفات JSON
    json_choices = [questionary.Choice(os.path.basename(p), value=p) for p in JSON_PATHS]
    json_choices.append(questionary.Choice("اختيار جميع الملفات الثلاثة (All)", value="ALL"))
    
    selected_json = questionary.select(
        "اختر ملف الـ JSON الذي تريد قراءة البيانات منه:",
        choices=json_choices
    ).ask()

    files_to_process = JSON_PATHS if selected_json == "ALL" else [selected_json]
    
    # دالة مساعدة لقراءة ملفات JSON وتجميع البيانات
    def load_json_databases(paths):
        combined_data = {}
        for path in paths:
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        combined_data[path] = data
                except Exception as e:
                    print(f"[!] خطأ في قراءة {os.path.basename(path)}: {e}")
            else:
                print(f"[!] الملف غير موجود: {os.path.basename(path)}")
        return combined_data

    db_data = load_json_databases(files_to_process)
    if not db_data:
        print("لم يتم العثور على أي بيانات صحيحة.")
        input("اضغط Enter للعودة...")
        return

    # ---------------------------------------------------------
    # الخيار 1: البحث والنسخ
    # ---------------------------------------------------------
    if action.startswith("1"):
        search_by = questionary.select(
            "هل تريد التصنيف والبحث بحسب:",
            choices=["الوسوم (Tags)", "الاسم (Name)"]
        ).ask()

        unique_items = set()
        
        # استخراج جميع الوسوم أو الأسماء المتاحة
        for file_path, data in db_data.items():
            for key, val in data.items():
                if search_by == "الوسوم (Tags)":
                    tags_str = val.get("tags", "")
                    if tags_str:
                        # تقسيم الوسوم إذا كانت مفصولة بفاصلة
                        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                        unique_items.update(tags_list)
                else:
                    name_str = val.get("name", "")
                    if name_str:
                        unique_items.add(name_str.strip())

        if not unique_items:
            print(f"\nلا يوجد أي {search_by} مسجل في ملفات الـ JSON المحددة.")
            input("اضغط Enter للعودة...")
            return

        print(f"\n--- قائمة {search_by} المتاحة ---")
        for item in sorted(list(unique_items)):
            print(f"- {item}")
        
        target_value = input(f"\nاكتب الـ {search_by} الذي تريد نسخه من القائمة أعلاه: ").strip()
        
        # البحث عن الأحجام (Sizes) المطابقة لطلب المستخدم
        target_sizes = set()
        for file_path, data in db_data.items():
            for key, val in data.items():
                match = False
                if search_by == "الوسوم (Tags)":
                    tags_list = [t.strip() for t in val.get("tags", "").split(',') if t.strip()]
                    if target_value in tags_list:
                        match = True
                else:
                    if target_value == val.get("name", "").strip():
                        match = True
                
                if match and "file_size" in val:
                    target_sizes.add(val["file_size"])

        if not target_sizes:
            print("لم يتم العثور على ملفات تطابق هذا المدخل.")
            input("اضغط Enter للعودة...")
            return
            
        print(f"\nتم العثور على {len(target_sizes)} ملف (أحجام مطابقة) في قاعدة البيانات. جاري البحث في المجلدات...")

        # مسح جميع الملفات في المجلد الرئيسي والمجلدات الفرعية
        found_count = 0
        for root, dirs, files in os.walk(SOURCE_DIR):
            for filename in files:
                full_path = os.path.join(root, filename)
                try:
                    size = os.path.getsize(full_path)
                    if size in target_sizes:
                        dest_path = os.path.join(TARGET_DIR, filename)
                        # نسخ الملف إذا لم يكن موجوداً مسبقاً
                        if not os.path.exists(dest_path):
                            shutil.copy2(full_path, dest_path)
                            print(f"✅ تم نسخ: {filename}")
                            found_count += 1
                        else:
                            print(f"⏭️ تم التخطي (موجود مسبقاً): {filename}")
                except Exception as e:
                    pass
        
        print(f"\nتم الانتهاء! تم نسخ {found_count} ملف إلى المجلد: Tags Copy")
        input("اضغط Enter للعودة...")

    # ---------------------------------------------------------
    # الخيار 2: الحذف العكسي للوسوم
    # ---------------------------------------------------------
    elif action.startswith("2"):
        if not os.path.exists(TARGET_DIR):
            print("مجلد Tags Copy غير موجود.")
            input("اضغط Enter للعودة...")
            return

        # 1. جمع أحجام الملفات الموجودة في مجلد Tags Copy
        print("جاري فحص الملفات في مجلد Tags Copy...")
        tags_copy_sizes = set()
        for filename in os.listdir(TARGET_DIR):
            full_path = os.path.join(TARGET_DIR, filename)
            if os.path.isfile(full_path):
                tags_copy_sizes.add(os.path.getsize(full_path))

        if not tags_copy_sizes:
            print("مجلد Tags Copy فارغ. لا يوجد شيء لمطابقته.")
            input("اضغط Enter للعودة...")
            return

        # 2. مطابقة الأحجام مع JSON واستخراج الوسوم الموجودة فيها فقط
        matched_tags = set()
        for file_path, data in db_data.items():
            for key, val in data.items():
                if val.get("file_size") in tags_copy_sizes:
                    tags_str = val.get("tags", "")
                    if tags_str:
                        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                        matched_tags.update(tags_list)

        if not matched_tags:
            print("\nالملفات الموجودة في المجلد ليس لديها أي وسوم مسجلة في ملف الـ JSON.")
            input("اضغط Enter للعودة...")
            return

        print("\n--- الوسوم (Tags) الموجودة حالياً في هذه الملفات ---")
        for t in sorted(list(matched_tags)):
            print(f"- {t}")

        tag_to_remove = input("\nاكتب الوسم الذي تريد حذفه من هذه الملفات: ").strip()

        if tag_to_remove not in matched_tags:
            print("الوسم الذي أدخلته غير موجود في القائمة.")
            input("اضغط Enter للعودة...")
            return

        # 3. تحديث البيانات وحذف الوسم
        updated_files_count = 0
        for file_path, data in db_data.items():
            file_modified = False
            for key, val in data.items():
                if val.get("file_size") in tags_copy_sizes:
                    tags_str = val.get("tags", "")
                    if tags_str:
                        tags_list = [t.strip() for t in tags_str.split(',') if t.strip()]
                        if tag_to_remove in tags_list:
                            tags_list.remove(tag_to_remove)
                            # إعادة دمج الوسوم المتبقية بفاصلة
                            val["tags"] = ", ".join(tags_list)
                            file_modified = True
                            updated_files_count += 1
            
            # حفظ التعديلات إذا تم تغيير أي شيء في هذا الملف
            if file_modified:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump(data, f, indent=4, ensure_ascii=False)
                    print(f"💾 تم حفظ التعديلات في: {os.path.basename(file_path)}")
                except Exception as e:
                    print(f"❌ خطأ أثناء الحفظ في {os.path.basename(file_path)}: {e}")

        print(f"\nتم الانتهاء! تمت إزالة الوسم '{tag_to_remove}' من {updated_files_count} صورة/فيديو بنجاح.")
        input("اضغط Enter للعودة...")
        
        
# ─────────────────────────────────────────────────────────
# FEATURE 9: SMART VIDEO SCREENSHOTS
# ─────────────────────────────────────────────────────────

def get_sharpness(image):
    import cv2
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Laplacian(gray, cv2.CV_64F).var()

def save_image_unicode(image, path):
    import cv2
    import numpy as np
    is_success, im_buf_arr = cv2.imencode(".jpg", image)
    if is_success:
        im_buf_arr.tofile(path)

def extract_smart_screenshots(video_path, output_dir, num_screenshots):
    import cv2
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"  [!] Could not open video: {os.path.basename(video_path)}")
        return

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    if total_frames <= 0 or fps <= 0:
        print(f"  [!] Invalid video data: {os.path.basename(video_path)}")
        cap.release()
        return

    safe_start = int(total_frames * 0.05)
    safe_end = int(total_frames * 0.95)
    safe_duration = safe_end - safe_start

    if safe_duration <= 0 or num_screenshots <= 0:
        print(f"  [!] Video is too short to extract {num_screenshots} screenshots.")
        cap.release()
        return

    interval = safe_duration // num_screenshots

    target_frames =[]
    for i in range(num_screenshots):
        target_frame = safe_start + (i * interval) + (interval // 2)
        target_frames.append(target_frame)

    print(f"  -> Processing: {os.path.basename(video_path)} ...", end=" ", flush=True)

    saved_count = 0
    for i, center_frame in enumerate(target_frames):
        best_frame_img = None
        highest_sharpness = -1.0
        sample_offsets =[-10, -5, 0, 5, 10]
        
        for offset in sample_offsets:
            check_frame = center_frame + offset
            if check_frame < 0 or check_frame >= total_frames:
                continue
                
            cap.set(cv2.CAP_PROP_POS_FRAMES, check_frame)
            ret, frame = cap.read()
            
            if ret:
                sharpness = get_sharpness(frame)
                if sharpness > highest_sharpness:
                    highest_sharpness = sharpness
                    best_frame_img = frame

        if best_frame_img is not None:
            screenshot_name = f"screenshot_{i+1:02d}.jpg"
            screenshot_path = os.path.join(output_dir, screenshot_name)
            save_image_unicode(best_frame_img, screenshot_path)
            saved_count += 1

    cap.release()
    print(f"Done! ({saved_count} saved)")

def feature_smart_screenshots():
    print("\n--- Smart Video Screenshots ---")
    
    try:
        import cv2
        import numpy as np
    except ImportError:
        print("[!] Missing required libraries.")
        print("    Please run: pip install opencv-python numpy")
        input("\nPress Enter to return to menu...")
        return

    default_dir = r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\Tags Copy"
    
    print(f"\nEnter the folder path containing the videos")
    print(f"(Press Enter to use default: {default_dir})")
    target_dir = input("> ").strip().strip('"').strip("'")
    
    if not target_dir:
        target_dir = default_dir

    if not os.path.isdir(target_dir):
        print(f"\n[!] Error: The directory '{target_dir}' does not exist.")
        input("Press Enter to return to menu...")
        return

    print("\nEnter the number of screenshots per video")
    print("(Press Enter to use default: 10)")
    raw_count = input("> ").strip()
    num_screenshots = int(raw_count) if raw_count.isdigit() else 10

    video_extensions = ('.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv')
    
    video_files =[]
    for file in os.listdir(target_dir):
        if file.lower().endswith(video_extensions):
            video_files.append(file)

    if not video_files:
        print("\n[!] No video files found in the specified directory.")
        input("Press Enter to return to menu...")
        return

    print(f"\nFound {len(video_files)} video(s). Starting extraction...\n")

    for video_file in video_files:
        video_path = os.path.join(target_dir, video_file)
        video_name_without_ext = os.path.splitext(video_file)[0]
        
        output_folder = os.path.join(target_dir, video_name_without_ext)
        os.makedirs(output_folder, exist_ok=True)
        
        extract_smart_screenshots(video_path, output_folder, num_screenshots)

    print("\n✅ All screenshots extracted successfully!")
    input("Press Enter to return to menu...")
# ─────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────

def main():
    clear_screen()
    print("Welcome to the Multi-Tool Script.")

    try:
        downloads_path = str(Path.home() / "Downloads")
    except Exception:
        downloads_path = "Could not find Downloads folder"

    default_paths =[
        ("Default Downloads Folder", downloads_path),
        ("ELO TIK Main", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"),
    ]

    path_choices =[
        questionary.Choice(title=f"{name}: {path}", value=path)
        for name, path in default_paths
    ]
    path_choices.append(questionary.Separator())
    path_choices.append(questionary.Choice(title="Enter a custom path...", value="custom"))

    chosen_path = questionary.select(
        "Please select a working directory (Main Menu Root):",
        choices=path_choices
    ).ask()

    if chosen_path == "custom":
        target_dir = input("Directory: ").strip('"')
    else:
        target_dir = chosen_path

    if not target_dir or not os.path.isdir(target_dir):
        print(f"Invalid dir: {target_dir}")
        sys.exit()

    while True:
        clear_screen()
        print(f"Main Working Directory: {target_dir}")

        answer = questionary.select(
            "Select an action:",
            choices=[
                "1. Extract File Sizes",
                "2. Create Competition (JSON)",
                "3. Remove Duplicates",
                "4. Interactive Renamer (Numbering) 🆕",
                questionary.Separator("─── PDF Tools ───"),
                "5. PDF Split (cut pages / ranges)",
                "6. PDF to Text",
                "7. PDF Compress / Reduce Size",
                questionary.Separator("─── Database & Media ───"),
                "8. Tags & Names Manager (Copy / Remove) 🆕",
                "9. Smart Video Screenshots 🆕",
                "Exit"
            ]
        ).ask()

        if answer == "1. Extract File Sizes":
            feature_extract_sizes(target_dir)
        elif answer == "2. Create Competition (JSON)":
            feature_create_competition()
        elif answer == "3. Remove Duplicates":
            feature_remove_duplicates(target_dir)
        elif answer == "4. Interactive Renamer (Numbering) 🆕":
            feature_interactive_renamer()
        elif answer == "5. PDF Split (cut pages / ranges)":
            feature_pdf_split()
        elif answer == "6. PDF to Text":
            feature_pdf_to_text()
        elif answer == "7. PDF Compress / Reduce Size":
            feature_pdf_compress()
        elif answer == "8. Tags & Names Manager (Copy / Remove) 🆕":
            feature_tags_manager()
        elif answer == "9. Smart Video Screenshots 🆕":
            feature_smart_screenshots()
        elif answer == "Exit":
            print("Goodbye!")
            sys.exit()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()