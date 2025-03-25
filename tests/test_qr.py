import tempfile
import unittest
from pathlib import Path
from server.qr import generate_qr_code


class TestGenerateQRCode(unittest.TestCase):
    def test_qr_code_creation(self):
        """Test if a QR code can be successfully created and saved to a file."""
        data = "Test QR Code Data"
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:
            temp_file_path = Path(temp_file.name)
        try:
            generate_qr_code(data, temp_file_path)
            self.assertTrue(temp_file_path.exists(), "The QR code file was not created.")
            self.assertGreater(
                temp_file_path.stat().st_size, 0, "The QR code file is empty."
            )
        finally:
            temp_file_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
