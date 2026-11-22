import os
import cv2
import albumentations as A

def get_augmentation_pipelines():
    """
    Defines 5 realistic, visually distinct insurance environmental pipelines.
    Using modern Albumentations 1.4+ syntax.
    """
    return {
        "rain": A.Compose([
            A.RandomRain(drop_length=20, drop_width=1, p=1.0)
        ]),
        "low_light": A.Compose([
            # Visibly darkens to simulate night/dark garage
            A.RandomBrightnessContrast(brightness_limit=(-0.5, -0.4), contrast_limit=(-0.2, -0.1), p=1.0)
        ]),
        "glare": A.Compose([
            A.RandomSunFlare(flare_roi=(0.2, 0, 0.8, 0.5), angle_range=(0, 1), p=1.0)
        ]),
        "fog": A.Compose([
            A.RandomFog(fog_coef_range=(0.4, 0.6), p=1.0)
        ]),
        "sensor_noise": A.Compose([
            A.GaussNoise(var_limit=(100.0, 300.0), p=1.0),
            A.HorizontalFlip(p=1.0)  # Flips horizontally to simulate reverse perspective
        ])
    }
def augment_claim_image(image_path, output_dir):
    """
    Takes an input image path, applies all 5 pipelines,
    saves the augmented photos into output_dir,
    and returns a list of dictionaries with metadata.
    """
    # 1. Read the source image from disk (OpenCV loads as BGR)
    image_bgr = cv2.imread(image_path)
    if image_bgr is None:
        raise ValueError(f"Could not read image at {image_path}")

    # 2. Convert BGR -> RGB for Albumentations
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    pipelines = get_augmentation_pipelines()
    augmented_results = []

    # 3. Apply each transformation pipeline
    for effect_name, transform in pipelines.items():
        # Albumentations expects named argument image=...
     transformed = transform(image=image_rgb.copy())
        aug_rgb = transformed["image"]

        # Convert back RGB -> BGR for OpenCV saving
        aug_bgr = cv2.cvtColor(aug_rgb, cv2.COLOR_RGB2BGR)

        # Build output filename: e.g., bumper_damaged_rain.jpg
        out_filename = f"{base_name}_{effect_name}.jpg"
        out_path = os.path.join(output_dir, out_filename)

        # Write to disk
        cv2.imwrite(out_path, aug_bgr)

        # Record metadata
        augmented_results.append({
            "effect": effect_name,
            "filename": out_filename,
            "path": out_path
        })

    return augmented_results