import json
from typing import Dict, List, Tuple
import copy
from pathlib import Path


class VideoDataHarmonizer:
    def __init__(self, source_file: str, target_file: str):
        self.source_file = source_file
        self.target_file = target_file
        self.source_data: Dict = {}
        self.target_data: List = []
        self.harmonized_data: List = []

    def read_files(self) -> None:
        """优雅地读取源文件和目标文件"""
        with open(self.source_file, 'r', encoding='utf-8') as f:
            self.source_data = json.load(f)

        with open(self.target_file, 'r', encoding='utf-8') as f:
            self.target_data = json.load(f)

    def find_video_by_size(self, file_size: int) -> Tuple[str, dict]:
        """在源数据中寻找特定大小的视频，如同在繁星中寻找某颗明星"""
        for video_name, video_info in self.source_data.items():
            if video_info.get('file_size') == file_size:
                return video_name, video_info
        return None, None

    def harmonize_data(self) -> None:
        """协调两个数据集之间的关系，创造完美的和谐"""
        self.harmonized_data = copy.deepcopy(self.target_data)

        for idx, entry in enumerate(self.harmonized_data):
            for video_idx, file_size in enumerate(entry['file_size']):
                video_name, video_info = self.find_video_by_size(file_size)

                if video_name and video_info:
                    self.harmonized_data[idx]['videos'][video_idx] = video_name
                    self.harmonized_data[idx]['rating'][video_idx] = video_info['rating']

    def save_harmonized_data(self) -> None:
        """将和谐后的数据优雅地保存到新文件"""
        output_file = Path(self.target_file).stem + '_harmonized.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(self.harmonized_data, f, indent=2, ensure_ascii=False)


def main():
    """主程序，如同一位优雅的指挥家"""
    import sys

    if len(sys.argv) != 3:
        print("使用方式: python compare.py first_file.json second_file.json")
        return

    harmonizer = VideoDataHarmonizer(sys.argv[1], sys.argv[2])
    harmonizer.read_files()
    harmonizer.harmonize_data()
    harmonizer.save_harmonized_data()
    print("✨ 数据协调已完成，新的和谐已经诞生 ✨")


if __name__ == "__main__":
    main()
