#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import subprocess
import sys
import re
from pathlib import Path

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def get_audio_files():
    """Scan for audio files in the current directory."""
    audio_extensions = ['.mp3', '.opus', '.wav', '.flac', '.aac', '.m4a', '.ogg', '.wma']
    audio_files = []
    
    for file in os.listdir('.'):
        if any(file.lower().endswith(ext) for ext in audio_extensions):
            audio_files.append(file)
    
    return sorted(audio_files)

def show_menu(items, title):
    """Display a selection menu using arrow keys."""
    if not items:
        print("No audio files found in the directory!")
        return None
    
    selected = 0
    
    while True:
        clear_screen()
        print(f"=== {title} ===\n")
        
        for i, item in enumerate(items):
            if i == selected:
                print(f"→ {item}")
            else:
                print(f"  {item}")
        
        print(f"\nUse Arrow keys to navigate, Enter to select")
        
        try:
            if os.name == 'nt':  # Windows
                import msvcrt
                key = msvcrt.getch()
                if key == b'\xe0':
                    key = msvcrt.getch()
                    if key == b'H':  # Up
                        selected = (selected - 1) % len(items)
                    elif key == b'P':  # Down
                        selected = (selected + 1) % len(items)
                elif key == b'\r':  # Enter
                    return items[selected]
            else:  # Linux/Mac
                import tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    key = sys.stdin.read(1)
                    if key == '\x1b':
                        key += sys.stdin.read(2)
                        if key == '\x1b[A':  # Up
                            selected = (selected - 1) % len(items)
                        elif key == '\x1b[B':  # Down
                            selected = (selected + 1) % len(items)
                    elif key == '\n' or key == '\r':  # Enter
                        return items[selected]
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except KeyboardInterrupt:
            return None

# START: MODIFIED SECTION (New Multi-Select Menu)
def multiselect_menu(items, title):
    """Allow selecting multiple files using Spacebar."""
    if not items:
        print("No files found!")
        return []
    
    selected_indices = set()
    current_pos = 0
    
    while True:
        clear_screen()
        print(f"=== {title} ===\n")
        print("Instructions: [Space] to Select/Deselect | [Enter] to Confirm | [Esc/Ctrl+C] to Cancel\n")
        
        for i, item in enumerate(items):
            cursor = "→" if i == current_pos else " "
            checkbox = "[x]" if i in selected_indices else "[ ]"
            print(f"{cursor} {checkbox} {item}")
        
        print(f"\nSelected: {len(selected_indices)} files")
        
        try:
            if os.name == 'nt': # Windows
                import msvcrt
                key = msvcrt.getch()
                if key == b'\xe0':
                    key = msvcrt.getch()
                    if key == b'H': # Up
                        current_pos = (current_pos - 1) % len(items)
                    elif key == b'P': # Down
                        current_pos = (current_pos + 1) % len(items)
                elif key == b' ': # Spacebar
                    if current_pos in selected_indices:
                        selected_indices.remove(current_pos)
                    else:
                        selected_indices.add(current_pos)
                elif key == b'\r': # Enter
                    return [items[i] for i in sorted(selected_indices)]
                elif key == b'\x1b': # Esc
                    return []
            else: # Linux/Mac
                import tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    key = sys.stdin.read(1)
                    if key == '\x1b':
                        next_char = sys.stdin.read(1) if sys.stdin in select.select([sys.stdin], [], [], 0)[0] else None
                        if next_char is None: # Just Esc
                            return []
                        key += next_char + sys.stdin.read(1)
                        if key == '\x1b[A': current_pos = (current_pos - 1) % len(items)
                        elif key == '\x1b[B': current_pos = (current_pos + 1) % len(items)
                    elif key == ' ':
                        if current_pos in selected_indices: selected_indices.remove(current_pos)
                        else: selected_indices.add(current_pos)
                    elif key == '\n' or key == '\r':
                        return [items[i] for i in sorted(selected_indices)]
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except KeyboardInterrupt:
            return []
# END: MODIFIED SECTION

