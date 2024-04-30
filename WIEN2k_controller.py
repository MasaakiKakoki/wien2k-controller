from datetime import datetime
from igorwriter import IgorWave
import numpy as np
import os
import re
import subprocess

class BaseController:
    """
    WIEN2kの基本的なシェルコマンドを制御する。
    """

    def __init__(self, case):
        """
        :param case: セクション名
        """
        self.case = case#.split("/")[-1]

        self.case_path = f"/Users/hb_wien2k/WIEN2k/{case}"
        self.temp_path = "/usr/local/WIEN2k_19.1/SRC_templates/"  # template file path

        self.parallel = 4  # numbar of parallels (on : > 1, off : = 1)

        # 計算の設定
        self.spin_pol = 0  # スピン偏極計算
        self.SOC = 0  # スピン軌道相互作用
        self.U = 0  # オンサイトクーロン相互作用
        self.ni = 1  # does NOT remove case.broyd*

        os.chdir(self.case_path)

    def set_parallel(self):
        """
        並列計算のための関数。
        .machinesファイルをテンプレートからコピーして編集
        :return:
        """
        machines_path = f"{self.case_path}/.machines"
        if self.parallel > 1:
            subprocess.call(["cp", f"{self.temp_path}/.machines", machines_path])

            if self.parallel > 2:
                with open(machines_path, "r") as f:
                    ms = f.read()

                ms = ms.replace("1:localhost\n" * 2, "1:localhost\n" * self.parallel)

                with open(machines_path, "w") as f:
                    f.write(ms)

    def initialization(self, rkmax=7, lmax=10, gmax=12, kmesh=1000):
        """
        イニシャライズを行う。
        % init_lapw -b -vxc 13 -ecut -6 and options...

        #rmax, lmax -> case.in
        #gmax -> case.in2
        #kmesh -> case.klist

        :param rkmax:
        :param lmax:
        :param gmax:
        :param kmesh:
        :param spin_pol:
        :return:
        """

        self.set_parallel()

        com_list = ["init_lapw", "-b", "-vxc", "13", "-ecut", "-6",
                    "-rkmax", str(rkmax),
                    "-lmax", str(lmax),
                    "-gmax", str(gmax),
                    "-numk", str(kmesh)]

        if self.spin_pol:
            com_list.insert(2, "-sp")

        print("run " + " ".join(com_list))
        subprocess.run(com_list)

    def scf(self, econv=0.0001, cconv=0.001, numofiteration=40):
        """
        SCFサイクルを実行する。
        :param econv:エネルギーの収束条件
        :param cconv:電荷の収束条件。なしの時は０を入れる
        :param numofiteration:最大SCFサイクル数
        :return:
        """
        if self.spin_pol:
            f_com = "runsp_lapw"
        else:
            f_com = "run_lapw"

        if cconv != 0:
            com_list = [f_com,
                        "-cc", str(cconv),
                        "-ec", str(econv),
                        "-i", str(numofiteration)]
        else:
            com_list = [f_com,
                        "-ec", str(econv),
                        "-i", str(numofiteration)]

        if self.parallel > 1:
            com_list.insert(1, "-p")

        if self.SOC:
            com_list.append("-so")

        if self.U:
            com_list.append("-orb")

        if self.ni:
            com_list.append("-NI")

        print("Run " + " ".join(com_list))
        subprocess.run(com_list)

    def save_lapw(self, dir_name):
        """
        SCF計算の結果を保存する。
        :return:
        """
        com_list = ["save_lapw", "-d", dir_name]
        subprocess.run(com_list)
        print(f"Save lapw in {dir_name}")

    def make_klist_band(self, kpath: list, denominator: int):
        """
        caseフォルダに.klist_bandファイルを作る
        :param kpath:[[kx, ky, kz],...]
        :param denominator: k点の分母
        :param echo:
        :return:
        """

        out_ls = []
        tail = "-8.00 8.00"

        # print(f"OUTPUT ----> {self.case}.klist_band")

        for kpi in range(len(kpath)):
            kx = int(round(kpath[kpi][0] * denominator))
            ky = int(round(kpath[kpi][1] * denominator))
            kz = int(round(kpath[kpi][2] * denominator))
            line = ["{:10}".format(""), "{:5}".format(kx), "{:5}".format(ky), "{:5}".format(kz), "{:5}".format(denominator),
                    "  2.0", tail]
            head = ""
            tail = ""
            out_ls.append(line)

        with open(f"{self.case}.klist_band", "w") as f:
            for lines in out_ls:
                print("".join(lines), file=f)
            print("END", file=f)

    def calculate_band_normal(self):
        """
        ただのバンドを計算する.
        x_lapw lapw1 [-p] -band
        x_lapw spaghetti [-p]
        :return:
        """

        self._make_insp()

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        run_spag = ["x_lapw", "spaghetti"]

        if self.parallel > 1:
            run_lapw1.append("-p")
            run_spag.append("-p")

        self._print_command(run_lapw1)
        subprocess.run(run_lapw1)
        self._print_command(run_spag)
        subprocess.run(run_spag)

    def calculate_band_with_spin(self, only_spin=""):
        """
        スピン偏極を入れたバンド計算
        x_lapw lapw1 [-p] -band [-up or -dn]
        x_lapw spaghetti [-p] [-up or -dn]
        :return:
        """
        self._make_insp()

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        run_spag = ["x_lapw", "spaghetti"]

        if self.parallel > 1:
            run_lapw1.append("-p")
            run_spag.append("-p")

        if only_spin == "":
            for spin in ["-up", "-dn"]:
                run_lapw1s = run_lapw1 + [spin]

                if self.U:
                    run_lapw1s = run_lapw1s + ["-orb"]

                self._print_command(run_lapw1s)
                subprocess.run(run_lapw1s)

                run_spags = run_spag + [spin]
                self._print_command(run_spags)
                subprocess.run(run_spags)

        else:
            spin = f"-{only_spin}"
            run_lapw1s = run_lapw1 + [spin]
            if self.U:
                run_lapw1s = run_lapw1s + ["-orb"]
            self._print_command(run_lapw1s)
            subprocess.run(run_lapw1s)

            run_spags = run_spag + [spin]
            self._print_command(run_spags)
            subprocess.run(run_spags)

    def calculate_band_with_soc(self):
        """
        SOC付きのバンド計算
        x_lapw lapw1 [-p] -band [-up or -dn]
        x_lapw lapwso [-p] [-up or -dn]
        x_lapw spaghetti [-p] [-up or -dn]
        :return:
        """

        self._make_insp()

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        run_lapwso = ["x_lapw", "lapwso"]
        run_spag = ["x_lapw", "spaghetti", "-so"]

        if self.parallel > 1:
            run_lapw1.insert(2, "-p")
            run_lapwso.insert(2, "-p")
            run_spag.insert(2, "-p")

        if self.spin_pol:
            run_lapw1s = run_lapw1 + ["-up"]
            if self.U:
                run_lapw1s = run_lapw1s + ["-orb"]
            self._print_command(run_lapw1s)
            subprocess.run(run_lapw1s)

            run_lapw1s = run_lapw1 + ["-dn"]
            if self.U:
                run_lapw1s = run_lapw1s + ["-orb"]
            self._print_command(run_lapw1s)
            subprocess.run(run_lapw1s)

            run_lapwso.append("-up")
            self._print_command(run_lapwso)
            subprocess.run(run_lapwso)

            run_spag.append("-up")
            subprocess.run(run_spag)

        else:
            self._print_command(run_lapw1)
            subprocess.run(run_lapw1)

            self._print_command(run_lapwso)
            subprocess.run(run_lapwso)

            self._print_command(run_spag)
            subprocess.run(run_spag)

    def calculate_band_with_orbit(self, outfol, atom_dict):
        """
        サイト毎の電子軌道を含めた計算を行う。
        klist_bandファイルは予め作っておく
        :param outfol: .band.agrファイルを保存するフォルダ
        :param atom_dict: {"atomname": {"atomnum": int, "orbitnum": [], "orbitname": []}, }
        :return:
        """

        if not os.path.exists(f"{outfol}"):
            os.makedirs(f"{outfol}")

        stop_flag = 0
        for _atomname in atom_dict.keys():
            _dict = atom_dict[_atomname]
            _atomnum = _dict["atomnum"]
            for _orbitnum, _orbitname in zip(_dict["orbitnum"], _dict["orbitname"]):
                self._calculate_one_orbit(_atomnum, _orbitnum)
                self._save_orbit_band(outfol, _atomname, _orbitname)

                if os.path.exists(f"{outfol}/stop.rtf"):
                    stop_flag = 1
                    break

            if stop_flag:
                break

        if stop_flag:
            print("Force Stop!")
        else:
            print(f"Output to {outfol}.")

    def calculate_dos(self, outfol, name, int_list=["total", "END"]):
        """
        DOSを計算するための関数。

        :param outfol:
        :param name:
        :param int_list: exmple : int_list = ["total", "1", "tot,d,d-eg,t2g", "2", "tot,s,p", "END"]
        :return:
        """

        if not outfol.startswith(self.case_path):
            outfol = f"{self.case_path}/{outfol}"

        run_lapw1 = ["x_lapw", "lapw1"]
        run_lapw2 = ["x_lapw", "lapw2", "-qtl"]
        run_tetra = ["x_lapw", "tetra"]

        if self.SOC:
            run_lapw2.append("-so")

        if self.U:
            run_lapw1.append("-orb")

        if self.spin_pol:
            for spin in ["-up", "-dn"]:
                run_lapw1 = run_lapw1 + [spin]
                self._print_command(run_lapw1)
                subprocess.run(run_lapw1)

                run_lapw2 = run_lapw2 + [spin]
                self._print_command(run_lapw2)
                subprocess.run(run_lapw2)
        else:
            self._print_command(run_lapw1)
            subprocess.run(run_lapw1)
            self._print_command(run_lapw2)
            subprocess.run(run_lapw2)

        print("run " + " ".join(["configure_int_lapw", "-b"] + int_list))
        subprocess.run(["configure_int_lapw", "-b"] + int_list)

        if self.spin_pol:
            for spin in ["-up", "-dn"]:
                run_tetra = run_tetra + [spin]
                self._print_command(run_tetra)
                subprocess.run(run_tetra)
        else:
            print("run " + " ".join(run_tetra))
            subprocess.run(run_tetra)

        subprocess.call(["mkdir", "-p", outfol])

        if self.spin_pol:
            spin_l = ["up", "dn"]
        else:
            spin_l = [""]

        for s in range(self.spin_pol + 1):
            spin = spin_l[s]
            n = 1
            while 1:
                path = self._filepath(f"dos{str(n)}eV{spin}")
                savepath = f"{outfol}/{name}.dos{str(n)}eV{spin}"
                if os.path.exists(path):
                    subprocess.call(["cp", path, savepath])
                else:
                    break
                n += 1

    def force_stop(self):
        """
        stop.rtfファイルがcaseフォルダにあるとき、計算を強制終了する。
        forサイクルでの計算にいれる。
        :return:
        """
        if os.path.exists(f"stop.rtf"):
            print("Force stop!!!!")
            exit()

    def _calculate_one_orbit(self, atomnum, orbitnum):
        """
        ひとつの軌道を計算する
        x_lapw lapw1 [-p] -band
        x_lapw lapw2 [-p] -band -qtl
        x_lapw spaghetti [-p]
        :param atomnum: 
        :param orbitnum: 
        :return: 
        """
        self._make_insp()

        self._mod_insp_weight(atomnum, orbitnum)

        run_lapw1 = ["x_lapw", "lapw1", "-band"]
        run_lapw2 = ["x_lapw", "lapw2", "-band", "-qtl"]
        run_spag = ["x_lapw", "spaghetti"]

        if self.parallel > 1:
            run_lapw1.insert(2, "-p")
            run_lapw2.insert(2, "-p")
            run_spag.insert(2, "-p")

        # コマンドラインで実行
        if self.spin_pol:
            for spin in ["-up", "-dn"]:
                run_lapw1 = run_lapw1 + [spin]
                run_lapw2 =  run_lapw2 + [spin]
                run_spag = run_spag + [spin]

                self._print_command(run_lapw1)
                subprocess.run(run_lapw1)

                self._print_command(run_lapw2)
                subprocess.run(run_lapw2)

                self._print_command(run_spag)
                subprocess.run(run_spag)
        else:
            self._print_command(run_lapw1)
            subprocess.run(run_lapw1)

            self._print_command(run_lapw1)
            subprocess.run(run_lapw2)

            self._print_command(run_lapw1)
            subprocess.run(run_spag)

    def _mod_insp_weight(self, atom, orb):  # modify insp file
        path = self._filepath("insp")
        print(path)
        with open(path, "r") as f:
            s = f.readlines()

        for l in range(len(s)):
            if "jatom, jcol, size" in s[l]:
                out = s[l].split()
                out[0] = str(atom)
                out[1] = str(orb)
                s[l] = " ".join(out)

        s = "".join(s)

        with open(path, "w") as f:
            f.write(s)

    def _save_orbit_band(self, outfol, atomname, orbitname):
        if self.spin_pol:
            subprocess.run(["mv", self._filepath(".bandsup.agr"), f"{outfol}/{atomname}_{orbitname}up.bands.agr"])
            subprocess.run(["mv", self._filepath(".bandsdn.agr"), f"{outfol}/{atomname}_{orbitname}dn.bands.agr"])
        else:
            subprocess.run(["mv", self._filepath(".bands.agr"), f"{outfol}/{atomname}_{orbitname}.bands.agr"])

    def _filepath(self, ext):
        """
        拡張子から絶対パスに変換
        :param ext: 拡張子
        :return:
        """
        return f"{self.case_path}/{self.case}.{ext}"

    def _cp_from_temp(self, ext):
        """
        指定された拡張子を持つファイルをテンプレートファルダからコピーするs
        :param ext:
        :return:
        """
        subprocess.run(["cp", f"{self.temp_path}/case.{ext}", f"{self.case_path}/{self.case}.{ext}"])

    def _make_insp(self):
        # make .insp file if not exists
        # if not os.path.exists(self._filepath("insp")):
        self._cp_from_temp("insp")
        print(".insp file is copied.")

        with open(f"{self.case}.insp", mode="r") as f:
            l = f.read()

        l = l.replace("0.xxxx", str(self._get_ef()))

        with open(f"{self.case}.insp", mode="w") as f:
            f.write(l)

    #  NOT USED
    def _set_ef_insp(self):  # set ef parameter for x_lapw spaghetti
        """
        .inspファイルにEFを入力する。
        :return:
        """
        self._cp_from_temp("insp")
        with open(self._filepath("insp"), "r") as f:
            s = f.read()

        s = s.replace("0.xxxx", str(self._get_ef()))

        with open(self._filepath(".insp"), "w") as f:
            f.write(s)

    def _get_ef(self):
        """
        .scfファイルからEFを取り出す
        :return: フェルミエネルギー
        """
        with open(f"{self.case}.scf", "r") as f:
            line_list = f.readlines()

        ef = 0
        for l in line_list:
            if ":FER" in l:
                ef = re.findall(r"\d+\.\d+", l)[0]

        return ef

    def _print_command(self, l):
        """
        listをスペースで繋げてプリントする。
        :param l:
        :return:
        """
        print(">>RUN " + " ".join(l))


