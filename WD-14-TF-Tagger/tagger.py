import os
import os
import re
import numpy as np
import tensorflow as tf
import pandas as pd
import PIL.Image
import cv2
import argparse
import urllib.request

#This options are good but it takes much more time to start. Maybe some aditional code could make things faster. TODO
os.environ["TF_XLA_FLAGS"] = "--tf_xla_auto_jit=2 --tf_xla_cpu_global_jit"
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "1"
gpus = tf.config.list_physical_devices('GPU')
if gpus:
    try:
        for gpu in gpus:
            tf.config.experimental.set_memory_growth(gpu, True)
        logical_gpus = tf.config.experimental.list_logical_devices('GPU')
        print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
    except RuntimeError as e:
        print(e)
else:
    print("No GPUs detected, using CPU.")

parser = argparse.ArgumentParser()
parser.add_argument("--input", type=str, default="./Test", help="Folder of images. By default will be using the Test folder")
parser.add_argument("--output", type=str, help="Output folder. By default same as the input")
parser.add_argument("--model", type=str, help="Path to your model's folder")
parser.add_argument("--label", type=str, default="./Models/selected_tags.csv", help="By default assumes that 'selected_tags.csv' is on the same directory.")
parser.add_argument("--batch_size", type=int, default=32, help="Batch size for processing images. Default is 32.")
parser.add_argument("--general_score", type=float, default="0.5", help="Sets the minimum score of 'confidence'. Default '0.5'")
parser.add_argument("--character_score", type=float, default="0.85", help="Sets the minimum score of 'character confidence'. Default '0.85'")
parser.add_argument("--add_initial_keyword", type=str, help="Keyword to add at the beginning of the tags.")
parser.add_argument("--add_final_keyword", type=str, help="Keyword to add at the end of the tags.")
parser.add_argument("--download", action="store_true", help="Download the specified model.")
args = parser.parse_args()

LABEL_FILENAME = args.label
IMAGES_DIRECTORY = args.input
OUTPUT_DIRECTORY = args.output
BATCH_SIZE = args.batch_size
SCORE_GENERAL_THRESHOLD = args.general_score
SCORE_CHARACTER_THRESHOLD = args.character_score
MODEL = f"./Models/{args.model}"
MODEL_NAME = args.model
INITIAL_KEYWORD = args.add_initial_keyword
FINAL_KEYWORD = args.add_final_keyword

if args.output is None:
    OUTPUT_DIRECTORY = IMAGES_DIRECTORY
else:
    OUTPUT_DIRECTORY = args.output

def download_file(url: str, filename: str):
    urllib.request.urlretrieve(url, filename)

def download_files():
    LABEL_URL = "https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/selected_tags.csv"
    
    if not os.path.exists(LABEL_FILENAME):
        print(f"Downloading {LABEL_FILENAME}...")
        download_file(LABEL_URL, LABEL_FILENAME)

def download_model():
    model_urls = {
        "SwinV2": [
            "https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/saved_model.pb",
            "https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/variables/variables.data-00000-of-00001",
            "https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2/resolve/main/variables/variables.index",
        ],
        "ConvNext": [
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnext-tagger-v2/resolve/main/saved_model.pb",
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnext-tagger-v2/resolve/main/variables/variables.data-00000-of-00001",
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnext-tagger-v2/resolve/main/variables/variables.index",
        ],
        "ConvNextV2": [
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnextv2-tagger-v2/resolve/main/saved_model.pb",
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnextv2-tagger-v2/resolve/main/variables/variables.data-00000-of-00001",
            "https://huggingface.co/SmilingWolf/wd-v1-4-convnextv2-tagger-v2/resolve/main/variables/variables.index",
        ],
        "ViTv2": [
            "https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2/resolve/main/saved_model.pb"
            "https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2/resolve/main/variables/variables.data-00000-of-00001"
            "https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2/resolve/main/variables/variables.index"
        ],
    }

    if MODEL_NAME not in model_urls:
        print(f"Model {MODEL_NAME} is not supported for downloading.")
        return

    model_folder = os.path.join("Models", MODEL_NAME)
    variables_folder = os.path.join(model_folder, "variables")

    if not os.path.exists(model_folder):
        os.makedirs(model_folder)

    if not os.path.exists(variables_folder):
        os.makedirs(variables_folder)

    for url in model_urls[MODEL_NAME]:
        filename = os.path.basename(url)
        file_path = os.path.join(variables_folder, filename) if "variables" in filename else os.path.join(model_folder, filename)
        print(f"Downloading {filename}...")
        urllib.request.urlretrieve(url, file_path)

