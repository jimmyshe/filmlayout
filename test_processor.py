import processor
from PIL import Image

def test_generate():
    # Create a dummy image
    dummy = Image.new('RGB', (1000, 1000), color='red')
    dummy.save("test_input.jpg")
    
    # Process
    frame = processor.create_film_frame("test_input.jpg")
    frame.save("test_frame.png")
    print("Saved test_frame.png")
    
    # Layout
    frames = [frame] * 50
    pages = processor.layout_on_a4(frames)
    for i, page in enumerate(pages):
        page.save(f"test_page_{i}.png")
        print(f"Saved test_page_{i}.png")

if __name__ == "__main__":
    try:
        test_generate()
    except Exception as e:
        print(f"Error during test: {e}")
