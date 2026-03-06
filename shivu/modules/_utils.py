from PIL import ImageFont, ImageDraw, Image
from io import BytesIO

def create_overlay_image(base_image: BytesIO, text: str, font_path: str, font_size: int, text_color: str = "white"):
    """
    Adds custom text overlay on an image using the latest Pillow methods.
    """
    # Open base image
    base_img = Image.open(base_image).convert("RGBA")

    # Create an overlay layer
    overlay = Image.new("RGBA", base_img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Load font
    font = ImageFont.truetype(font_path, font_size)

    # Naya method: Calculate text size using textbbox
    # bbox returns (left, top, right, bottom)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Calculate position (Center horizontal, Bottom vertical)
    position = ((base_img.size[0] - text_width) // 2, base_img.size[1] - text_height - 20)

    # Add text to overlay
    draw.text(position, text, fill=text_color, font=font)

    # Merge base image with overlay
    combined = Image.alpha_composite(base_img, overlay)

    # Save to BytesIO
    output = BytesIO()
    combined.save(output, format="PNG")
    output.seek(0)
    return output
