import WIEN2k_controller as wc

if __name__ == "__main__":
    # .structと.struct_iiを用意しておく。
    case = "ohwada_Au"
    bc = wc.BaseController(case)
    bc.spin_pol = 0  # スピン偏極計算
    bc.parallel = 4
    # rkmax, lmax, gmax, kmeshの値を変数に設定できる。
    bc.initialization()