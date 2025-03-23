import unittest
from main import sanitize_path, ensure_path_in_base
from pathlib import Path


class TestSanitizePath(unittest.TestCase):
    def setUp(self):
        self.base_path = "/valid/base/path"

    def test_valid_path_same_directory(self):
        result = sanitize_path(self.base_path, "file.txt")
        expected = (Path(self.base_path) / Path("file.txt")).resolve()
        self.assertEqual(expected, result)

    def test_valid_path_subdirectory_allowed(self):
        result = sanitize_path(self.base_path, "subdir/file.txt", allow_subdirs=True)
        expected = (Path(self.base_path) / Path("subdir/file.txt")).resolve()
        self.assertEqual(expected, result)

    def test_invalid_path_outside_base_directory(self):
        with self.assertRaises(ValueError):
            sanitize_path(self.base_path, "../outside_file.txt")

    def test_invalid_path_subdirectory_not_allowed(self):
        with self.assertRaises(ValueError):
            sanitize_path(self.base_path, "subdir/file.txt", allow_subdirs=False)

    def test_relative_base_path(self):
        relative_base_path = "relative/base/path"
        result = sanitize_path(relative_base_path, "file.txt")
        expected = (Path(relative_base_path) / Path("file.txt")).resolve()
        self.assertEqual(expected, result)

    def test_invalid_path_outside_relative_base_directory(self):
        relative_base_path = "relative/base/path"
        with self.assertRaises(ValueError):
            sanitize_path(relative_base_path, "../outside_file.txt")

    def test_invalid_path_absolute(self):
        with self.assertRaises(ValueError):
            sanitize_path(self.base_path, "/absolute/file.txt")

    def test_empty_path(self):
        with self.assertRaises(ValueError):
            sanitize_path(self.base_path, "")


class TestEnsurePathInBase(unittest.TestCase):
    def setUp(self):
        self.base_path = "/valid/base/path"

    def test_valid_path_within_base_directory(self):
        test_path = Path(self.base_path) / Path("file.txt")
        result = ensure_path_in_base(self.base_path, test_path, allow_subdirs=False)
        expected = (Path(self.base_path) / Path("file.txt")).resolve()
        self.assertEqual(result, expected)

    def test_valid_path_within_base_directory_subdir(self):
        test_path = Path(self.base_path) / Path("subdir/file.txt")
        result = ensure_path_in_base(self.base_path, test_path, allow_subdirs=True)
        expected = (Path(self.base_path) / Path("subdir/file.txt")).resolve()
        self.assertEqual(result, expected)

    def test_absolute_path_within_base_directory(self):
        test_path = Path("/valid/base/path/file.txt")
        result = ensure_path_in_base(self.base_path, test_path, allow_subdirs=False)
        expected = (Path(self.base_path) / Path("file.txt")).resolve()
        self.assertEqual(result, expected)

    def test_absolute_path_within_base_directory_subdir(self):
        test_path = Path("/valid/base/path/subdir/file.txt")
        result = ensure_path_in_base(self.base_path, test_path, allow_subdirs=True)
        expected = (Path(self.base_path) / Path("subdir/file.txt")).resolve()
        self.assertEqual(result, expected)

    def test_path_traversal(self):
        test_path = Path("/valid/base/path/../file.txt")
        with self.assertRaises(ValueError):
            ensure_path_in_base(self.base_path, test_path, allow_subdirs=False)

    def test_path_traversal_subdir(self):
        test_path = Path("/valid/base/path/subdir/../../file.txt")
        with self.assertRaises(ValueError):
            ensure_path_in_base(self.base_path, test_path, allow_subdirs=False)


if __name__ == '__main__':
    unittest.main()