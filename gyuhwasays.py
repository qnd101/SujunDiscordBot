from PIL import Image, ImageDraw, ImageFont

def create_speech_bubble(text, font, padding=20):
    # Load font

    # Get text size
    dummy_img = Image.new("RGB", (1, 1))
    draw = ImageDraw.Draw(dummy_img)
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Bubble and tail sizes
    bubble_width = text_width + 2 * padding
    bubble_height = text_height + 2 * padding
    tail_length = 40  # Length of the tail
    tail_width = 30   # Width of the tail at the base

    # Create an image with enough space for the tail
    img = Image.new("RGBA", (bubble_width, bubble_height + tail_length), (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)

    # Define speech bubble shape (including the tail)
    bubble_body = [
        (0, 0),  # Top-left
        (0, bubble_height),  # Bottom-left
        (bubble_width // 4, bubble_height),  # Start of tail (left side)
        (bubble_width // 4 - tail_width, bubble_height + tail_length),  # Tail tip (pointed left)
        (bubble_width // 4 + tail_width, bubble_height),  # End of tail (right side)
        (bubble_width, bubble_height),  # Bottom-right
        (bubble_width, 0)  # Top-right
    ]

    # Draw the speech bubble
    draw.polygon(bubble_body, fill="white", outline="black", width=2)

    # Draw text
    text_x = padding
    text_y = padding*3/4
    draw.text((text_x, text_y), text, font=font, fill="black")

    return img

def gyuwhasays(text, font, baseimg: Image.Image, bubble_pos: tuple[int, int]):
    bubble_img = create_speech_bubble(text, font)
    bubble_width, bubble_height = bubble_img.size
    bubble_x, bubble_y = bubble_pos

    if bubble_x + bubble_width > baseimg.width:
        new_width = bubble_x + bubble_width
        new_img = Image.new("RGBA", (new_width, baseimg.height), (0, 0, 0, 0))
        new_img.paste(baseimg, (0, 0))
        baseimg = new_img
    else:
         baseimg = baseimg.convert("RGBA")

    baseimg.paste(bubble_img, (bubble_x, bubble_y), bubble_img)

    return baseimg

# font = ImageFont.truetype("./NotoSansKR-Regular.ttf" or "arial.ttf", 20)
# img = Image.open("gyuwha_500.jpg")
# # Example usage
# gyuwhasays("너 수준",font, img, (250, 0)).show()