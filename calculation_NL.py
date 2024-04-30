import datetime
import glob
import numpy as np
import os
import re
import subprocess

from email import message
from email.mime.text import MIMEText
import smtplib

from WIEN2k_controller import BaseController


class NLFirstCalculation:
    """
    初めに指定さてた分割数で３D空間を荒く計算する.
    FIRSTCALCFOLDERにstop.rtfを入れるとそのサイクルで終了する。
    """

    def __init__(self, case):
        self.case = case

        self.w2k_path = "/Users/hb_wien2k/WIEN2k/"
        self.case_path = self.w2k_path + self.case + "/"
        self.temp_path = '/usr/local/WIEN2k_19.1/SRC_templates/'  # template file path

        self.para = 1
        self.spol = 0  # spin偏極計算

        os.chdir(self.case_path)

        self.outout_folder_name = FIRSTCALCFOLDER
        os.makedirs(self.outout_folder_name)

    def _make_klist_band(self, kpath: list, d: int):
        """
        .klist_bandを作る

        :param kpath: 一つの.klist_bandファイルで計算するk点(<1)のリスト[[kx, ky, kz], ...]
        :param d: .klist_bandの４番目の数字
        :return:
        """

        output_name = f"{self.case}.klist_band"

        out_ls = []
        tail = '-8.00 8.00'

        for kpi in range(len(kpath)):
            kx = int(round(kpath[kpi][0] * d))
            ky = int(round(kpath[kpi][1] * d))
            kz = int(round(kpath[kpi][2] * d))
            line = ['{:10}'.format(''), '{:5}'.format(kx), '{:5}'.format(ky), '{:5}'.format(kz), '{:5}'.format(d),
                    '  2.0', tail]
            head = ''
            tail = ''
            out_ls.append(line)

        with open(output_name, 'w') as f:
            for lines in out_ls:
                print(''.join(lines), file=f)
            print('END', file=f)

    def _calculate_band(self, spin):  # calculate band dispersion
        """
        _make_klist_bandファイルに従ってバンドを計算する
        .bands.agr or .bandsup.agr and .bandsdn.agrが残る
        """
        spol = self.spol
        p = self.para

        if not os.path.exists(self._filepath('.insp')):  # make .insp file if not exist
            self._set_ef_insp()
            print('.insp file made')

        run_lapw1 = ['x_lapw', 'lapw1', '-band']
        run_spag = ['x_lapw', 'spaghetti']

        if p > 1:
            run_lapw1.insert(2, '-p')
            run_spag.insert(2, '-p')

        # コマンドラインで実行
        if spol:
            for s in spin:
                run_lapw1s = run_lapw1 + [f"-{s}"]
                run_spags = run_spag + [f"-{s}"]

                print('run ' + ' '.join(run_lapw1s))
                subprocess.run(run_lapw1s)

                print('run ' + ' '.join(run_spags))
                subprocess.run(run_spags)
        else:
            print('run ' + ' '.join(run_lapw1))
            subprocess.run(run_lapw1)

            print('run ' + ' '.join(run_spag))
            subprocess.run(run_spag)

    def _save(self, ky, kz, spin):
        """
        .klist_bandと.bands.agrを/kxkykz_{kz}/ky_{ky}に保存する
        """

        klistfol = f"{self.outout_folder_name}/kxkykz_{kz}/klists"
        if not os.path.exists(klistfol):
            os.makedirs(klistfol)

        bandfol = f"{self.outout_folder_name}/kxkykz_{kz}/bands"
        if not os.path.exists(bandfol):
            os.makedirs(bandfol)

        filename = f"ky_{ky}"

        if self.spol:
            subprocess.run(["mv", self._filepath(".klist_band"), f"{klistfol}/{filename}.klist_band"])
            for s in spin:
                subprocess.run(["mv", self._filepath(f".bands{s}.agr"), f"{bandfol}/{filename}{s}.bands.agr"])
        else:
            subprocess.run(["mv", self._filepath(".klist_band"), f"{klistfol}/{filename}.klist_band"])
            subprocess.run(["mv", self._filepath(".bands.agr"), f"{bandfol}/{filename}dn.bands.agr"])

    def _filepath(self, ext):  # return full path of file with extention
        return self.case_path + self.case + ext

    def _cp_from_temp(self, ext):  # copy template file with extension
        subprocess.call(['cp', self.temp_path + 'case' + ext, self.case_path + self.case + ext])

    def _get_ef(self):
        with open(self.case + ".scf2", "r") as f:
            line_list = f.readlines()

        for l in line_list:
            l = l.split(" ")
            if l[0] == ":FER":
                ef = float(l[len(l) - 1])
                break
            else:
                ef = "NaN"

        return ef

    def _set_ef_insp(self):  # set ef parameter for x_lapw spaghetti
        self._cp_from_temp('.insp')
        with open(self._filepath('.insp'), 'r') as f:
            s = f.read()

        s = s.replace('0.xxxx', str(self._get_ef()))

        with open(self._filepath('.insp'), 'w') as f:
            f.write(s)

    def first_calculation(self, d=200, spin = ["up", "dn"]):
        stop_flag = 0
        for kz in range(d+1):
            for ky in range(d+1):
                kpath = [[kx / d, ky / d, kz / d] for kx in range(d+1)]
                self._make_klist_band(kpath=kpath, d=d)
                self._calculate_band(spin)
                self._save(ky, kz, spin)
                if os.path.exists(f"{FIRSTCALCFOLDER}/stop.rtf"):
                    stop_flag = 1
                    break

            if stop_flag:
                break