def yes_no_menu(question, extra_content=""):
    """Yes/No Menu that can display extra info (like reports) without clearing it."""
    options = ["Yes", "No"]
    selected = 0
    
    while True:
        clear_screen()
        if extra_content:
            print(extra_content)
            print("-" * 40)
            
        print(f"{question}\n")
        
        for i, option in enumerate(options):
            if i == selected:
                print(f"→ {option}")
            else:
                print(f"  {option}")
        
        print(f"\nUse Arrow keys to navigate, Enter to select")
        
        try:
            if os.name == 'nt':
                import msvcrt
                key = msvcrt.getch()
                if key == b'\xe0':
                    key = msvcrt.getch()
                    if key == b'H':
                        selected = (selected - 1) % len(options)
                    elif key == b'P':
                        selected = (selected + 1) % len(options)
                elif key == b'\r':
                    return selected == 0
            else:
                import tty, termios
                fd = sys.stdin.fileno()
                old_settings = termios.tcgetattr(fd)
                try:
                    tty.setcbreak(fd)
                    key = sys.stdin.read(1)
                    if key == '\x1b':
                        key += sys.stdin.read(2)
                        if key == '\x1b[A':
                            selected = (selected - 1) % len(options)
                        elif key == '\x1b[B':
                            selected = (selected + 1) % len(options)
                    elif key == '\n' or key == '\r':
                        return selected == 0
                finally:
                    termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        except KeyboardInterrupt:
            return False

def compress_audio(input_file):
    """Compress audio file"""
    file_path = Path(input_file)
    output_file = f"{file_path.stem}_small.opus"
    
    cmd = [
        'ffmpeg', '-i', input_file,
        '-c:a', 'libopus',
        '-b:a', '32k',
        output_file
    ]
    
    print(f"Compressing file: {input_file}")
    print(f"Output: {output_file}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Compression successful! New file: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error compressing file: {e}")
    except FileNotFoundError:
        print("Error: ffmpeg is not installed")

def cut_audio(input_file):
    """Cut a section of the audio"""
    print("\nEnter cut times in format: HH:MM:SS,HH:MM:SS")
    print("Example: 00:55:28,00:57:00")
    
    time_input = input("Times: ").strip()
    
    try:
        start_time, end_time = time_input.split(',')
        start_time = start_time.strip()
        end_time = end_time.strip()
    except ValueError:
        print("Error: Invalid time format!")
        return
    
    file_path = Path(input_file)
    output_file = f"{file_path.stem}_cut{file_path.suffix}"
    
    cmd = [
        'ffmpeg', '-i', input_file,
        '-ss', start_time,
        '-to', end_time,
        output_file
    ]
    
    print(f"Cutting file from {start_time} to {end_time}")
    
    try:
        subprocess.run(cmd, check=True)
        print(f"Cut successful! New file: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error cutting file: {e}")

def merge_audio(first_file):
    """Merge two audio files"""
    all_files = get_audio_files()
    other_files = [f for f in all_files if f != first_file]
    
    if not other_files:
        print("No other audio files to merge with!")
        return

    second_file = show_menu(other_files, f"Select file to merge with '{first_file}'")
    if not second_file:
        return

    print(f"\nMerging '{first_file}' + '{second_file}'...")
    
    output_file = f"merged_{Path(first_file).stem}_{Path(second_file).stem}.mp3"
    
    cmd = [
        'ffmpeg',
        '-i', first_file,
        '-i', second_file,
        '-filter_complex', '[0:a][1:a]concat=n=2:v=0:a=1[out]',
        '-map', '[out]',
        output_file
    ]

    try:
        subprocess.run(cmd, check=True)
        print(f"Merge successful! Created: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error merging files: {e}")

