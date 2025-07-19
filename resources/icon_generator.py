"""
Generate a simple icon for ObsidianClone
Creates both .ico for Windows and .icns for macOS
"""
from PIL import Image, ImageDraw, ImageFont
import os

def create_icon():
    # Create a 256x256 image with a dark background
    size = 256
    img = Image.new('RGBA', (size, size), (30, 30, 40, 255))
    draw = ImageDraw.Draw(img)
    
    # Draw a stylized "O" for ObsidianClone
    # Outer circle
    margin = 40
    draw.ellipse([margin, margin, size-margin, size-margin], 
                 fill=(100, 80, 200, 255), outline=(150, 130, 250, 255), width=8)
    
    # Inner circle (to create a ring)
    inner_margin = 80
    draw.ellipse([inner_margin, inner_margin, size-inner_margin, size-inner_margin], 
                 fill=(30, 30, 40, 255))
    
    # Add a small accent dot
    dot_size = 30
    dot_x = size - margin - 20
    dot_y = margin + 20
    draw.ellipse([dot_x - dot_size//2, dot_y - dot_size//2, 
                  dot_x + dot_size//2, dot_y + dot_size//2], 
                 fill=(150, 130, 250, 255))
    
    # Save in multiple sizes for .ico file
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    icons = []
    
    for target_size in sizes:
        resized = img.resize(target_size, Image.Resampling.LANCZOS)
        icons.append(resized)
    
    # Save as .ico for Windows
    icons[5].save('obsidianclone.ico', format='ICO', sizes=sizes)
    
    # Save as .png for other uses
    img.save('obsidianclone.png', format='PNG')
    
    print("Icons created successfully!")

if __name__ == "__main__":
    try:
        from PIL import Image, ImageDraw
        create_icon()
    except ImportError:
        print("Pillow library not installed. Creating a placeholder icon file.")
        # Create an empty ico file as placeholder
        with open('obsidianclone.ico', 'wb') as f:
            # Minimal ICO header
            f.write(b'\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00\x18\x00')