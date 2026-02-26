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


def _process_single_pdf_to_text(pdf_path, ranges, use_filter,
                                 filter_pattern, raw_query,
                                 extract_style, words_around):
    try:
        from pypdf import PdfReader
    except ImportError:
        return None, 0

    reader = PdfReader(pdf_path)

    if not use_filter:
        parts = []
        for (s, e) in ranges:
            parts.append(f"\n{'='*60}\n  Pages {s} – {e}\n{'='*60}\n")
            for i in range(s - 1, e):
                page_text = reader.pages[i].extract_text() or ""
                parts.append(f"\n--- Page {i+1} ---\n{page_text}")
        return "".join(parts), 0
    else:
        parts = []
        total_hits = 0
        for (s, e) in ranges:
            for i in range(s - 1, e):
                page_num = i + 1
                page_text = reader.pages[i].extract_text() or ""
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
        print(f"  ⏳ {pdf_name} ...", end=" ", flush=True)
        content, hit_count = _process_single_pdf_to_text(
            pdf_path, ranges, use_filter,
            filter_pattern, raw_query,
            extract_style, words_around
        )
        results[pdf_path] = {"content": content, "hits": hit_count, "name": pdf_name}
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
# MAIN LOOP
# ─────────────────────────────────────────────────────────

def main():
    clear_screen()
    print("Welcome to the Multi-Tool Script.")

    try:
        downloads_path = str(Path.home() / "Downloads")
    except Exception:
        downloads_path = "Could not find Downloads folder"

    default_paths = [
        ("Default Downloads Folder", downloads_path),
        ("ELO TIK Main", r"C:\Users\Stark\Download\myhome\video_rating_app\NS\TikTok\ELO TIK"),
    ]

    path_choices = [
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
        elif answer == "Exit":
            print("Goodbye!")
            sys.exit()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nExiting...")
        sys.exit()