class NLAnalysisFirstCalculation:
    """
    FIRSTCALCFOLDER内の.bands.agrファイルを解析し、band_indexに指定されたband番号とband番号+1のエネルギー分裂を求める。
    その分裂の大きさが閾値(energy_split_cut)以下である波数点を.klist_bandから抜き出し、.band_agrファイルごとに.npyファイルで保存する。
    """

    def __init__(self, case, band_index):
        self.case = case
        self.band_index = band_index

        self.w2k_path = "/Users/hb_wien2k/WIEN2k/"
        self.case_path = self.w2k_path + self.case

        self.energy_split_cut = 0.01

        os.chdir(f"{self.case_path}/{FIRSTCALCFOLDER}")

    def _load_files(self, ky, kz, spin=""):
        """
        .klist_bandと.band_agrを読みリストを返す
        :return:
        """
        klist_file_path = f"kxkykz_{kz}/klists/ky_{ky}.klist_band"
        with open(klist_file_path, mode="r") as f:
            klist_lines = f.readlines()

        band_file_path = f"kxkykz_{kz}/bands/ky_{ky}{spin}.bands.agr"
        with open(band_file_path, mode="r") as f:
            bands_lines = f.readlines()

        return klist_lines, bands_lines

    def _make_bands_dict(self, klist_lines, band_lines):
        """
        _load_files()で読んだファイルの中身から、kpathと
        band_indexで指定されたバンド番号とひとつインデックスが大いバンドをarrayの形にして辞書型で返す。
        :return: {kpath: array([]), band{band_index}: array([]), band{band_index+1}: array([])}
        """

        bands_dict = {}

        klist_array = np.array([])

        for line in klist_lines:
            _line_nums = re.findall(r"\d+", line)
            _line_array = np.array(_line_nums[:3], dtype=float)
            klist_array = np.append(klist_array, _line_array)

        klist_array = klist_array.reshape(len(klist_lines) - 1, 3)
        bands_dict["kpath"] = klist_array

        bandis = [self.band_index, self.band_index + 1]

        for bandi in bandis:
            for i, line in enumerate(band_lines):
                if "bandindex:" in line:
                    _band_num = float(re.findall(r"\d+", line)[0])
                    if _band_num == bandi:
                        linenum = i
                        break

            _band_array = np.array([])
            for l in band_lines[linenum + 1:]:
                if "&" in l:
                    break
                _eng = float(re.findall(r"[\-]*\d+\.\d+", l)[1])
                _band_array = np.append(_band_array, _eng)

            bands_dict[f"band{bandi}"] = _band_array

        return bands_dict

    def _calc_energy_split(self, bands_dict):
        """
        エネルギー分裂の値をband_dictに追加して返す
        """
        energy_split = bands_dict[f"band{self.band_index + 1}"] - bands_dict[f"band{self.band_index}"]
        bands_dict["engsplit"] = energy_split

        return bands_dict

    def _make_degen_array(self, bands_dict):
        """
        エネルギー分裂がenergy_split_cut以下であるk点をarray型で出力
        """
        degen_klist = np.array([])
        for i, split in enumerate(bands_dict['engsplit']):
            if split <= self.energy_split_cut:
                degen_klist = np.append(degen_klist, bands_dict["kpath"][i])

        degen_klist = degen_klist.reshape((int(degen_klist.shape[0] / 3), 3))

        return degen_klist

    def _save_as_npy(self, ky, kz, degen_klist, spin=""):
        """
        degen_klistsフォルダを作って、縮退しているk点を.npyファイルで保存
        """
        if not os.path.exists(f"kxkykz_{kz}/degen_klists"):
            os.makedirs(f"kxkykz_{kz}/degen_klists")

        save_path = f"kxkykz_{kz}/degen_klists/ky_{ky}{spin}"
        np.save(save_path, degen_klist)

    def do_analysis(self, d=100, spin=[""]):
        """
        外で実行する関数。
        各関数の実行と、縮退している全てのk点が入った.npyファイル、縮退しているk点に１を入れた3Dk空間を見立てたボリュームデータを出力する。
        """
        for s in spin:
            degen_klist_all = np.array([])
            for kz in range(d + 1):
                for ky in range(d + 1):
                    klist_lines, bands_lines = self._load_files(ky, kz, spin=s)
                    bands_dict = self._make_bands_dict(klist_lines, bands_lines)
                    bands_dict = self._calc_energy_split(bands_dict)
                    degen_klist = self._make_degen_array(bands_dict)
                    self._save_as_npy(ky, kz, degen_klist, spin=s)
                    degen_klist_all = np.append(degen_klist_all, degen_klist)

            degen_klist_all = degen_klist_all.reshape((int(degen_klist_all.shape[0] / 3), 3))
            np.save(f"degen_klist_all{self.band_index}{s}", degen_klist_all)

            degen_klist_vol = np.zeros((d + 1, d + 1, d + 1))
            for k in degen_klist_all:
                _kx, _ky, _kz = int(k[0]), int(k[1]), int(k[2])
                degen_klist_vol[_kx, _ky, _kz] = 1
            np.save(f"degen_klist_vol{self.band_index}{s}", degen_klist_vol)


