import unittest
import shutil
import json
from pathlib import Path
from data_manager import DataManager

class TestDataManager(unittest.TestCase):
    def setUp(self):
        # 測試前建立暫存目錄
        self.test_dir = "Test_WorkSnap_Data"
        self.dm = DataManager(base_dir=self.test_dir)

    def tearDown(self):
        # 測試後清理暫存目錄
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)

    def test_directory_creation(self):
        """測試是否正確建立所有預設資料夾"""
        self.assertTrue((Path(self.test_dir) / "Art").exists())
        self.assertTrue((Path(self.test_dir) / "Logs").exists())

    def test_generate_image_path(self):
        """測試圖片路徑生成格式"""
        path = self.dm.generate_image_path("Dev", "Test Project")
        path_str = str(path)
        self.assertIn("Dev", path_str)
        self.assertTrue(path_str.endswith("Test Project.png"))

    def test_save_archive_record(self):
        """測試 JSON 紀錄是否能正確寫入並累加"""
        dummy_data_1 = [{"tag": "Dev", "note": "Test 1"}]
        dummy_data_2 = [{"tag": "Writing", "note": "Test 2"}]
        
        log_file = self.dm.save_archive_record(dummy_data_1)
        self.dm.save_archive_record(dummy_data_2)
        
        import json
        with open(log_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["projects"][0]["note"], "Test 1")
        self.assertEqual(data[1]["projects"][0]["note"], "Test 2")

if __name__ == '__main__':
    unittest.main()