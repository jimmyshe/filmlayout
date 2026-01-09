import os
from PIL import Image, ImageDraw, ImageOps

DEFAULT_DPI = 300

def mm_to_px(mm, dpi=DEFAULT_DPI):
    return int(mm * dpi / 25.4)

# 35mm film frame dimensions (Standard 135 film)
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

def draw_rounded_rect(draw, x, y, w, h, r, fill):
    draw.rectangle([x + r, y, x + w - r, y + h], fill=fill)
    draw.rectangle([x, y + r, x + w, y + h - r], fill=fill)
    draw.pieslice([x, y, x + 2*r, y + 2*r], 180, 270, fill=fill)
    draw.pieslice([x + w - 2*r, y, x + w, y + 2*r], 270, 360, fill=fill)
    draw.pieslice([x, y + h - 2*r, x + 2*r, y + h], 90, 180, fill=fill)
    draw.pieslice([x + w - 2*r, y + h - 2*r, x + w, y + h], 0, 90, fill=fill)

def draw_sprocket_holes(image, x_start_px, y_start_px, width_px, dpi=DEFAULT_DPI):
    """
    Draws continuous sprocket holes on the image.
    """
    draw = ImageDraw.Draw(image)
    hole_w = mm_to_px(SPROCKET_HOLE_W_MM, dpi)
    hole_h = mm_to_px(SPROCKET_HOLE_H_MM, dpi)
    pitch = mm_to_px(SPROCKET_HOLE_PITCH_MM, dpi)
    hole_r = mm_to_px(SPROCKET_HOLE_RADIUS_MM, dpi)
    
    margin_h = (FRAME_H_MM - IMAGE_H_MM) / 2
    top_hole_y = mm_to_px((margin_h - SPROCKET_HOLE_H_MM) / 2, dpi)
    bottom_hole_y = mm_to_px(FRAME_H_MM - margin_h + (margin_h - SPROCKET_HOLE_H_MM) / 2, dpi)
    
    # Use a fixed offset to ensure alignment across frames when gap is 2mm
    offset = mm_to_px(0.5, dpi)
    
    curr_x = x_start_px + offset
    while curr_x + hole_w <= x_start_px + width_px:
        draw_rounded_rect(draw, curr_x, y_start_px + top_hole_y, hole_w, hole_h, hole_r, "white")
        draw_rounded_rect(draw, curr_x, y_start_px + bottom_hole_y, hole_w, hole_h, hole_r, "white")
        curr_x += pitch

def create_film_frame(image_path, crop_mode='short', color_mode='color', film_type='positive', rotation=0, draw_holes=True, dpi=DEFAULT_DPI):
    """
    Takes an image and returns a PIL Image object of a 35mm film frame.
    """
    target_w = mm_to_px(FRAME_W_MM, dpi)
    target_h = mm_to_px(FRAME_H_MM, dpi)
    img_w = mm_to_px(IMAGE_W_MM, dpi)
    img_h = mm_to_px(IMAGE_H_MM, dpi)

    # 1. Create black background
    frame = Image.new('RGB', (target_w, target_h), color='black')

    # 2. Process input image
    try:
        with Image.open(image_path) as img:
            # Apply rotation
            if rotation != 0:
                img = img.rotate(rotation, expand=True)

            if color_mode == 'bw':
                img = img.convert('L').convert('RGB')
            else:
                img = img.convert('RGB')

            if film_type == 'negative':
                img = ImageOps.invert(img)

            img_ratio = img.width / img.height
            target_ratio = img_w / img_h

            if crop_mode == 'short':
                if img_ratio > target_ratio:
                    new_h = img_h
                    new_w = int(new_h * img_ratio)
                else:
                    new_w = img_w
                    new_h = int(new_w / img_ratio)
            else:
                if img_ratio > target_ratio:
                    new_w = img_w
                    new_h = int(new_w / img_ratio)
                else:
                    new_h = img_h
                    new_w = int(new_h * img_ratio)

            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            canvas = Image.new('RGB', (img_w, img_h), color='black')
            
            left = (img_w - new_w) // 2
            top = (img_h - new_h) // 2
            
            if crop_mode == 'short':
                crop_left = (new_w - img_w) // 2
                crop_top = (new_h - img_h) // 2
                img = img.crop((crop_left, crop_top, crop_left + img_w, crop_top + img_h))
                canvas.paste(img, (0, 0))
            else:
                canvas.paste(img, (left, top))

            offset_y = mm_to_px((FRAME_H_MM - IMAGE_H_MM) / 2, dpi)
            frame.paste(canvas, (0, offset_y))
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")

    # 3. Draw sprocket holes if requested
    if draw_holes:
        draw_sprocket_holes(frame, 0, 0, target_w, dpi)

    return frame

def layout_on_a4(image_list, margin_mm=10, gap_mm=2, dpi=DEFAULT_DPI):
    """
    image_list: list of PIL Image objects (the film frames)
    returns: (list of A4 PIL Images, list of layout_info)
    """
    margin = mm_to_px(margin_mm, dpi)
    gap = mm_to_px(gap_mm, dpi)
    
    a4_w_p = mm_to_px(A4_W_MM, dpi)
    a4_h_p = mm_to_px(A4_H_MM, dpi)
    
    a4_w_l = mm_to_px(A4_H_MM, dpi)
    a4_h_l = mm_to_px(A4_W_MM, dpi)
    
    frame_w = mm_to_px(FRAME_W_MM, dpi)
    frame_h = mm_to_px(FRAME_H_MM, dpi)
    
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
    all_layout_info = []
    
    if frames_per_page == 0:
        return [], []

    for i in range(0, len(image_list), frames_per_page):
        page = Image.new('RGB', (best_w, best_h), color='white')
        batch = image_list[i : i + frames_per_page]
        page_layout = []
        
        for r in range(best_rows):
            start_idx = r * best_cols
            if start_idx >= len(batch):
                break
            
            row_batch = batch[start_idx : min(start_idx + best_cols, len(batch))]
            row_cols = len(row_batch)
            row_w_px = row_cols * frame_w + (row_cols - 1) * gap
            
            x_row_start = margin
            y_row_start = margin + r * (frame_h + gap)
            
            # Draw black background for the whole row (strip)
            draw = ImageDraw.Draw(page)
            draw.rectangle([x_row_start, y_row_start, x_row_start + row_w_px, y_row_start + frame_h], fill="black")
            
            for c, img in enumerate(row_batch):
                img_idx = i + start_idx + c
                x = x_row_start + c * (frame_w + gap)
                y = y_row_start
                page.paste(img, (x, y))
                page_layout.append({
                    "rect": (x, y, x + frame_w, y + frame_h),
                    "index": img_idx
                })
            
            # Draw continuous sprocket holes for the row
            draw_sprocket_holes(page, x_row_start, y_row_start, row_w_px, dpi)
            
        pages.append(page)
        all_layout_info.append(page_layout)
        
    return pages, all_layout_info
