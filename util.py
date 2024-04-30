import numpy as np

def BZinside(v: float) -> float:
    """入力値を0から1の値に規格化する.
    端は折りたたまれる.

    Args:
        v (float): 入力値

    Returns:
        float: 出力値
    """
    v = np.mod(v, 2)
    if v > 1:
        v = 2 - v
    return v

def rotate_vector(vector: np.ndarray, angle_degrees: float):
    # 角度をラジアンに変換
    angle_radians = np.deg2rad(angle_degrees)

    # 回転行列を作成
    rotation_matrix = np.array([[np.cos(angle_radians), -np.sin(angle_radians)],
                                [np.sin(angle_radians), np.cos(angle_radians)]])

    # ベクトルを回転
    rotated_vector = np.dot(rotation_matrix, vector)

    return rotated_vector