# START: MODIFIED SECTION (Added 'auto_confirm' for Batch Mode)
def remove_silence(input_file, auto_confirm=False):
    """Detect and remove silence safely. auto_confirm skips the menu."""
    print(f"\nAnalyzing '{input_file}'...")
    print("Detecting silence > 3 seconds...")
    
    detect_cmd = [
        'ffmpeg', '-i', input_file,
        '-af', 'silencedetect=noise=-40dB:d=3',
        '-f', 'null', '-'
    ]
    
    try:
        result = subprocess.run(detect_cmd, stderr=subprocess.PIPE, text=True)
        output = result.stderr
    except FileNotFoundError:
        print("Error: ffmpeg not found.")
        return

    silence_starts = re.findall(r'silence_start: (\d+(\.\d+)?)', output)
    silence_ends = re.findall(r'silence_end: (\d+(\.\d+)?)', output)
    
    if not silence_starts:
        print("No silence longer than 3 seconds detected.")
        return

    report_text = f"\n--- Silence Analysis for: {input_file} ---\n"
    for i, start in enumerate(silence_starts):
        s_time = float(start[0])
        if i < len(silence_ends):
            e_time = float(silence_ends[i][0])
            duration = e_time - s_time
            report_text += f"Start: {s_time:.2f}s | End: {e_time:.2f}s | Duration: {duration:.2f}s\n"
        else:
            report_text += f"Start: {s_time:.2f}s | End: (End of file)\n"
    
    report_text += "\nNote: We will leave a 1-second buffer."

    # Only ask for confirmation if NOT in auto (batch) mode
    if not auto_confirm:
        if not yes_no_menu("Do you want to DELETE these silent sections?", extra_content=report_text):
            print("Operation cancelled.")
            return
    else:
        print(report_text)
        print("\n[Batch Mode] Proceeding with deletion automatically...")

    file_path = Path(input_file)
    output_file = f"{file_path.stem}_nosilence{file_path.suffix}"
    
    remove_cmd = [
        'ffmpeg', '-i', input_file,
        '-af', 'silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-40dB',
        output_file
    ]
    
    print(f"\nRemoving silence...")
    try:
        subprocess.run(remove_cmd, check=True)
        print(f"Done! Saved as: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error removing silence: {e}")

def batch_processor():
    """Handle batch operations for multiple files."""
    audio_files = get_audio_files()
    if not audio_files:
        print("No audio files found.")
        input("Press Enter to continue...")
        return

    selected_files = multiselect_menu(audio_files, "Batch Processing - Select Files")
    if not selected_files:
        return

    actions = ["Compress All (Small Size)", "Remove Silence All"]
    choice = show_menu(actions, f"Selected {len(selected_files)} files. Choose Action:")

    if not choice:
        return

    print(f"\nStarting batch processing for {len(selected_files)} files...")
    
    for i, file in enumerate(selected_files, 1):
        print(f"\n>>> Processing File {i}/{len(selected_files)}: {file}")
        
        if choice == "Compress All (Small Size)":
            compress_audio(file)
        elif choice == "Remove Silence All":
            # We pass auto_confirm=True so it doesn't ask Yes/No for every file
            remove_silence(file, auto_confirm=True)
    
    print("\nBatch processing complete!")
    input("Press Enter to return to menu...")
# END: MODIFIED SECTION

def main():
    while True:
        clear_screen()
        print("=== Audio File Wizard ===\n")
        
        audio_files = get_audio_files()
        
        # START: MODIFIED SECTION (Added Batch Option to Main Menu)
        menu_items = ["Batch Processing (Multiple Files)"] 
        if audio_files:
            menu_items.extend(audio_files)
        menu_items.append("Exit Program")
        
        selected = show_menu(menu_items, "Select Mode or File")
        
        if selected == "Exit Program" or selected is None:
            print("Goodbye!")
            break
        
        if selected == "Batch Processing (Multiple Files)":
            batch_processor()
            continue
        # END: MODIFIED SECTION
        
        # Single File Mode Logic
        selected_file = selected
        print(f"\nSelected: {selected_file}")
        
        while True:
            actions = [
                "Compress (Reduce Size)",
                "Cut (Trim segment)",
                "Merge (Add another file)",
                "Remove Silence (Auto-clean)",
                "Select Different File",
                "Exit Program"
            ]
            
            action_choice = show_menu(actions, f"Action for: {selected_file}")
            
            if action_choice == "Compress (Reduce Size)":
                compress_audio(selected_file)
                input("\nPress Enter to continue...")
            
            elif action_choice == "Cut (Trim segment)":
                cut_audio(selected_file)
                input("\nPress Enter to continue...")
            
            elif action_choice == "Merge (Add another file)":
                merge_audio(selected_file)
                input("\nPress Enter to continue...")
            
            elif action_choice == "Remove Silence (Auto-clean)":
                remove_silence(selected_file)
                input("\nPress Enter to continue...")
            
            elif action_choice == "Select Different File":
                break
            
            elif action_choice == "Exit Program" or action_choice is None:
                print("Goodbye!")
                return

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user")