import glob
import os
import send2trash

class W2kRemoveFiles:

    def __init__(self, case):
        self.case = case

        self.case_path = f"/Users/hb_wien2k/WIEN2k/{self.case}"

        self.remain_files_ext = []

        os.chdir(self.case_path)

    def remove_files(self):
        files = self._get_files()
        for remove_file in files:
            if self._remove_flag(remove_file):
                send2trash.send2trash(remove_file)

    def _get_files(self):
        return glob.glob("*")

    def _remove_flag(self, file):
        if "." in file:
            ext = file.split(".")[1]
            if ext not in self.remain_files_ext:
                return 1
        elif ":" in file:
             return 1
        else:
            return 0


if __name__ == "__main__":
    case = "ohwada_Au"
    wrf = W2kRemoveFiles(case)
    wrf.remain_files_ext = ["struct", "struct_ii"]
    wrf.remove_files()
    # print(wrf._get_files())