class NLMakeNLKlist:
    """
    NLFirstCalculationの結果をNLAnalysisFirstCalculationで解析して得た縮退点の周りを詳しく計算するためのklist_bandを作る。
    指定された１次元の分割数(<100000)の０が入ったボリュームデータを作り、これの計算したいk点に１を代入する。
    １が入っている点のインデックスをk点として.klist_bandファイルを作る。
    """

    def __init__(self, case, numofk, band_index, spin=""):
        self.case = case
        self.numofk = numofk
        self.margin_size = 20  # 全体の20%の大きさのマージンをつける。
        self.margin = int(self.margin_size / 100 * numofk)
        self.band_index = band_index
        self.spin = spin

        self.w2k_path = "/Users/hb_wien2k/WIEN2k/"
        self.case_path = self.w2k_path + self.case

        os.chdir(self.case_path)

    def _load_degen_klist(self):
        """
        degen_klist_all{self.band_index}{spin}.npyを読み込む。
        degen_klist_vol{self.band_index}{spin}.npyを読み込む。
        :return:
        """
        path = f"{FIRSTCALCFOLDER}/degen_klist_all{self.band_index}{self.spin}.npy"
        degen_klist_all = np.load(path)

        path = f"{FIRSTCALCFOLDER}/degen_klist_vol{self.band_index}{self.spin}.npy"
        degen_klist_vol = np.load(path)

        return degen_klist_all, degen_klist_vol

    def _make_NL_vol(self, degen_klist_all, degen_klist_vol):
        """
        degen_klist_volと同様の位置に１が入ったボリュームデータを作る
        """

        large_vol = np.zeros((self.numofk + 1, self.numofk + 1, self.numofk + 1), dtype="uint8")

        degen_klist_all_ratio = degen_klist_all / degen_klist_vol.shape[0]
        large_klist_all = degen_klist_all_ratio * large_vol.shape[0]

        large_klist_all = large_klist_all.astype(np.int64)

        i = 1
        for _l, _m, _n in zip(large_klist_all.T[0], large_klist_all.T[1], large_klist_all.T[2]):
            print(f"{round(i/degen_klist_all.shape[0] * 100, 2)} %")
            if self._pass_same_value([_l, _m, _n]):
                large_vol = self._make_margin(large_vol, _l, _m, _n)
            i += 1

        if not os.path.exists(f"NL_main/klists{self.band_index}"):
            os.makedirs(f"NL_main/klists{self.band_index}")

        np.save(f"{self.case_path}/NL_main/large_vol", large_vol)

        return large_vol

    def _make_margin(self, large_vol, l, m, n):
        """
        設定したマージンの領域に1を付け足す。
        """
        mar = self.margin
        l0, l1 = self._marge_bound(l, mar, self.numofk)
        n0, n1 = self._marge_bound(n, mar, self.numofk)
        m0, m1 = self._marge_bound(m, mar, self.numofk)

        for _l in range(l0, l1 + 1):
            for _m in range(m0, m1 + 1):
                for _n in range(n0, n1 + 1):
                    large_vol[_l, _m, _n] = 1

        return large_vol

    def _marge_bound(self, i, mar, max):
        """
        0以下やボリュームのサイズを超えるようなインデックスを避ける
        """
        if i - mar >= 0:
            i0 = i - mar
        else:
            i0 = 0

        if i + mar <= max:
            i1 = i + mar
        else:
            i1 = max

        return int(i0), int(i1)

    def _vol_to_klist_band(self, large_vol):
        """
        ボリュームデータの１が入っているインデックスをk点として.klist_bandファイルを作る。
        ひとつの.klist_bandファイルに900点のk点を入れる。
        対体格の点は削除
        """

        _kpath = []
        _numofklist = 0
        for _kz in range(large_vol.shape[2]):
            for _ky in range(large_vol.shape[1]):
                for _kx in range(large_vol.shape[0]):
                    if large_vol[_kx, _ky, _kz] and self._pass_same_value([_kx, _ky, _kz]):
                        _kpath.append([_kx, _ky, _kz])

                        if len(_kpath) == MAXKPOINTS:
                            self._make_klist_band(_kpath, _numofklist, d=int(self.numofk))
                            _numofklist += 1
                            _kpath = []

    def _pass_same_value(self, l):
        return len(list(set(l))) != 1

    def _make_klist_band(self, kpath: list, numofklist, d: int):
        """
        .klist_bandを作る

        :param kpath: 一つの.klist_bandファイルで計算するk点(<1)のリスト[[kx, ky, kz], ...]
        :param d: .klist_bandの４番目の数字
        :return:
        """

        output_name = f"NL_main/klists{self.band_index}/klist{numofklist}.klist_band"

        out_ls = []
        tail = '-8.00 8.00'

        for kpi in range(len(kpath)):
            kx = int(round(kpath[kpi][0]))
            ky = int(round(kpath[kpi][1]))
            kz = int(round(kpath[kpi][2]))
            line = ['{:10}'.format(''), '{:5}'.format(kx), '{:5}'.format(ky), '{:5}'.format(kz), '{:5}'.format(d),
                    '  2.0', tail]
            head = ''
            tail = ''
            out_ls.append(line)

        with open(output_name, 'w') as f:
            for lines in out_ls:
                print(''.join(lines), file=f)
            print('END', file=f)

    def make_NL_klists(self):
        degen_klist_all, degen_klist_vol = self._load_degen_klist()
        large_vol = self._make_NL_vol(degen_klist_all, degen_klist_vol)
        self._vol_to_klist_band(large_vol)


