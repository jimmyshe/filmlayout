import processor
from PIL import Image

def test_generate():
    # Create a dummy image (Gradient)
    img = Image.new('RGB', (1000, 600), color='red')
    # Add some detail
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([100, 100, 400, 400], fill='blue')
    draw.ellipse([500, 100, 800, 400], fill='green')
    img.save("test_input.jpg")
    
    # 1. Test short side (Fill) - Default
    frame1 = processor.create_film_frame("test_input.jpg", crop_mode='short')
    frame1.save("test_frame_fill.png")
    print("Saved test_frame_fill.png")
    
    # 2. Test long side (Fit)
    frame2 = processor.create_film_frame("test_input.jpg", crop_mode='long')
    frame2.save("test_frame_fit.png")
    print("Saved test_frame_fit.png")

    # 3. Test BW
    frame3 = processor.create_film_frame("test_input.jpg", color_mode='bw')
    frame3.save("test_frame_bw.png")
    print("Saved test_frame_bw.png")

    # 4. Test Negative
    frame4 = processor.create_film_frame("test_input.jpg", film_type='negative')
    frame4.save("test_frame_neg.png")
    print("Saved test_frame_neg.png")
    
    # Layout test
    frames = [frame1, frame2, frame3, frame4] * 10
    pages, info = processor.layout_on_a4(frames)
    for i, page in enumerate(pages):
        page.save(f"test_page_{i}.png")
        print(f"Saved test_page_{i}.png")

if __name__ == "__main__":
    try:
        test_generate()
    except Exception as e:
        print(f"Error during test: {e}")