def load_labels() -> list[str]:
    df = pd.read_csv(LABEL_FILENAME)
    tag_names = df["name"].tolist()
    rating_indexes = list(np.where(df["category"] == 9)[0])
    general_indexes = list(np.where(df["category"] == 0)[0])
    character_indexes = list(np.where(df["category"] == 4)[0])
    return tag_names, rating_indexes, general_indexes, character_indexes

def process_images(model, image_paths, batch_size):
    images = []
    
    for image_path in image_paths:
        image = PIL.Image.open(image_path)
        input_shape = model.signatures['serving_default'].inputs[0].shape.as_list()
        _, height, width, _ = input_shape
        image = image.convert("RGBA")
        new_image = PIL.Image.new("RGBA", image.size, "WHITE")
        new_image.paste(image, mask=image)
        image = new_image.convert("RGB")
        image = np.asarray(image)
        image = image[:, :, ::-1]
        image_size = (height, height)
        image = cv2.resize(image, image_size, interpolation=cv2.INTER_AREA)
        image = image.astype(np.float32)
        
        images.append(image)
    
    images_batch = np.stack(images)
    
    return images_batch

def predict(
    model,
    images_batch,
    general_threshold: float,
    character_threshold: float,
    tag_names: list[str],
    rating_indexes: list[np.int64],
    general_indexes: list[np.int64],
    character_indexes: list[np.int64],
):
    output_name = list(model.signatures['serving_default'].structured_outputs.keys())[0] #Just so it doesn't freak out in case of changes
    #print(f"Output name: {output_name}") #Expected: predictions_sigmoid
    probs_batch = model.signatures['serving_default'](tf.constant(images_batch))[output_name].numpy()
    
    results = []

    for probs in probs_batch:
        labels = list(zip(tag_names, probs.astype(float)))

        ratings_names = [labels[i] for i in rating_indexes]
        rating = dict(ratings_names)
        general_names = [labels[i] for i in general_indexes]
        general_res = [x for x in general_names if x[1] > general_threshold]
        general_res = dict(general_res)
        character_names = [labels[i] for i in character_indexes]
        character_res = [x for x in character_names if x[1] > character_threshold]
        character_res = dict(character_res)

        b = dict(sorted(general_res.items(), key=lambda item: item[1], reverse=True))
        a = (
            ", ".join(list(b.keys()))
            .replace("_", " ")
            .replace("(", "\(")
            .replace(")", "\)")
            .replace(", ,", ",")
        )
        a = re.sub(r'\\?\([^)]*\)', '', a)
        c = ", ".join(list(b.keys()))
        character_tags = ', '.join(list(character_res.keys())).replace('_', ' ')
        character_tags = re.sub(r'\([^)]*\)', '', character_tags)

        if INITIAL_KEYWORD and FINAL_KEYWORD:
            result = f"{INITIAL_KEYWORD}, {character_tags}, {a}, {FINAL_KEYWORD}"
        elif INITIAL_KEYWORD:
            result = f"{INITIAL_KEYWORD}, {character_tags}, {a}"
        elif FINAL_KEYWORD:
            result = f"{character_tags}, {a}, {FINAL_KEYWORD}"
        else:
            result = f"{character_tags}, {a}"
        result = re.sub(r'\s*,\s*', ', ', result)
        
        results.append(result)
    
    return results

def main():
    if args.download:
        download_model()
    model = tf.saved_model.load(MODEL)
    
    tag_names, rating_indexes, general_indexes, character_indexes = load_labels()

    if not os.path.exists(OUTPUT_DIRECTORY):
        os.makedirs(OUTPUT_DIRECTORY)

    image_paths = [os.path.join(IMAGES_DIRECTORY, f) for f in os.listdir(IMAGES_DIRECTORY) if f.endswith(".jpg") or f.endswith(".png") or f.endswith(".webp")]

    for i in range(0, len(image_paths), BATCH_SIZE):
        batch_image_paths = image_paths[i:i + BATCH_SIZE]
        images_batch = process_images(model, batch_image_paths, BATCH_SIZE)
        
        results = predict(
            model,
            images_batch,
            SCORE_GENERAL_THRESHOLD,
            SCORE_CHARACTER_THRESHOLD,
            tag_names,
            rating_indexes,
            general_indexes,
            character_indexes,
        )
        
        for j, result in enumerate(results):
            output_path = os.path.join(OUTPUT_DIRECTORY, os.path.splitext(os.path.basename(batch_image_paths[j]))[0] + ".txt")

            with open(output_path, "w") as f:
                print(f"Writing result for {os.path.basename(batch_image_paths[j])}...")
                f.write(str(result))

if __name__ == "__main__":
    download_files()
    main()