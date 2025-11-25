# START: FULL SCRIPT
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

# START: MODIFIED SECTION (Improved UI to keep report visible)
def yes_no_menu(question, extra_content=""):
    """Yes/No Menu that can display extra info (like reports) without clearing it."""
    options = ["Yes", "No"]
    selected = 0
    
    while True:
        clear_screen()
        # If there is extra content (like silence report), print it first
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
# END: MODIFIED SECTION

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

# START: MODIFIED SECTION (Advanced Silence Removal Logic)
def remove_silence(input_file):
    """Detect and remove silence safely with buffering"""
    print(f"\nAnalyzing '{input_file}'...")
    # Increased duration to 3 seconds (d=3)
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

    # Build the report string to display in the menu
    report_text = f"\n--- Silence Analysis for: {input_file} ---\n"
    for i, start in enumerate(silence_starts):
        s_time = float(start[0])
        if i < len(silence_ends):
            e_time = float(silence_ends[i][0])
            duration = e_time - s_time
            report_text += f"Start: {s_time:.2f}s | End: {e_time:.2f}s | Duration: {duration:.2f}s\n"
        else:
            report_text += f"Start: {s_time:.2f}s | End: (End of file)\n"
    
    report_text += "\nNote: We will leave a 1-second buffer to avoid chopping speech."

    # Pass report_text to the menu so it stays visible
    if not yes_no_menu("Do you want to DELETE these silent sections?", extra_content=report_text):
        print("Operation cancelled.")
        return

    file_path = Path(input_file)
    output_file = f"{file_path.stem}_nosilence{file_path.suffix}"
    
    # stop_duration=1 ensures we leave 1 second of silence
    remove_cmd = [
        'ffmpeg', '-i', input_file,
        '-af', 'silenceremove=stop_periods=-1:stop_duration=1:stop_threshold=-40dB',
        output_file
    ]
    
    print(f"\nRemoving silence (keeping 1s buffer)...")
    try:
        subprocess.run(remove_cmd, check=True)
        print(f"Done! Saved as: {output_file}")
    except subprocess.CalledProcessError as e:
        print(f"Error removing silence: {e}")
# END: MODIFIED SECTION

def main():
    # START: MODIFIED SECTION (Main Loop for Flexibility)
    while True:
        clear_screen()
        print("=== Audio File Wizard ===\n")
        
        audio_files = get_audio_files()
        
        if not audio_files:
            print("No audio files found in the current folder!")
            return
        
        # Add option to quit at file selection
        menu_items = audio_files + ["Exit Program"]
        selected = show_menu(menu_items, "Select an Audio File")
        
        if not selected or selected == "Exit Program":
            print("Goodbye!")
            break
        
        selected_file = selected
        print(f"\nSelected: {selected_file}")
        
        # Inner loop: Perform multiple actions on the selected file
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
                break  # Breaks inner loop, goes back to file selection
            
            elif action_choice == "Exit Program" or action_choice is None:
                print("Goodbye!")
                return # Exits the whole program
    # END: MODIFIED SECTION

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nCancelled by user")
# END: FULL SCRIPT