import os
from PIL import Image, ImageDraw, ImageFont

def get_font():
    try:
        return ImageFont.truetype("arial.ttf", 20)
    except IOError:
        return ImageFont.load_default()

def create_base_scene(size=(800, 600)):
    # Background: light gray (desk surface) bottom 60%, lighter gray (wall) top 40%
    img = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)
    wall_height = int(size[1] * 0.4)
    draw.rectangle([0, 0, size[0], wall_height], fill=(230, 230, 230))
    draw.rectangle([0, wall_height, size[0], size[1]], fill=(200, 200, 200))
    draw.line([0, wall_height, size[0], wall_height], fill=(150, 150, 150), width=3)
    return img

def add_object(img, bbox, color, label):
    draw = ImageDraw.Draw(img)
    draw.rectangle(bbox, fill=color, outline="black")
    font = get_font()
    draw.text((bbox[0] + 5, bbox[1] + 5), label, fill="black", font=font)

def apply_tint(img, tint_color, factor=0.2):
    # Create a solid color image
    tint = Image.new("RGB", img.size, tint_color)
    return Image.blend(img, tint, factor)

def generate_set1(base_dir):
    os.makedirs(os.path.join(base_dir, 'set1_before'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'set1_after'), exist_ok=True)

    # Before
    img_before = create_base_scene()
    add_object(img_before, (100, 350, 160, 450), "blue", "Mug")
    add_object(img_before, (300, 320, 450, 460), "green", "Book")
    add_object(img_before, (550, 330, 620, 460), "orange", "Pencils")
    add_object(img_before, (200, 380, 280, 450), "gray", "Phone")
    img_before = apply_tint(img_before, (255, 255, 200), 0.15) # Warm yellow tint
    img_before.save(os.path.join(base_dir, 'set1_before', 'photo1.png'))

    # After
    img_after = create_base_scene()
    add_object(img_after, (650, 350, 710, 450), "blue", "Mug") # moved to far right
    add_object(img_after, (300, 320, 450, 460), "green", "Book") # unchanged
    add_object(img_after, (550, 330, 620, 460), "orange", "Pencils") # unchanged
    add_object(img_after, (350, 100, 430, 180), "pink", "Notes") # added
    img_after = apply_tint(img_after, (200, 220, 255), 0.15) # Cooler bluer tint
    img_after.save(os.path.join(base_dir, 'set1_after', 'photo1.png'))

def generate_set2(base_dir):
    os.makedirs(os.path.join(base_dir, 'set2_before'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'set2_after'), exist_ok=True)

    # Before
    img_before = create_base_scene()
    add_object(img_before, (100, 350, 160, 450), "blue", "Mug")
    add_object(img_before, (300, 320, 450, 460), "green", "Book")
    add_object(img_before, (550, 330, 620, 460), "orange", "Pencils")
    add_object(img_before, (200, 380, 280, 450), "gray", "Phone")
    img_before.save(os.path.join(base_dir, 'set2_before', 'photo1.png'))

    # After
    img_after = create_base_scene()
    add_object(img_after, (100, 350, 160, 450), "blue", "Mug")
    add_object(img_after, (300, 320, 450, 460), "green", "Book")
    add_object(img_after, (550, 330, 620, 460), "orange", "Pencils")
    add_object(img_after, (200, 380, 280, 450), "gray", "Phone")
    
    # Darker overall and warm tint
    img_after = img_after.point(lambda p: p * 0.85)
    img_after = apply_tint(img_after, (255, 150, 0), 0.2)
    img_after.save(os.path.join(base_dir, 'set2_after', 'photo1.png'))

def generate_set3(base_dir):
    os.makedirs(os.path.join(base_dir, 'set3_before'), exist_ok=True)
    os.makedirs(os.path.join(base_dir, 'set3_after'), exist_ok=True)

    # Before
    img_before = create_base_scene()
    add_object(img_before, (100, 350, 160, 450), "blue", "Mug")
    add_object(img_before, (300, 320, 450, 460), "green", "Book")
    add_object(img_before, (550, 330, 620, 460), "orange", "Pencils")
    add_object(img_before, (200, 380, 280, 450), "gray", "Phone")
    img_before.save(os.path.join(base_dir, 'set3_before', 'photo1.png'))

    # After - cropped view (x >= 350)
    img_after_full = create_base_scene()
    add_object(img_after_full, (100, 350, 160, 450), "blue", "Mug")
    add_object(img_after_full, (300, 320, 450, 460), "green", "Book")
    add_object(img_after_full, (550, 330, 620, 460), "orange", "Pencils")
    add_object(img_after_full, (200, 380, 280, 450), "gray", "Phone")
    
    cropped = img_after_full.crop((350, 0, 800, 600))
    # Scale up cropped region to 800x600
    img_after = cropped.resize((800, 600), Image.Resampling.LANCZOS)
    img_after.save(os.path.join(base_dir, 'set3_after', 'photo1.png'))

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    print("Generating Set 1...")
    generate_set1(script_dir)
    print("Generating Set 2...")
    generate_set2(script_dir)
    print("Generating Set 3...")
    generate_set3(script_dir)
    print("Done generating test sets.")
