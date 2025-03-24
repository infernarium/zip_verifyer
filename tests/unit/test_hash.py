import pytest
from unittest.mock import MagicMock
from fastapi import UploadFile
import hashlib

from app.check_hash import calculate_file_hash


def test_calculate_file_hash_large_file():
    # Создаем большой файл через повторение строки
    test_file_content = b"A" * (10**6)
    test_file = MagicMock(spec=UploadFile)
    test_file.file = MagicMock()
    test_file.file.read.side_effect = [
        test_file_content[:512000],
        test_file_content[512000:],
        b"",
    ]

    expected_hash = hashlib.sha256(test_file_content).hexdigest()
    result = calculate_file_hash(test_file)
    assert result == expected_hash


def test_calculate_file_hash_identical_files():
    test_file_content = b"Same content"

    test_file_1 = MagicMock(spec=UploadFile)
    test_file_1.file = MagicMock()
    test_file_1.file.read.side_effect = [test_file_content, b""]

    test_file_2 = MagicMock(spec=UploadFile)
    test_file_2.file = MagicMock()
    test_file_2.file.read.side_effect = [test_file_content, b""]

    hash_1 = calculate_file_hash(test_file_1)
    hash_2 = calculate_file_hash(test_file_2)

    assert hash_1 == hash_2, "Хеши должны быть одинаковыми для одинаковых файлов"


def test_calculate_file_hash_varied_characters():
    test_file_content = b"\x00\xff\x01Hello\x7fWorld!\xfe"

    test_file = MagicMock(spec=UploadFile)
    test_file.file = MagicMock()
    test_file.file.read.side_effect = [test_file_content, b""]

    expected_hash = hashlib.sha256(test_file_content).hexdigest()
    result = calculate_file_hash(test_file)

    assert result == expected_hash


def test_calculate_file_hash_stability():
    test_file_content = b"Stable test"

    test_file = MagicMock(spec=UploadFile)
    test_file.file = MagicMock()
    test_file.file.read.side_effect = [test_file_content, b""]

    first_hash = calculate_file_hash(test_file)

    test_file = MagicMock(spec=UploadFile)
    test_file.file = MagicMock()
    test_file.file.read.side_effect = [test_file_content, b""]

    second_hash = calculate_file_hash(test_file)

    assert first_hash == second_hash, "Hash не должен меняться при повторном вызове"


def test_same_file_different_names():
    """Один и тот же файл с разными названиями должен иметь одинаковый хеш."""
    test_file_content = b"Same content"

    test_file_1 = MagicMock(spec=UploadFile)
    test_file_1.filename = "file1.zip"
    test_file_1.file = MagicMock()
    test_file_1.file.read.side_effect = [test_file_content, b""]

    test_file_2 = MagicMock(spec=UploadFile)
    test_file_2.filename = "file2.zip"
    test_file_2.file = MagicMock()
    test_file_2.file.read.side_effect = [test_file_content, b""]

    hash_1 = calculate_file_hash(test_file_1)
    hash_2 = calculate_file_hash(test_file_2)

    assert (
        hash_1 == hash_2
    ), "Hash должен быть одинаковым для одного и того же содержимого, даже если имена файлов разные"


def test_different_files_same_name():
    """Разные файлы с одинаковыми названиями должны иметь разные хеши."""
    test_file_content_1 = b"Content A"
    test_file_content_2 = b"Content B"

    test_file_1 = MagicMock(spec=UploadFile)
    test_file_1.filename = "file.zip"
    test_file_1.file = MagicMock()
    test_file_1.file.read.side_effect = [test_file_content_1, b""]

    test_file_2 = MagicMock(spec=UploadFile)
    test_file_2.filename = "file.zip"  # Имя то же самое, но содержимое другое
    test_file_2.file = MagicMock()
    test_file_2.file.read.side_effect = [test_file_content_2, b""]

    hash_1 = calculate_file_hash(test_file_1)
    hash_2 = calculate_file_hash(test_file_2)

    assert (
        hash_1 != hash_2
    ), "Hash должен быть разным для разных файлов, даже если имя файла одинаковое"
