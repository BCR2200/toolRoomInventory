from pathlib import Path

import qrcode


def generate_qr_code(data, filename: Path):
    # Create QR code instance
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )

    # Add data to the QR code
    qr.add_data(data)
    qr.make(fit=True)

    # Create an image from the QR code
    qr_image = qr.make_image(fill_color="black", back_color="white")

    # Save the image
    filename.touch()
    with open(filename, "wb") as f:
        qr_image.format = "PNG"
        qr_image.save(f)
