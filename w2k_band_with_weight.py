import os
import subprocess

from WIEN2k_controller import BaseController


class CaluculateWithOrbit(BaseController):
    def calculate_band_with_orbit(self, outfol, atom_dict, do_lapw=True):
        """
        サイト毎の電子軌道を含めた計算を行う。
        klist_bandファイルは予め作っておく。
        初めにlapwを計算し、その後.inspファイルの編集とspaghettiを設定された軌道に対して繰り返す。

        :param outfol: .band.agrファイルを保存するフォルダ
        :param atom_dict: {"atomname": {"atomnum": int, "orbitnum": [], "orbitname": []}, }
        :param do_lapw: lapw計算をするかどうか
        :return:
        """

        if not os.path.exists(f"{outfol}"):
            os.makedirs(f"{outfol}")

        if do_lapw and self.SOC:
            self._do_lapw_soc()

        if do_lapw:
            self._do_lapw()

        for _atomname in atom_dict.keys():
            _dict = atom_dict[_atomname]
            _atomnum = _dict["atomnum"]
            for _orbitnum, _orbitname in zip(_dict["orbitnum"], _dict["orbitname"]):
                self._mod_insp_weight(_atomnum, _orbitnum)
                self._do_spaghetti()
                self._save_orbit_band(outfol, _atomname, _orbitname)

                self.force_stop()

        print(f"Output to {outfol}.")

    def _do_lapw(self):
        if not os.path.exists(self._filepath("insp")):  # make .insp file if not exist
            self._set_ef_insp()
            print(".insp file made")

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        if self.SOC:
            run_lapwso = ["x_lapw", "lapwso"]
        run_lapw2 = ["x_lapw", "lapw2", "-band", "-qtl"]

        if self.parallel > 1:
            run_lapw1 = run_lapw1 + ["-p"]
            run_lapw2 = run_lapw2 + ["-p"]

        # コマンドラインで実行
        if self.spin_pol:
            for s in ["up", "dn"]:
                run_lapw1s = run_lapw1 + [f"-{s}"]

                print("run " + " ".join(run_lapw1s))
                subprocess.run(run_lapw1s)

                if self.SOC:
                    run_lapwsos = run_lapwso + [f"-{s}"]

            for s in ["up", "dn"]:
                run_lapw2s = run_lapw2 + [f"-{s}"]

                print("run " + " ".join(run_lapw2s))
                subprocess.run(run_lapw2s)

        else:
            print("run " + " ".join(run_lapw1))
            subprocess.run(run_lapw1)

            print("run " + " ".join(run_lapw2))
            subprocess.run(run_lapw2)

    def _do_lapw_soc(self):
        if not os.path.exists(self._filepath("insp")):  # make .insp file if not exist
            self._set_ef_insp()
            print(".insp file made")

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        run_lapwso = ["x_lapw", "lapwso", "-up"]
        run_lapw2 = ["x_lapw", "lapw2", "-band", "-qtl", "-up"]

        if self.parallel > 1:
            run_lapw1 = run_lapw1 + ["-p"]
            run_lapwso = run_lapwso + ["-p"]
            run_lapw2 = run_lapw2 + ["-p"]

        for s in ["up", "dn"]:
            run_lapw1s = run_lapw1 + [f"-{s}"]

            print("run " + " ".join(run_lapw1s))
            subprocess.run(run_lapw1s)

        print("run " + " ".join(run_lapwso))
        subprocess.run(run_lapwso)

        print("run " + " ".join(run_lapw2))
        subprocess.run(run_lapw2)

    def _do_spaghetti(self):
        run_spag = ["x_lapw", "spaghetti"]

        if self.parallel > 1:
            run_spag = run_spag + ["-p"]

        spin_list = ["up", "dn"]

        if self.SOC:
            run_spag = run_spag + ["-so"]
            spin_list = ["up"]

        # コマンドラインで実行
        if self.spin_pol:
            for s in spin_list:
                run_spags = run_spag + [f"-{s}"]
                print("run " + " ".join(run_spags))
                subprocess.run(run_spags)
        else:
            print("run " + " ".join(run_spag))
            subprocess.run(run_spag)

    def _save_orbit_band(self, outfol, atomname, orbitname):
        if self.spin_pol: # スピン偏極計算の場合
            subprocess.run(["mv", self._filepath("bandsup.agr"), f"{outfol}/{atomname}_{orbitname}up.bands.agr"]) # .bandsup.agrのファイルの名前を変えて出力用フォルダに移動する
            subprocess.run(["mv", self._filepath("bandsdn.agr"), f"{outfol}/{atomname}_{orbitname}dn.bands.agr"]) # .bandsdn.agrについて同様
        else: # すぴん偏極ない場合
            subprocess.run(["mv", self._filepath("bands.agr"), f"{outfol}/{atomname}_{orbitname}.bands.agr"])

if __name__ == "__main__":
    # klist_bandファイルは予め作っておく
    case = "Kakoki_Fe4N"
    cw = CaluculateWithOrbit(case)
    cw.spin_pol = 1
    cw.parallel = 1
    cw.SOC = 0
    # atom_dict = {"atomname": {"atomnum": int, "orbitnum": [], "orbitname": []}, }
    atom_dict = {#"Fe1": {"atomnum": 1, "orbitnum": [1, 5, 6, 7, 8, 9], "orbitname": ["tot", "DZ2", "DX2Y2", "DXY", "DXZ", "DYZ"]},
                 "Fe2": {"atomnum": 2, "orbitnum": [7, 8, 9, 10 ], "orbitname": [ "DZ2", "DXY", "DX2Y2", "DXZ+DYZ"]}}
                 #"Ga": {"atomnum": 3, "orbitnum": [1, 2, 3], "orbitname": ["tot", "s", "p"]}}
    cw.calculate_band_with_orbit(outfol="orbitalGM", atom_dict=atom_dict, do_lapw=True)
