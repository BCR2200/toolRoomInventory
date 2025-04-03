from pathlib import Path
import barcode
from barcode.writer import ImageWriter


def generate_barcode(data: str, filename: Path):
    # Create the barcode image
    # Using Code128 as it's versatile and can encode both numbers and text
    code = barcode.Code39(data, writer=ImageWriter())

    # Save the image
    # The save method returns the filename with the extension
    # Save the image
    with open(filename, "wb") as f:
        code.write(f, text=data)