class W2kTemplates(BaseController):
    """
    テンプレートの関数群
    BaseControllerを継承
    """

    def calculate_band(self, save_dir, save_name, kpath, denominator):
        """
        mappingの計算
        :param save_dir:
        :param save_name:
        :param kpath:
        :param denominator:
        :return:
        """
        self.make_klist_band(kpath, denominator=denominator)

        if self.spin_pol:
            self.calculate_band_with_spin()
        elif self.SOC:
            self.calculate_band_with_soc()
        elif self.U:
            pass
        else:
            self.calculate_band_normal()

        self._save_results_for_map(save_dir, save_name)

    def _save_results_for_map(self, save_dir, save_name):
        """
        .klist_bandと.band.agrを保存する。
        """
        if not os.path.exists(f"{save_dir}/klists"):
            os.makedirs(f"{save_dir}/klists", exist_ok=True)
        subprocess.run(["mv", f"{self.case}.klist_band", f"{save_dir}/klists/{save_name}.klsit_band"])

        if not os.path.exists(f"{save_dir}/Bands"):
            os.makedirs(f"{save_dir}/Bands")

        if self.spin_pol:
            for spin in ["up", "dn"]:
                subprocess.run(["mv", f"{self.case}.bands{spin}.agr", f"{save_dir}/Bands/{save_name}{spin}.bands.agr"])
        else:
            subprocess.run(["mv", f"{self.case}.bands.agr", f"{save_dir}/Bands/{save_name}.bands.agr"])

if __name__ == "__main__":
    case = "ohwada_Au"
    w2ktemp = W2kTemplates(case)