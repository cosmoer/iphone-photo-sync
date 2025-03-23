import pytest

def test_main():
    from mtp_file_sync.__main__ import main
    assert main() is None  # 根据实际逻辑调整断言