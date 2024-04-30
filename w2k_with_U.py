import os
import subprocess

from WIEN2k_controller import BaseController
import send_email as se

class CalculationWithU(BaseController):
    """
    LDA + U計算用のプログラム
    :param udict: {"atomname": ("atomnum", (min, max, delta)), ...}
    """
    def __init__(self, case):
        super().__init__(case)

        self.U = 1

        os.chdir(self.case_path)

    def calculate_scf_with_U(self, udict):
        """
        LDA + U計算用のプログラム
        イニシャライズをやっておく
        あらかじめ.klist_bandを作っておく
        :param udict: {"atomname": (atomnum, (min, max, delta)), ...}
        :return:
        """

        domain_list = self._make_u_lists(udict)

        _atom1 = list(udict.keys())[0]
        _atom2 = list(udict.keys())[1]

        for _u1 in domain_list[0]:
            for _u2 in domain_list[1]:
                subprocess.run(["rm", "-f", "*.broyd*"])
                self._modify_inorb([_u1, _u2])
                self._modify_indm()
                self._remove_lapw()
                print(f"Start SCF with {_atom1} = {_u1} and {_atom2} = {_u2}")
                self.scf()
                self._make_insp()
                name = f"{_atom1}_{_u1}_{_atom2}_{_u2}"
                self._save_lapw(name)
                self._cp_results(name)
                print("Start band calculation.")
                self._calculate_band()
                self._save_band(name)
                # print("Start DOS calculation.")
                # self.DOS_calculation()
                # self._save_dos(name)
                self._remove_lapw()

                if os.path.exists("stop.rtf"):
                    print("Froce stop!!")
                    exit()

    def _make_u_lists(self, udict):
        domain_list = []
        for _atom in udict.keys():
            _domain = self._make_domain(udict[_atom][1])
            domain_list.append(_domain)

        return domain_list

    def _make_domain(self, tap):
        """
        (min, max, delta) -> [min,...,max+1]
        """
        min, max, delta = tap[0], tap[1], tap[2]

        if not delta:
            domain = [min]
        else:
            domain = range(min, max + delta, delta)
            # domain = [0, 0.5, 1]

        return domain

    def _modify_inorb(self, ulist):
        self._cp_from_temp("inorb")

        with open(f"{self.case_path}/{self.case}.inorb", mode="r") as f:
            lines = f.readlines()

        lines[2] = "  1 1 2                          iatom nlorb, lorb\n"
        lines[3] = "  3 1 2                          iatom nlorb, lorb\n"

        n = 0
        for i, l in enumerate(lines):
            if "0.52" in l:
                _U = self._ev2ry(ulist[n])
                l_split = l.split()
                l_split[0] = str(_U)
                lines[i] = " ".join(l_split) + "\n"
                n += 1

        # lines = lines.replace("0.52", str(self._ev2ry(_u1)))
        # lines = lines.replace("0.52", str(self._ev2ry(_u2)))
        text = "".join(lines)
        with open(f"{self.case_path}/{self.case}.inorb", mode="w") as f:
            f.write(text)

    def _modify_indm(self):
        self._cp_from_temp("indm")
        with open(f"{self.case_path}/{self.case}.indm", mode="r") as f:
            lines = f.readlines()

        lines[2] = " 1  1  2      index of 1st atom, number of L's, L1\n"
        lines[3] = " 3  1  2      ditto for 2nd atom, repeat NATOM times\n"

        text = "".join(lines)
        with open(f"{self.case_path}/{self.case}.indm", mode="w") as f:
            f.write(text)

    def _remove_lapw(self):
        subprocess.run(["rm", "-f", "*.broyd*"])

    def _ev2ry(self, ev):
        return ev / 13.6058

    def _calculate_band(self):
        run_lapw1 = ['x_lapw', 'lapw1', '-band', "-orb"]
        run_spag = ['x_lapw', 'spaghetti', "-orb"]

        if self.spin_pol:
            for spin in ["-up", "-dn"]:
                run_lapw1 += [spin]
                run_spag += [spin]

                subprocess.run(run_lapw1)
                subprocess.run(run_spag)
        else:
            subprocess.run(run_lapw1)
            subprocess.run(run_spag)

    def _save_band(self, name):
        dir = "Bands"
        if not os.path.exists(dir):
            os.makedirs(dir)

        if self.spin_pol:
            for spin in ["up", "dn"]:
                subprocess.run(["cp", f"{self.case}.bands{spin}.agr", f"{dir}/{name}{spin}.bands.agr"])
        else:
            subprocess.run(["cp", f"{self.case}.bands.agr", f"{dir}/{name}.bands.agr"])

    def _save_lapw(self, name):
        com_list = ["save_lapw", "-d", name]
        subprocess.run(com_list)
        print(f"Save lapw in {name}")

    def _cp_results(self, name):
        subprocess.run(["cp", f"{name}/*", "."])

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

    def _save_dos(self, name: str):
        dir = "DOSs"
        if not os.path.exists(dir):
            os.makedirs(dir)

        if self.spin_pol:
            for spin in ["up", "dn"]:
                subprocess.run(["cp", f"{self.case}.dos1ev{spin}", f"{dir}/{name}{spin}.dos1ev"])
        else:
            subprocess.run(["cp", f"{self.case}.dos1ev", f"{dir}/{name}.dos1ev"])



if __name__ == "__main__":
    # イニシャライズをやっておく
    # あらかじめ.klist_bandを作っておく
    # _modify_inorbと_modify_indmを編集して
    def run():
        case = "Nakanishi_Co2FeSi"
        udict = {"Fe": (1, (0, 5, 1)),
                 "Co": (3, (0, 5, 1))}
        withu = CalculationWithU(case)
        withu.spin_pol = 1
        withu.parallel = 4
        withu.calculate_scf_with_U(udict)

    run()
    # mail = se.EmailFromMac()
    # mail.info_panel()
    # mail.send(run())