class NLMainCalculation:
    """
    # NLMakeNLKlistで作ったklist_bandファイルにしたがってバンド計算を行う。
    """

    def __init__(self, case, spin):
        self.case = case
        self.spin = spin

        self.para = 1
        self.spol = 0

        self.klists_dir = "NL_main"

        self.w2k_path = "/Users/hb_wien2k/WIEN2k/"
        self.case_path = self.w2k_path + self.case
        self.temp_path = '/usr/local/WIEN2k_19.1/SRC_templates/'  # template file path

        os.chdir(self.case_path)

        self.numofkz = len(glob.glob(f"{self.klists_dir}/kxkykz_*"))
        self.numofky = len(glob.glob(f"{self.klists_dir}/kxkykz_0/klists/ky_*.klist_band"))

    def _copy_klist_to_case(self, i, spin):
        # klist_path = f"{self.case_path}/{self.klists_dir}/kxkykz_{kz}/ky_{ky}{spin}.klist_band"
        klist_path = f"{self.case_path}/{self.klists_dir}/klist_{i}.klist_band"
        subprocess.run(["cp", f"{klist_path}", f"{self.case_path}/{self.case}.klist_band"])

    def _calculate_band(self, spin):  # calculate band dispersion
        """
        .klist_bandファイルに従ってバンドを計算する
        """
        spol = self.spol
        p = self.para

        # if not os.path.exists(self._filepath('.insp')):  # make .insp file if not exist
        #     self._set_ef_insp()
        #     print('.insp file made')

        run_lapw1 = ['x_lapw', 'lapw1', '-band']
        run_spag = ['x_lapw', 'spaghetti']

        if p > 1:
            run_lapw1.insert(2, '-p')
            run_spag.insert(2, '-p')

        # コマンドラインで実行
        if spol:
            run_lapw1s = run_lapw1 + [f"-{spin}"]
            run_spags = run_spag + [f"-{spin}"]

            print('run ' + ' '.join(run_lapw1s))
            subprocess.run(run_lapw1s)

            print('run ' + ' '.join(run_spags))
            subprocess.run(run_spags)
        else:
            print('run ' + ' '.join(run_lapw1))
            subprocess.run(run_lapw1)

    def _filepath(self, ext):  # return full path of file with extention
        return self.case_path + self.case + ext

    def _cp_from_temp(self, ext):  # copy template file with extension
        subprocess.call(['cp', self.temp_path + 'case' + ext, self.case_path + self.case + ext])

    def _get_ef(self):
        with open(self.case + ".scf", "r") as f:
            line_list = f.readlines()

        for l in line_list:
            l = l.split(" ")
            if l[0] == ":FER":
                ef = float(l[len(l) - 1])
                break
            else:
                ef = "NaN"

        return ef

    def _set_ef_insp(self):  # set ef parameter for x_lapw spaghetti
        self._cp_from_temp('.insp')
        with open(self._filepath('.insp'), 'r') as f:
            s = f.read()

        s = s.replace('0.xxxx', str(self._get_ef()))

        with open(self._filepath('.insp'), 'w') as f:
            f.write(s)

    def _save_band(self, i, spin):
        """
        .klist_bandと.bands.agrを/kxkykz_{kz}/ky_{ky}に保存する
        """
        bandfol = f"NL_main/bands"
        if not os.path.exists(bandfol):
            os.makedirs(bandfol)

        filename = f"band_{i}"

        if spin != "":
            subprocess.run(["mv", f"{self.case_path}/{self.case}.bands{spin}.agr", f"{bandfol}/{filename}{spin}.bands.agr"])
        else:
            subprocess.run(["mv", f"{self.case_path}/{self.case}.bands.agr", f"{bandfol}/{filename}.bands.agr"])

    def caluclate_NL(self):
        stop_flag = 0

        numofklists = len(glob.glob(f"{self.klists_dir}/*.klist_band"))

        start = datetime.datetime.now()
        for s in spin:
            for i in range(numofklists):
                self._copy_klist_to_case(i+1, s)
                self._calculate_band(s)
                self._save_band(i+1, s)
                if os.path.exists(f"{FIRSTCALCFOLDER}/stop.rtf"):
                    stop_flag = 1
                    break

            if stop_flag:
                break

        end = datetime.datetime.now()
        delta = end - start

        print(f"End on {end}.")
        print(f"This calculation takes {delta}.")


