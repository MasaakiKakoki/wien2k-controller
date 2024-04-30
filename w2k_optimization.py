import datetime
import glob
import os
import subprocess

import send_email as se
from WIEN2k_controller import BaseController

class W2kOptimization(BaseController):
    """
    RKmax, lmax, Gmax, k-meshの値を最適化する

    それぞれを(min, max, delta)のようなタプルで指定する。

    optimize関数を呼び出す

    """
    def __init__(self, case):
        super().__init__(case)

        self.rkmax = (7.0, 7.0, 0)
        self.lmax = (10, 10, 0)
        self.gmax = (12, 12, 0)
        self.kmesh = (1000, 1000, 0)

        # scf parameters
        self.cc = 0.001  # charge convergence (e)
        self.ec = 0.0001  # energy convergence (Ry)
        self.i = 40  # max numbar of SCF iterations
        self.ni = 1  # does NOT remove case.broyd*
        # self.soc = 0  # including SOC
        # self.orb = 0

        os.chdir(self.case_path)

    def _make_one_domain(self, t):
        """
        :param t:(min, max, delta)のタプル
        :return: 定義域の値が入ったリスト
        """
        min, max, delta = t[0], t[1], t[2]
        if delta == 0:
            l = [min]
        else:
            l = list(range(min, max + delta, delta))

        return l

    def _make_domains(self):
        self.rkmax_list = self._make_one_domain(self.rkmax)
        self.lmax_list = self._make_one_domain(self.lmax)
        self.gmax_list = self._make_one_domain(self.gmax)
        self.kmesh_list = self._make_one_domain(self.kmesh)

    def _initialization(self, rkmax, lmax, gmax, kmesh):
        """
        イニシャライズを行う関数

        saved file name
        rmax, lmax -> case.in
        gmax -> case.in2
        kmesh -> case.klist
        """

        com_list = ["init_lapw", "-b", "-vxc", "13", "-ecut", "-6",
                    "-rkmax", str(rkmax),
                    "-lmax", str(lmax),
                    "-gmax", str(gmax),
                    "-numk", str(kmesh)]

        if self.spin_pol:
            com_list.insert(2, "-sp")

        print("run " + " ".join(com_list))
        # with open("init_test.txt", mode="w") as f:
        #     f.write("")
        subprocess.run(com_list)

    def _scf(self):
        if self.spin_pol:
            f_com = "runsp_lapw"
        else:
            f_com = "run_lapw"

        com_list = [f_com,
                    "-cc", str(self.cc),
                    "-ec", str(self.ec),
                    "-i", str(self.i)]

        if self.para > 1:
            com_list.append("-p")

        if self.soc:
            com_list.append("-so")

        if self.orb:
            com_list.append("-orb")

        if self.ni:
            com_list.append("-NI")

        print("run " + " ".join(com_list))
        # with open("scf_test.txt", mode="w") as f:
        #     f.write("")
        subprocess.run(com_list)

    def _get_etot(self):
        if os.path.exists("*.scf"):
            with open(self.case + ".scf", "r") as f:
                line_list = f.readlines()
        else:
            with open(self.case + ".scfm", "r") as f:
                line_list = f.readlines()

        for l in line_list:
            l = l.split(" ")
            if l[0] == ":ENE":
                etot = float(l[len(l) - 1])
                break
            else:
                etot =  "NaN"

        return etot

    def _make_summary_text(self, rkmax, lmax, gmax, kmesh, scf_time):
        """
        計算の設定が書かれたテキストファイルを作る
        """
        file_name = "optimization_results.txt"
        text = "==========Settings==========\n"
        text += f"RKmax -> {rkmax}\n"
        text += f"lmax -> {lmax}\n"
        text += f"gmax -> {gmax}\n"
        text += f"k-mesh -> {kmesh}\n\n"
        text += "==========Results==========\n"
        text += f"Total Energy -> {self._get_etot()} Ry\n"
        text += f"Run time -> {scf_time}\n"
        text += "End"

        with open(file_name, mode="w") as f:
            f.write(text)

    def DOS_calculation(self):
        """
        最低限(total)のDOS計算だけを行う。
        """
        run_lapw1 = ['x_lapw', 'lapw1']
        run_lapw2 = ['x_lapw', 'lapw2', '-qtl']
        run_tetra = ['x_lapw', 'tetra']

        if self.parallel > 1:
            run_lapw1.append("-p")
            run_lapw2.append("-p")

        int_list = ["total", "END"]
        if self.spin_pol:
            for spin in ['-up', '-dn']:
                run_lapw1s = run_lapw1 + [spin]
                run_lapw2s = run_lapw2 + [spin]
                run_tetras = run_tetra + [spin]
                print('run ' + ' '.join(run_lapw1s))
                subprocess.run(run_lapw1s)
                print('run ' + ' '.join(run_lapw2s))
                subprocess.run(run_lapw2s)
                print('run ' + ' '.join(['configure_int_lapw', '-b'] + int_list))
                subprocess.run(['configure_int_lapw', '-b'] + int_list)
                print('run ' + ' '.join(run_tetras))
                subprocess.run(run_tetras)
        else:
            print('run ' + ' '.join(run_lapw1))
            subprocess.run(run_lapw1)
            print('run ' + ' '.join(run_lapw2))
            subprocess.run(run_lapw2)
            print('run ' + ' '.join(['configure_int_lapw', '-b'] + int_list))
            subprocess.run(['configure_int_lapw', '-b'] + int_list)
            print('run ' + ' '.join(run_tetra))
            subprocess.run(["x_lapw", "tetra"])

    def _save_all(self, rkmax, lmax, gmax, kmesh):
        """
        case内の全てのファイルを保存する
        """
        files_list = glob.glob("*.*")

        save_dir = f"rk{int(rkmax)}l{int(lmax)}g{int(gmax)}km{int(kmesh)}"
        os.makedirs(save_dir)

        for _f in files_list:
            subprocess.run(["mv", _f, f"{save_dir}/{_f}"])

        print(f"Saved in {save_dir}")

    def _restore_structfile(self, rkmax, lmax, gmax, kmesh):
        """
        .structファイルと.struct_iiファイルだけをcaseに戻す
        """
        struct_file_paths = [f"rk{int(rkmax)}l{int(lmax)}g{int(gmax)}km{int(kmesh)}/{self.case}.struct",
                             f"rk{int(rkmax)}l{int(lmax)}g{int(gmax)}km{int(kmesh)}/{self.case}.struct_ii"]

        for f in struct_file_paths:
            subprocess.run(["cp", f"{f}", ""])

    def optimize(self):
        self._make_domains()
        numofruns = 0
        for _rkmax in self.rkmax_list:
            for _lmax in self.lmax_list:
                for _gmax in self.gmax_list:
                    for _kmesh in self.kmesh_list:
                        if os.path.exists("stop.rtf"):
                            print("Force stop!!!!")
                            exit()

                        subprocess.run(["rm", "-f", "*.broyd*"])
                        self.initialization(_rkmax, _lmax, _gmax, _kmesh)  # イニシャライズ
                        scf_start = datetime.datetime.now()
                        self.scf(econv=self.ec, cconv=self.cc, numofiteration=self.i)  # SCF
                        scf_end = datetime.datetime.now()
                        scf_time = scf_end - scf_start
                        self._make_summary_text(_rkmax, _lmax, _gmax, _kmesh, scf_time)
                        self.DOS_calculation()
                        self._save_all(_rkmax, _lmax, _gmax, _kmesh) # 保存
                        self._restore_structfile(_rkmax, _lmax, _gmax, _kmesh)
                        numofruns += 1


if __name__ == "__main__":

    # .structと.struct_iiを用意しておく。
    def run():
        case = "Nakanishi_Fe4N"
        wo = W2kOptimization(case)
        wo.spin_pol = 1
        wo.parallel = 4
        wo.cc = 0.001
        wo.ec = 0.0001
        wo.i = 80
        wo.rkmax = (9, 9, 0)
        wo.lmax = (10, 10, 0)
        wo.gmax = (12, 12, 0)
        wo.kmesh = (7000, 10000, 1000)
        wo.optimize()

    run()
    # mail = se.EmailFromMac()
    # mail.info_panel()
    # mail.send(run())

    # case = "ohwada_MgSb"
    # wo = W2kOptimization(case)
    # wo.spin_pol = 0
    # wo.parallel = 0
    # wo.DOS_calculation()