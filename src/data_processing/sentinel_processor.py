import os
import shutil
from pathlib import Path


class SentinelProcessor:
    def __init__(self, raw_path=None, processed_path=None):
        if raw_path is None:
            self.raw_path = Path(__file__).parents[2] / 'data' / 'raw'
        else:
            self.raw_path = raw_path

        if processed_path is None:
            self.processed_path = Path(__file__).parents[2] / 'data' / 'processed'
        else:
            self.processed_path = processed_path

        self._safe_files = self._find_safe_files

    def _find_safe_files(self):
        dir_in_raw = os.listdir(self.raw_path)
        safe_files = [x for x in dir_in_raw if x.endswith('.SAFE')]
        return safe_files

    def _parse_safe_name(self, safe_name):
        name_components = safe_name.split('_')
        date_time = name_components[2].split('T')
        tile = name_components[5]
        date = date_time[0]
        time = date_time[1]

        return tile, date, time

    def _create_folder(self, tile, date, time):
        Path(self.processed_path / tile / date).mkdir(parents=True, exist_ok=True)

    def _extract_bands(self, safe_file):

        tile, date, time = self._parse_safe_name(safe_file)

        self._create_folder(tile, date, time)

        weird_directory_path = Path(self.raw_path / safe_file / 'GRANULE')

        weird_directory = os.listdir(str(weird_directory_path))

        img_path = str(Path(self.raw_path / safe_file / 'GRANULE' / weird_directory[0] / 'IMG_DATA'))

        target = str(Path(self.processed_path / tile / date))

        shutil.copytree(img_path, target, dirs_exist_ok=True)

    def process_all(self):
        safe_files = self._find_safe_files()
        for safe_file in safe_files:
            self._extract_bands(safe_file)

processor = SentinelProcessor()
processor.process_all()