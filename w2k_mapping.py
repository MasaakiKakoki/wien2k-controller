import datetime
import os
import subprocess
import glob
import util
import numpy as np
from pprint import pprint

from WIEN2k_controller import BaseController
import send_email as se

class W2kMapping(BaseController):
    """
    等エネルギー面を計算するプログラム。
    """
    
    def __init__(self, case):
        super().__init__(case)
        os.chdir(self.case_path)

    def make_klist_folder(self, save_dir: str, kpath: list, denominator: int):
        self.make_klist_band(kpath, denominator)

        numofklists = len(glob.glob(f"{save_dir}/klists/*.klist_band"))

        subprocess.run(["cp", f"{self.case}.klist_band", f"{save_dir}/klists/klist{numofklists}.klist_band"])

    def make_folder(self, save_dir):
        if not os.path.exists(f"{save_dir}/klists"):
            os.makedirs(f"{save_dir}/klists")
            return 0

        elif os.path.exists(f"{save_dir}/klists") and not os.path.exists(f"{save_dir}/Band"):
            from_klists = input("Do you want to calculate from the existing klist_band files. (y/n) : ")
            if from_klists == "y":
                return 1
            else:
                exit()
        else:
            over_write = input(f"{save_dir} exists. Override? (y/n) : ")
            if over_write == "y":
                os.makedirs(f"{save_dir}/klists", exist_ok=True)
            else:
                print("Please change name.")
                exit()

    def calculate_bands_template(self, save_dir, save_name, kpath, denominator):
        self.force_stop()
        self.set_parallel()
        self.make_klist_band(kpath, denominator=denominator)

        if self.spin_pol:
            self.calculate_band_with_spin()
        else:
            self.calculate_band_normal()

        self._save_results_for_map(save_dir, save_name)

    def calculate_bands_from_klistsdir(self, save_dir: str, only_spin=""):

        self.set_parallel()
        numofklists = len(glob.glob(f"{save_dir}/klists/*.klist_band"))
        for i in range(numofklists):
            klist = f"{save_dir}/klists/klist{i}.klist_band"
            self.force_stop()
            print(f"Calculation starts for number {i}")
            self._cp_klist_band(klist)
            if self.spin_pol:
                if self.SOC:
                    self.calculate_band_with_soc()
                else:
                    self.calculate_band_with_spin(only_spin=only_spin)
            elif self.SOC:
                self.calculate_band_with_soc()
            else:
                self.calculate_band_normal()

            self._save_only_bandsagr(f"{save_dir}", f"bands{i}", only_spin=only_spin)

    def _cp_klist_band(self, klist: str):
        """klists_dir内のklistをコピーする。

        :param klists_dir:
        :return:
        """
        subprocess.run(["cp", f"{klist}", f"{self.case}.klist_band"])

    def _save_results_for_map(self, save_dir, save_name):
        """
        .klist_bandと.band.agrを保存する。
        """
        if not os.path.exists(f"{save_dir}/klists"):
            os.makedirs(f"{save_dir}/klists", exist_ok=True)
        subprocess.run(["mv", f"{self.case}.klist_band", f"{save_dir}/klists/{save_name}.klist_band"])
    
        if not os.path.exists(f"{save_dir}/Bands"):
            os.makedirs(f"{save_dir}/Bands")
    
        if self.spin_pol:
            for spin in ["up", "dn"]:
                subprocess.run(["mv", f"{self.case}.bands{spin}.agr", f"{save_dir}/Bands/{save_name}{spin}.bands.agr"])
        else:
            subprocess.run(["mv", f"{self.case}.bands.agr", f"{save_dir}/Bands/{save_name}.bands.agr"])

    def _save_only_bandsagr(self, save_dir, save_name, only_spin=""):
        if not os.path.exists(f"{save_dir}/Bands"):
            os.makedirs(f"{save_dir}/Bands")

        if self.spin_pol:
            if only_spin == "":
                for spin in ["up", "dn"]:
                    subprocess.run(
                        ["mv", f"{self.case}.bands{spin}.agr", f"{save_dir}/Bands/{save_name}{spin}.bands.agr"])
            else:
                subprocess.run(
                    ["mv", f"{self.case}.bands{only_spin}.agr", f"{save_dir}/Bands/{save_name}{only_spin}.bands.agr"])
        else:
            subprocess.run(["mv", f"{self.case}.bands.agr", f"{save_dir}/Bands/{save_name}.bands.agr"])


if __name__ == "__main__":
    case = "rhmnga"
    wm = W2kMapping(case)
    wm.spin_pol = 1  # スピン偏極計算
    wm.SOC = 0
    wm.U = 0

    """
    
    """
    save_dir = "map_XUG_kono_retry"
    denominator = 300  # kx,ky,kzを割り込む値。klist_bandの４行列。
    xug_size = 301  # ひとつのklist_bandファイルで計算するk点の数。
    mapping_direction_size = 301  # 作られるklist_bandファイルの数。
    k3_size = 0

    is_klist = wm.make_folder(save_dir)
    if not is_klist:
        for mapping_direction in range(mapping_direction_size): # 波b
            kpath = [] # klist_bandに入れる波数点を納品するリストを初期化
            for xug in range(xug_size): # 波a
                kab = np.array([xug, mapping_direction]) # 波ベクトルを定義
                kxy = util.rotate_vector(kab, 45) * np.sqrt(2) # 波基底→k基底変換のため、ベクトルを45度回転してルート2倍する
                print(f"rotate {kab} -> {kxy}")
                kpath.append([util.BZinside(kxy[0] / denominator), util.BZinside(kxy[1] / denominator), 1.0]) # 波数てんを納品
            pprint(kpath)
            wm.make_klist_folder(save_dir, kpath, denominator) # kpathからklist_bandファイルへ変換
            print(f"klist_band files are made in {case}/{save_dir}/klists.")

    is_good = input("Are the klist_band files on target? (y/n) : ")

    start = datetime.datetime.now()
    if is_good == "y":
        wm.calculate_bands_from_klistsdir(save_dir, only_spin="")
        end = datetime.datetime.now()
        delta = end - start
        print(f"This calculation takes {delta}.")
    else:
        exit()
    #subprocess.run(["rm", "-r", f"{save_dir}"])
