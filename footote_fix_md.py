import os
import re
import shutil

# --- Configuration ---
# 1. Regex to find references in text like [[1]](#footnote-0)
# Flexible with spaces [[ 1 ]] or [[1]]
REF_REGEX = r"\[\[?\s*(\d+)\s*\]?\]\(#footnote-?\d+\)"

# 2. SMART Regex for definitions: 
# It MUST start with a number and MUST contain the return arrow [↑]
# This prevents it from accidentally catching your medical lists (e.g., 4. Treatment...)
DEF_REGEX = r"^(\d+)\.\s+(.*?)\[↑\]\(#footnote-ref-\d+\).*$"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def backup_file(file_path):
    """Creates a .bak copy of the file for safety."""
    shutil.copy2(file_path, file_path + ".bak")

def extract_definitions_from_text(text):
    """
    Separates the footnotes from the main text.
    Only extracts lines that look like Google Drive footnotes (contain the [↑] arrow).
    """
    definitions = {}
    clean_lines = []
    
    lines = text.split('\n')
    for line in lines:
        stripped = line.strip()
        match = re.match(DEF_REGEX, stripped)
        
        if match:
            fn_id = match.group(1)
            # Remove the return arrow from the final clean text
            fn_content = match.group(2).strip()
            definitions[fn_id] = fn_content
        else:
            # Keep the line in the body, but ignore the specific Google Drive header
            if "### f notes" not in line.lower():
                clean_lines.append(line)
    
    return definitions, "\n".join(clean_lines)

def fix_references_in_text(text):
    """Converts [[1]](#...) to [^1] and returns set of IDs found."""
    used_ids = set()
    def replace_func(match):
        fn_id = match.group(1)
        used_ids.add(fn_id)
        return f"[^{fn_id}]"

    new_text = re.sub(REF_REGEX, replace_func, text)
    return new_text, used_ids

def analyze_discrepancy(def_ids, ref_ids):
    """Prints a detailed report of orphans and broken links."""
    def_set = set(def_ids)
    ref_set = set(ref_ids)
    
    print("\n" + "="*30)
    print("      DIAGNOSTIC REPORT")
    print("="*30)
    print(f"Definitions Found:     {len(def_set)} -> {sorted(list(def_set), key=int)}")
    print(f"References Found:      {len(ref_set)} -> {sorted(list(ref_set), key=int)}")
    
    orphans = def_set - ref_set
    broken = ref_set - def_set
    
    if orphans:
        print(f"\n[!] Orphans (Definitions with no Reference): {sorted(list(orphans), key=int)}")
    if broken:
        print(f"\n[!] Broken (References with no Definition):   {sorted(list(broken), key=int)}")
    
    if not orphans and not broken and def_set:
        print("\n[+] Perfect Match! All links are healthy.")

def process_single_file_mode(file_path):
    print(f"\n>>> Mode: Single File - {os.path.basename(file_path)}")
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # 1. Extraction (Smart)
    definitions, body_text = extract_definitions_from_text(content)
    
    # 2. Conversion
    fixed_body, used_ids = fix_references_in_text(body_text)
    
    # 3. Report
    analyze_discrepancy(definitions.keys(), used_ids)
    
    # 4. Reconstruction
    final_content = fixed_body.rstrip() + "\n\n"
    for uid in sorted(used_ids, key=int):
        if uid in definitions:
            final_content += f"[^{uid}]: {definitions[uid]}\n"
        else:
            final_content += f"[^{uid}]: (Missing Definition)\n"

    confirm = input("\nApply changes? (y/n): ").strip().lower()
    if confirm == 'y':
        backup_file(file_path)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
        print("Done! Changes saved and backup created.")
    else:
        print("Operation cancelled.")

def process_folder_mode(folder_path):
    print(f"\n>>> Mode: Folder - {folder_path}")
    
    md_files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
    if not md_files:
        print("No .md files found.")
        return

    global_definitions = {}
    files_data = {} 
    
    # Track ALL references found across ALL files to build the report
    all_referenced_ids = set()

    print("Step 1: Gathering all definitions from all files...")
    for filename in md_files:
        path = os.path.join(folder_path, filename)
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        defs, cleaned_text = extract_definitions_from_text(content)
        global_definitions.update(defs)
        files_data[filename] = cleaned_text

    print(f"Done. Collected {len(global_definitions)} total unique definitions.")
    
    files_to_update = {}
    
    # Step 2: Prepare updates and collect stats
    for filename, text in files_data.items():
        fixed_text, used_ids = fix_references_in_text(text)
        
        # Add found IDs to our global report set
        all_referenced_ids.update(used_ids)
        
        if used_ids:
            fixed_text = fixed_text.rstrip() + "\n\n"
            for uid in sorted(used_ids, key=int):
                if uid in global_definitions:
                    fixed_text += f"[^{uid}]: {global_definitions[uid]}\n"
                else:
                    fixed_text += f"[^{uid}]: (Missing Global Definition)\n"
            files_to_update[filename] = fixed_text

    # --- NEW: Call the report function for the whole folder ---
    analyze_discrepancy(global_definitions.keys(), all_referenced_ids)
    # ----------------------------------------------------------

    print(f"\nStep 2: Analysis complete. {len(files_to_update)} files need updating.")
    
    confirm = input("\nApply changes to all these files? (y/n): ").strip().lower()
    if confirm == 'y':
        for filename, new_content in files_to_update.items():
            path = os.path.join(folder_path, filename)
            backup_file(path)
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
        print(f"Successfully updated {len(files_to_update)} files.")
    else:
        print("Operation cancelled.")

def main():
    clear_screen()
    print("="*50)
    print("   OBSIDIAN FOOTNOTE FIXER v3.1 (With Folder Report)")
    print("="*50)
    
    path = input("Enter File or Folder Path: ").strip().strip('"')
    
    if os.path.exists(path):
        if os.path.isfile(path):
            process_single_file_mode(path)
        elif os.path.isdir(path):
            process_folder_mode(path)
    else:
        print("Invalid path. Please try again.")

if __name__ == "__main__":
    main()