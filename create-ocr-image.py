#!/usr/bin/env python3
from PIL import Image, ImageDraw, ImageFont
import textwrap

# Create a white image
width, height = 800, 1200
image = Image.new('RGB', (width, height), 'white')
draw = ImageDraw.Draw(image)

# Read the content
with open('test-flujo-ocr-content.txt', 'r') as f:
    content = f.read()

# Try to use a system font, fallback to default
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14)
    title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 20)
except:
    font = ImageFont.load_default()
    title_font = ImageFont.load_default()

# Draw text
y_position = 50
line_spacing = 20

# Split content into lines and wrap
lines = content.split('\n')
for line in lines:
    if line.strip().startswith('==='):
        # Title/section
        draw.text((50, y_position), line, fill='black', font=title_font)
        y_position += 30
    else:
        # Regular text - wrap long lines
        wrapped = textwrap.fill(line, width=80)
        for wrapped_line in wrapped.split('\n'):
            if y_position < height - 50:  # Don't go beyond page
                draw.text((50, y_position), wrapped_line, fill='black', font=font)
                y_position += line_spacing

# Save the image
image.save('test-flujo-ocr.png')
print("✅ Imagen PNG creada: test-flujo-ocr.png")