class NLCalculation(BaseController):

    def __init__(self, case, spin):
        super().__init__(case)
        self.spin = spin

        if spin == [""]:
            self.spin_pol = 0
        else:
            self.spin_pol = 1

        os.chdir(self.case_path)
        print(self.case_path)

    def calculate_NL(self, data_folder: str):
        klist_folder = f"{data_folder}/klists"
        klists = os.listdir(klist_folder)  # get klist file names as list
        klists.sort(reverse=False)
        for klist in klists:
            if "klist_band" in klist:
                # copy klist_band file from klist_folder
                subprocess.run(["cp", f"{klist_folder}/{klist}", f"{self.case}.klist_band"])
                base_name = klist.split(".")[0]

                # out_folder = f"{data_folder}/Bands/{base_name}"
                for spin in self.spin:
                    if self.spin_pol:
                        self._calculate_band_one_spin(spin)
                    else:
                        self.calculate_band_normal()

                self._save_result(data_folder, base_name)

            self.force_stop()

    def _calculate_band_one_spin(self, spin: str):
        """
        一つのスピンに対してバンド計算を行う

        :param spin:
        :return:
        """
        self._make_insp()

        run_lapw1 = ["x_lapw", "lapw1", "-band", f"-{spin}"]
        run_spag = ["x_lapw", "spaghetti", f"-{spin}"]

        if self.parallel > 1:
            run_lapw1.append("-p")
            run_spag.append("-p")

        self._print_command(run_lapw1)
        subprocess.run(run_lapw1)

        self._print_command(run_spag)
        subprocess.run(run_spag)

    def _save_result(self, data_folder: str, base_name: str):
        save_dir = f"{data_folder}/Bands"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        for spin in self.spin:
            subprocess.run(["mv", f"{self.case}.bands{spin}.agr", f"{save_dir}/{base_name}{spin}.bands.agr"])


