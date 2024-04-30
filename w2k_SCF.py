import datetime

import WIEN2k_controller as wc

if __name__ == "__main__":
    # イニシャライズ済のsessionを選ぶ。
    case = "nag_GdAlSi"
    bc = wc.BaseController(case)
    bc.spin_pol = 1  # スピン偏極計算
    bc.parallel = 0

    start = datetime.datetime.now()
    # econv, cconv, numofiterationを変数として設定できる。
    bc.scf()
    end = datetime.datetime.now()
    delta = end - start
    print(f"This calculation takes {delta}.")