# import datetime
import os
import subprocess

# from WIEN2k_controller import BaseController
from w2k_band_with_weight import CaluculateWithOrbit


class W2kMappingWithWeight(CaluculateWithOrbit):

    def __init__(self, case: str):
        """
        指定した波数面に対して、軌道の重みを付けたエネルギー固有値を計算する。
        :param case: session name

        """
        super().__init__(case)

        # self.data_folder = ""
        # self.klist_folder = ""

        os.chdir(self.case_path)

    def make_map(self, data_folder: str, atom_dict):
        """
        :param data_folder: 計算に使用するklistフォルダが入っているフォルダ
        :param base_name: output file name finally named kz_{num}.bands.agr
        :return:
        """
        klist_folder = f"{data_folder}/klists"
        klists = os.listdir(klist_folder)  # get klist file names as list
        klists.sort(reverse=False)
        for klist in klists:
            if "klist_band" in klist:
                # copy klist_band file from klist_folder
                subprocess.run(["cp", f"{klist_folder}/{klist}", f"{self.case}.klist_band"])
                base_name = klist.split(".")[0]

                # print(klist, base_name)
                out_folder = f"{data_folder}/Bands/{base_name}"
                self.calculate_band_with_orbit(outfol=out_folder, atom_dict=atom_dict, do_lapw=True)

            if os.path.exists("stop.rtf"):
                print("Force stop!!")
                exit()

        self._organize_folders(data_folder, klists)

    def _organize_folders(self, data_folder: str, klists):
        # print(klists)
        for klist in klists[1:]:
            if "klist_band" in klist:
                base_name = klist.split(".")[0]
                band_list = os.listdir(f"{data_folder}/Bands/{base_name}")
                # print(base_name, band_list)
                # break
                for bands in band_list:
                    if self.spin_pol:
                        orb = bands.split(".")[0][:-2]
                        self._make_orb_folder(data_folder, orb)
                        if "up" in bands:
                            spin = "up"
                        else:
                            spin = "dn"
                        subprocess.run(["cp", f"{data_folder}/Bands/{base_name}/{bands}",
                                        f"{data_folder}/{orb}/{base_name}{spin}.bands.agr"])
                    else:
                        orb = bands.split(".")[0]
                        self._make_orb_folder(data_folder, orb)
                        subprocess.run(["cp", f"{data_folder}/Bands/{base_name}/{bands}",
                                        f"{data_folder}/{orb}/{base_name}.bands.agr"])

    def _make_orb_folder(self, data_folder, orb):
        orb_fol = f"{data_folder}/{orb}"
        if not os.path.exists(orb_fol):
            os.makedirs(orb_fol)


if __name__ == "__main__":
    mww = W2kMappingWithWeight("ohwada_FeGa")
    mww.spin_pol = 1
    # atom_dict = {"atomname": {"atomnum": int, "orbitnum": [], "orbitname": []}, }
    atom_dict = {"Fe1": {"atomnum": 1, "orbitnum": [1, 5, 6, 7, 8, 9],
                         "orbitname": ["tot", "DZ2", "DX2Y2", "DXY", "DXZ", "DYZ"]},
                 "Fe2": {"atomnum": 2, "orbitnum": [1, 5, 6, 7, 8, 9],
                         "orbitname": ["tot", "DZ2", "DX2Y2", "DXY", "DXZ", "DYZ"]},
                 "Ga": {"atomnum": 3, "orbitnum": [1, 2, 3], "orbitname": ["tot", "s", "p"]}}
    mww.make_map(data_folder="orbit_map_GXkz", atom_dict=atom_dict)
    mww.make_map(data_folder="orbit_map_GKXkz", atom_dict=atom_dict)