def set_email(add):
    # self.end = datetime.now()
    # time = self.end - self.start
    # if error == 0:
    #     comment = """
    #         Python said that \"The program was completed!!\"
    #         The program took {0}.
    #         """.format(time)
    # elif error == 1:
    #     comment = """
    #         Python said that \"The program was error stop!!\"
    #         Error message is \n \"{0}\".
    #         """.format(emsg)
    comment = "Finished NL calculation"
    # メッセージ内容
    msg = message.EmailMessage()
    msg = MIMEText(comment)
    msg['Subject'] = 'Notice from your Python program!'
    # msg['From'] = "dayliy.paper.times@gmail.com"
    msg['From'] = "hb_wein2k@gmail.com"
    msg['To'] = add

    # サーバとのやり取り
    smtpobj = smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=10)
    smtpobj.login(msg['From'], "hikaribussei")
    smtpobj.sendmail(msg['From'], msg['To'], msg.as_string())
    smtpobj.close()

    print(f"Send email to {add}")


if __name__ == "__main__":
    FIRSTCALCFOLDER = "NL_firstcalc"
    MAXKPOINTS = 900  # 一つの.klist_bandファイルに入れるk点の数。<1000

    case = "ohwada_FeGa_soc"
    spin = ["dn"]
    band_index = 25

    # calculation first data
    # nlfc = NLFirstCalculation(case)
    # nlfc.spol = 1
    # nlfc.first_calculation(d=100, spin=spin)  # dは分割数の2倍を入れる。101点計算したかったらd=100

    # analysis first data
    # first_calc_d = 100
    # nlanal1st = NLAnalysisFirstCalculation(case, band_index)
    # nlanal1st.energy_split_cut = 0.0003
    # nlanal1st.do_analysis(d=first_calc_d, spin=spin)

    # make klist_band files for main NL calculation
    # This part takes very much time!
    # I must modify this program.
    # numofk = 1000
    # nlmk = NLMakeNLKlist(case, numofk, band_index, spin="dn")
    # nlmk.margin_size = 5
    # nlmk.make_NL_klists()

    # nlmc = NLMainCalculation(case, spin)
    # nlmc.klists_dir = "NL_main/klist5000"
    # nlmc.spol = 1
    # nlmc.caluclate_NL()

    nlc = NLCalculation(case, spin)
    data_folder = "NLs_d50000/NL_25"
    start = datetime.datetime.now()
    nlc.calculate_NL(data_folder)
    end = datetime.datetime.now()
    print(end - start)
    # set_email("ohwadakiyotaka@hiroshima-u.ac.jp")
