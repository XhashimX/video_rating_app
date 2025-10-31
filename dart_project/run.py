# START: FULL SCRIPT
import os
import sys
import torch
import questionary
from transformers import AutoTokenizer, AutoModelForCausalLM

# --- CONFIGURATION ---
# The script will use the local model you've already downloaded.
# Ensure this path is correct relative to where you run the script.
MODEL_PATH = "./dart-v2-moe-sft-local"

# --- HELPER FUNCTIONS ---

def clear_screen():
    """Clears the terminal screen for a cleaner UI."""
    os.system('cls' if os.name == 'nt' else 'clear')

def load_model_and_tokenizer(model_path):
    """Loads the model and tokenizer from the specified local path."""
    print("Loading model and tokenizer...")
    print(f"Path: {os.path.abspath(model_path)}")
    
    try:
        # Load the tokenizer responsible for converting text to numbers
        tokenizer = AutoTokenizer.from_pretrained(model_path)
        
        # Load the model itself
        # Using dtype=torch.bfloat16 to save memory and for performance
        model = AutoModelForCausalLM.from_pretrained(model_path, dtype=torch.bfloat16)

        print("✅ Model and tokenizer loaded successfully.\n")
        return model, tokenizer
    except OSError:
        print("❌ ERROR: Model files not found.")
        print(f"Please make sure the model is downloaded and located in the '{model_path}' directory.")
        sys.exit(1) # Exit the script if the model cannot be loaded
    except Exception as e:
        print(f"❌ An unexpected error occurred during model loading: {e}")
        sys.exit(1)

def get_user_prompt_interactively():
    """
    Guides the user through a series of questions to build the prompt string.
    Returns the fully formatted prompt string or None if the user cancels.
    """
    print("--- Prompt Builder ---")
    print("Please answer the following questions to create your prompt. Press Ctrl+C to cancel.")

    try:
        # 1. Copyright Tags
        copyright_tags = questionary.text(
            "Enter copyright tags (e.g., vocaloid, genshin impact):"
        ).ask()
        if copyright_tags is None: return None

        # 2. Character Tags
        character_tags = questionary.text(
            "Enter character tags (e.g., hatsune miku, ganyu):"
        ).ask()
        if character_tags is None: return None

        # 3. Rating
        rating = questionary.select(
            "Select rating:",
            choices=['general', 'sfw', 'sensitive', 'nsfw', 'questionable', 'explicit'],
            default='general'
        ).ask()
        if rating is None: return None

        # 4. Aspect Ratio
        aspect_ratio = questionary.select(
            "Select aspect ratio:",
            choices=['tall', 'square', 'wide', 'ultra_tall', 'ultra_wide'],
            default='tall'
        ).ask()
        if aspect_ratio is None: return None

        # 5. Length
        length = questionary.select(
            "Select desired prompt length:",
            choices=['long', 'medium', 'short', 'very_long', 'very_short'],
            default='long'
        ).ask()
        if length is None: return None
        
        # 6. General Tags (the main prompt)
        general_tags = questionary.text(
            "Enter your base general tags (e.g., 1girl, cat ears, smile):"
        ).ask()
        if general_tags is None: return None

        # 7. Identity Preservation
        identity = questionary.select(
            "Select identity preservation strictness:",
            choices=[
                'none', # Most creative
                'lax',  # Tries to keep identity
                'strict'# Strictly keeps identity
            ],
            default='none'
        ).ask()
        if identity is None: return None

        # Assemble the final prompt string based on the official format
        prompt = (
            f"<|bos|>"
            f"<copyright>{copyright_tags.strip()}</copyright>"
            f"<character>{character_tags.strip()}</character>"
            f"<|rating:{rating}|><|aspect_ratio:{aspect_ratio}|><|length:{length}|>"
            f"<general>{general_tags.strip()}<|identity:{identity}|><|input_end|>"
        )
        return prompt

    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully
        return None

# --- MAIN EXECUTION ---

def main():
    """Main function to run the interactive prompt generator."""
    clear_screen()
    print("--- DART v2 Interactive Prompt Generator ---")
    
    model, tokenizer = load_model_and_tokenizer(MODEL_PATH)
    
    while True:
        # Get the complete prompt from the user via the interactive UI
        prompt = get_user_prompt_interactively()

        if prompt is None:
            print("\nPrompt generation cancelled.")
            break

        clear_screen()
        print("--- Generating Tags ---")
        print(f"Constructed Prompt:\n{prompt}\n")
        
        # Convert the prompt text into numbers (tokens) the model understands
        inputs = tokenizer(prompt, return_tensors="pt").input_ids

        # Generate the tags
        # `torch.no_grad()` is a performance optimization
        with torch.no_grad():
            outputs = model.generate(
                inputs,
                do_sample=True,
                temperature=1.0,
                top_p=1.0,
                top_k=100,
                max_new_tokens=256, # Increased for potentially very_long prompts
                num_beams=1,
            )

        # Decode the numbers back into text and format the output
        decoded_tags = [tag for tag in tokenizer.batch_decode(outputs[0], skip_special_tokens=True) if tag.strip()]
        final_output = ", ".join(decoded_tags)

        print("--- Result ---")
        print("Completed prompt with generated tags:")
        print(final_output)
        print("-" * 20)
        
        # Ask the user if they want to run again
        try:
            run_again = questionary.confirm("Generate another prompt?").ask()
            if not run_again:
                break
            else:
                clear_screen()
        except KeyboardInterrupt:
            break

    print("\nExiting. Goodbye!")


if __name__ == "__main__":
    main()
# END: FULL SCRIPT