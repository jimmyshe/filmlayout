import os
from PIL import Image, ImageDraw, ImageOps

DPI = 300
MM_TO_PX = DPI / 25.4

def mm_to_px(mm):
    return int(mm * MM_TO_PX)

# 35mm film frame dimensions (Standard 135 film)
# Total width: 36mm (for the frame image part, usually film is a continuous strip)
# Total height: 35mm
# Image area: 36mm x 24mm
FRAME_W_MM = 36
FRAME_H_MM = 35
IMAGE_W_MM = 36
IMAGE_H_MM = 24
SPROCKET_HOLE_W_MM = 2.8
SPROCKET_HOLE_H_MM = 1.98
SPROCKET_HOLE_PITCH_MM = 4.75
SPROCKET_HOLE_RADIUS_MM = 0.5

# A4 dimensions
A4_W_MM = 210
A4_H_MM = 297

def create_film_frame(image_path, crop_mode='short', color_mode='color', film_type='positive'):
    """
    Takes an image and returns a PIL Image object of a 35mm film frame.
    crop_mode: 'short' (fill) or 'long' (fit)
    color_mode: 'color' or 'bw'
    film_type: 'positive' or 'negative'
    """
    target_w = mm_to_px(FRAME_W_MM)
    target_h = mm_to_px(FRAME_H_MM)
    img_w = mm_to_px(IMAGE_W_MM)
    img_h = mm_to_px(IMAGE_H_MM)

    # 1. Create black background
    frame = Image.new('RGB', (target_w, target_h), color='black')

    # 2. Process input image
    try:
        with Image.open(image_path) as img:
            # Handle color mode
            if color_mode == 'bw':
                img = img.convert('L').convert('RGB')
            else:
                img = img.convert('RGB')

            # Handle film type (negative)
            if film_type == 'negative':
                img = ImageOps.invert(img)

            img_ratio = img.width / img.height
            target_ratio = img_w / img_h

            if crop_mode == 'short':
                # Aspect fill / cover (Align short side)
                if img_ratio > target_ratio:
                    new_h = img_h
                    new_w = int(new_h * img_ratio)
                else:
                    new_w = img_w
                    new_h = int(new_w / img_ratio)
            else:
                # Aspect fit (Align long side)
                if img_ratio > target_ratio:
                    new_w = img_w
                    new_h = int(new_w / img_ratio)
                else:
                    new_h = img_h
                    new_w = int(new_h * img_ratio)

            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

            # Create a transparent-friendly canvas for the image part (actually black is fine as film is black)
            canvas = Image.new('RGB', (img_w, img_h), color='black')
            
            # Center the resized image on the canvas
            left = (img_w - new_w) // 2
            top = (img_h - new_h) // 2
            
            if crop_mode == 'short':
                # Crop center if filling
                crop_left = (new_w - img_w) // 2
                crop_top = (new_h - img_h) // 2
                img = img.crop((crop_left, crop_top, crop_left + img_w, crop_top + img_h))
                canvas.paste(img, (0, 0))
            else:
                # Paste centered if fitting
                canvas.paste(img, (left, top))

            # Paste canvas onto frame
            offset_y = mm_to_px((FRAME_H_MM - IMAGE_H_MM) / 2)
            frame.paste(canvas, (0, offset_y))
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")

    # 3. Draw sprocket holes
    draw = ImageDraw.Draw(frame)
    hole_w = mm_to_px(SPROCKET_HOLE_W_MM)
    hole_h = mm_to_px(SPROCKET_HOLE_H_MM)
    pitch = mm_to_px(SPROCKET_HOLE_PITCH_MM)
    
    # Calculate starting x to center holes
    num_holes = int(FRAME_W_MM / SPROCKET_HOLE_PITCH_MM)
    start_x = (target_w - (num_holes - 1) * pitch - hole_w) // 2
    
    # Vertical positions for holes
    # Usually holes are centered in the 5.5mm margin
    margin_h = (FRAME_H_MM - IMAGE_H_MM) / 2
    top_hole_y = mm_to_px((margin_h - SPROCKET_HOLE_H_MM) / 2)
    bottom_hole_y = mm_to_px(FRAME_H_MM - margin_h + (margin_h - SPROCKET_HOLE_H_MM) / 2)

    def draw_rounded_rect(draw, x, y, w, h, r, fill):
        draw.rectangle([x + r, y, x + w - r, y + h], fill=fill)
        draw.rectangle([x, y + r, x + w, y + h - r], fill=fill)
        draw.pieslice([x, y, x + 2*r, y + 2*r], 180, 270, fill=fill)
        draw.pieslice([x + w - 2*r, y, x + w, y + 2*r], 270, 360, fill=fill)
        draw.pieslice([x, y + h - 2*r, x + 2*r, y + h], 90, 180, fill=fill)
        draw.pieslice([x + w - 2*r, y + h - 2*r, x + w, y + h], 0, 90, fill=fill)

    hole_r = mm_to_px(SPROCKET_HOLE_RADIUS_MM)
    for i in range(num_holes):
        x = start_x + i * pitch
        # Top hole
        draw_rounded_rect(draw, x, top_hole_y, hole_w, hole_h, hole_r, "white")
        # Bottom hole
        draw_rounded_rect(draw, x, bottom_hole_y, hole_w, hole_h, hole_r, "white")

    return frame

def layout_on_a4(image_list, margin_mm=10, gap_mm=2):
    """
    image_list: list of PIL Image objects (the film frames)
    returns: list of A4 PIL Image objects
    """
    margin = mm_to_px(margin_mm)
    gap = mm_to_px(gap_mm)
    
    # Try portrait
    a4_w_p = mm_to_px(A4_W_MM)
    a4_h_p = mm_to_px(A4_H_MM)
    
    # Try landscape
    a4_w_l = mm_to_px(A4_H_MM)
    a4_h_l = mm_to_px(A4_W_MM)
    
    frame_w = mm_to_px(FRAME_W_MM)
    frame_h = mm_to_px(FRAME_H_MM)
    
    def get_capacity(w, h, fw, fh, m, g):
        cols = (w - 2 * m + g) // (fw + g)
        rows = (h - 2 * m + g) // (fh + g)
        if cols < 0 or rows < 0: return 0, 0, 0
        return cols * rows, cols, rows

    cap_p, cols_p, rows_p = get_capacity(a4_w_p, a4_h_p, frame_w, frame_h, margin, gap)
    cap_l, cols_l, rows_l = get_capacity(a4_w_l, a4_h_l, frame_w, frame_h, margin, gap)
    
    if cap_l > cap_p:
        best_w, best_h = a4_w_l, a4_h_l
        best_cols, best_rows = cols_l, rows_l
        frames_per_page = cap_l
    else:
        best_w, best_h = a4_w_p, a4_h_p
        best_cols, best_rows = cols_p, rows_p
        frames_per_page = cap_p
        
    pages = []
    
    if frames_per_page == 0:
        return []

    for i in range(0, len(image_list), frames_per_page):
        page = Image.new('RGB', (best_w, best_h), color='white')
        batch = image_list[i : i + frames_per_page]
        
        for idx, img in enumerate(batch):
            r = idx // best_cols
            c = idx % best_cols
            
            x = margin + c * (frame_w + gap)
            y = margin + r * (frame_h + gap)
            
            page.paste(img, (x, y))
        
        pages.append(page)
        
    return pages
