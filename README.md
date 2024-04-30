# control_WIEN2k

PythonでWIEN2kのシェルコマンドを制御する。  
WIEN2k及びPythonの基礎知識が必要。  
基本的にファイル操作と文字列操作を行っている。  

# 目次
* [使い方](#usage)
* [プログラムとできること](#can)
* [WIEN2kについて](#w2k)
* [メモ](#note)  
    * [並列計算について](#parallel)
    * [計算コマンド](#command)
* [参考](#ref)
* [作成者](#author)

<h1 id="useage">使い方</h1>

ターミナルでWIEN2kを起動。
```bash
% source ~/.bashrc
```
Pythonプログラムを実行。
```bash
% python3 (path to script)
```

<h1 id="can">プログラムとできること</h1>

* __WIEN2k_controller.py__  
WIEN2kの基本操作を行う関数をまとめている。  
基本的に他プログラムで継承して使う。

* __w2k_initialization.py__  
設定に従ってイニシャライズを行う。

* __w2k_SCF.py__  
設定に従ってSCF計算を行う。

* __w2k_mapping.py__  
等エネルギー面を作成するための計算を行う。

* __w2k_band_with_weight.py__  
重みつきバンド計算を設定に従って行う。

* __w2k_optimization.py__ (工事中)  
SCF計算の収束性を確かめるためのプログラム。

* __w2k_with_U.py__  
オンサイトクーロン相互作用を取り入れた計算を行う。  
現在２サイトに入れるようになっている。

* __w2k_remove_files.py__  
caseフォルダ内のファイルを一括削除する。

* __w2k_others.py__  
その他適当に作ったプログラム。

* __send_email.py__  
プログラムが終了したことをメールで通知する。  
使えるが、工事が必要。

<h1 id="w2k">WIEN2kについて</h1>  

* __計算条件設定__  
    * R<sub>mt</sub>K<sub>max</sub>　(default=7.00)  
    case.in1ファイルで設定。  
    最小のマフィンティン半径R<sub>mt</sub>と、その外で平面波により展開される波動関数の最大波数ベクトルK<sub>max</sub>の積。
    この値で平面波の数（行列の大きさ）が決まるため、計算の収束性に最も影響を与える。
    R<sub>mt</sub>は特に変えない限り結晶を構成する元素で自動設定される（StructGenで設定させる）。
    よって、実質K<sub>max</sub>の大きさを決めるパラメータである。
      
    * l<sub>max</sub>　(default=10)   
    case.in1ファイルで設定。  
    LAPW法ではマフィンティン球内で方位角量子数を指数として球面調和関数により展開する。
    このときの最大指数。  
    
    * G<sub>max</sub>　(default=12)   
    case.in1ファイルで設定。  
    マフィンティン球外の電荷密度をフーリエ級数展開する際の指数最大値。
    GGAを使う場合は14などの大い値にする。
    電荷密度の勾配は、この値で決まるメッシュ上で数値計算される。
    
    * k-points　(default=1000)  
    case.klistファイルで設定。  
    ブリリュアンゾーンを分割するk点数。ブリリュアンゾーンが大い物ほど多くとる必要がある。

* __イニシャライズ時に行われること__

    * nn  
    全原子間の距離を最近接距離の2倍まで求める。
    さらに、球体の重なりを確認し、重なった場合はエラーメッセージを出す。
    また、同じ要素が同じ環境を持つかどうか確認し、最終的に等価な集合にまとめ直す。
    
    * sgroup  
    構造を確認し、空間群を決定する。
    対応する空間群のWyckoff位置に加え、等価な原子位置をまとめる。
    さらに、プリミティブセルを確認、決定し必要であれば対応する構造ファイルを作る。
    
    * symmetry  
    空間群の対称操作だけでなく各原子の点群、さらには対応する電荷密度やポテンシャルのためのLM展開を見つける。
    LMはマフィンティン球内の電荷密度を球面調和関数によって展開するときの指数。
    
    * lstart  
    自由原子について球面ディラック方程式を数値的に解き、原子密度を作る。
    原子順位の固有状態を使い、各電子をコアと価電子帯に分類する。
    準コア順位のために局所軌道LOsを自動設定し、エネルギーパラメータE<sub>l</sub>をcase.in1に書き込む。
    この値はSCFサイクル中に最適化される。
    
    * kgen  
    ブリリュアンゾーン内の既約部分において、設定したk-pointsの値に従い等距離のメッシュを作る。
    
    * dstart  
    原子密度を重ね、SCFサイクルのための初期密度を作る。

* __1SCFサイクル時に行われること__

    * lapw0  
    クーロンポテンシャル、交換相関ポテンシャルを電荷密度より計算する。
    
    * lapw1  
    全てのk点について価電子と準コアの固有値及び固有ベクトルを計算する。
    
    * lapw2  
    価電子帯の電荷密度を計算する。
    
    * lcore  
    コアの固有値及び電荷密度を計算する。
    
    * mixer  
    このサイクルで計算されたコアと価電子の密度を足し合わせ、それと１つ前のサイクルで計算されたもののクロネッカー積をとる。
    さらに、原子にかかる力を計算し原子位置を更新する。
    加えてDFT＋Uやオンサイトハイブリット法を使用しているときには、密度行列や軌道ポテンシャルも更新する。
    
    

<h1 id="note">メモ</h1>

<p id="command"><b>計算コマンド</b><br>
ターミナルでWIEN2kを動かすためのshell command。cdコマンドでcaseフォルダに移動する。<br>

【イニシャライズコマンド】<br>
% init_lapw (-options)  
options  
-b : バッチモード。(non-interactive)  
-vxc : 交換相関ポテンシャルの番号。default=13(PBE-GGA)  
-ecut : コアとヴァレンスのエネルギー幅設定。default=-6.0 Ry  
-rkmax : R<sub>mt</sub>K<sub>max</sub>の値。  
-lmax : l<sub>max</sub>の値。  
-gmax : G<sub>max</sub>の値。  
-numk : k-meshの値。
</p>

<p id="parallel"><b>並列計算について</b><br>
.machinesファイル内の「1:localhost」の数がノード数に対応する。
AuのSCF計算を1~6ノードで行ったところ、計算時間は4ノードで最小となった。<br>  
バンド計算は並列化するとむしろ遅くなった。
理由は不明。
ブラウザ上でのパラレル計算は早そう。<br>
DOS計算は並列の環境だとできない。
session_infoで並列計算をやめて、.machinesファイルを削除する必要がある。
</p>

<h1 id="ref">参考</h1>

<a href="https://aip.scitation.org/doi/10.1063/1.5143061" target="_blank">ウィーン工科大学開発グループらによるWIEN2k総説</a>  
<a href="http://susi.theochem.tuwien.ac.at/reg_user/textbooks/DFT_and_LAPW_2nd.pdf" target="_blank">DFTおよび(L)APW法の導入ガイド　</a>  
<a href="https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.77.3865" target="_blank">PBE-GGAの論文　</a>

<h1 id="author">作成者</h1>

* 作成者１ : 大和田 清貴
