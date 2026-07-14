from django.core.management.base import BaseCommand
from logs.models import Problem

TESSOKU_CATEGORIES = {
    # A01-A05: アルゴリズムと計算量
    "tessoku_book_a": "アルゴリズムと計算量",   # A01 The First Problem
    "tessoku_book_b": "アルゴリズムと計算量",   # A02 Linear Search
    "tessoku_book_c": "アルゴリズムと計算量",   # A03 Two Cards
    "tessoku_book_d": "アルゴリズムと計算量",   # A04 Binary Representation 1
    "tessoku_book_e": "アルゴリズムと計算量",   # A05 Three Cards

    # A06-A10: 累積和
    "tessoku_book_f": "累積和",   # A06 How Many Guests?（DB未収録）
    "tessoku_book_g": "累積和",   # A07 Event Attendance
    "tessoku_book_h": "累積和",   # A08 Two Dimensional Sum
    "tessoku_book_i": "累積和",   # A09 Winter in ALGO Kingdom
    "tessoku_book_j": "累積和",   # A10 Resort Hotel

    # A11-A15: 二分探索
    "tessoku_book_k": "二分探索",   # A11 Binary Search 1
    "tessoku_book_l": "二分探索",   # A12 Printer
    "tessoku_book_m": "二分探索",   # A13 Close Pairs
    "tessoku_book_n": "二分探索",   # A14 Four Boxes
    "tessoku_book_o": "二分探索",   # A15 Compression

    # A16-A25: 動的計画法
    "tessoku_book_p": "動的計画法",   # A16 Dungeon 1
    "tessoku_book_q": "動的計画法",   # A17 Dungeon 2
    "tessoku_book_r": "動的計画法",   # A18 Subset Sum
    "tessoku_book_s": "動的計画法",   # A19 Knapsack 1
    "tessoku_book_t": "動的計画法",   # A20 LCS
    "tessoku_book_u": "動的計画法",   # A21 Block Game
    "tessoku_book_v": "動的計画法",   # A22 Sugoroku
    "tessoku_book_w": "動的計画法",   # A23 All Free
    "tessoku_book_x": "動的計画法",   # A24 LIS
    "tessoku_book_y": "動的計画法",   # A25 Number of Routes

    # A26-A35: 数学的問題
    "tessoku_book_z": "数学的問題",    # A26 Prime Check
    "tessoku_book_aa": "数学的問題",   # A27 Calculate GCD（DB未収録）
    "tessoku_book_ab": "数学的問題",   # A28 Blackboard
    "tessoku_book_ac": "数学的問題",   # A29 Power（DB未収録）
    "tessoku_book_ad": "数学的問題",   # A30 Combination
    "tessoku_book_ae": "数学的問題",   # A31 Divisors
    "tessoku_book_af": "数学的問題",   # A32 Game 1
    "tessoku_book_ag": "数学的問題",   # A33 Game 2
    "tessoku_book_ah": "数学的問題",   # A34 Game 3
    "tessoku_book_ai": "数学的問題",   # A35 Game 4

    # A36-A45: 考察テクニック
    "tessoku_book_aj": "考察テクニック",   # A36 Travel
    "tessoku_book_ak": "考察テクニック",   # A37 Travel 2
    "tessoku_book_al": "考察テクニック",   # A38 Black Company 1
    "tessoku_book_am": "考察テクニック",   # A39 Interval Scheduling Problem（DB未収録）
    "tessoku_book_an": "考察テクニック",   # A40 Triangle
    "tessoku_book_ao": "考察テクニック",   # A41 Tile Coloring
    "tessoku_book_ap": "考察テクニック",   # A42 Soccer
    "tessoku_book_aq": "考察テクニック",   # A43 Travel 3
    "tessoku_book_ar": "考察テクニック",   # A44 Change and Reverse
    "tessoku_book_as": "考察テクニック",   # A45 Card Elimination

    # A46-A50: ヒューリスティック
    "tessoku_book_at": "ヒューリスティック",   # A46 Heuristic 1
    "tessoku_book_aw": "ヒューリスティック",   # A49 Heuristic 2
    "tessoku_book_ax": "ヒューリスティック",   # A50 山型足し算（DB未収録）

    # A51-A60: データ構造とクエリ処理
    "tessoku_book_ay": "データ構造とクエリ処理",   # A51 Stack
    "tessoku_book_az": "データ構造とクエリ処理",   # A52 Queue
    "tessoku_book_ba": "データ構造とクエリ処理",   # A53 Priority Queue
    "tessoku_book_bb": "データ構造とクエリ処理",   # A54 Map
    "tessoku_book_bc": "データ構造とクエリ処理",   # A55 Set
    "tessoku_book_bd": "データ構造とクエリ処理",   # A56 String Hash
    "tessoku_book_be": "データ構造とクエリ処理",   # A57 Doubling
    "tessoku_book_bf": "データ構造とクエリ処理",   # A58 RMQ
    "tessoku_book_bg": "データ構造とクエリ処理",   # A59 RSQ
    "tessoku_book_bh": "データ構造とクエリ処理",   # A60 Stock Price

    # A61-A70: グラフアルゴリズム
    "tessoku_book_bi": "グラフアルゴリズム",   # A61 Adjacent Vertices
    "tessoku_book_bj": "グラフアルゴリズム",   # A62 Depth First Search（DB未収録）
    "tessoku_book_bk": "グラフアルゴリズム",   # A63 Shortest Path 1（DB未収録）
    "tessoku_book_bl": "グラフアルゴリズム",   # A64 Shortest Path 2
    "tessoku_book_bm": "グラフアルゴリズム",   # A65 Road to Promotion
    "tessoku_book_bn": "グラフアルゴリズム",   # A66 Connect Query
    "tessoku_book_bo": "グラフアルゴリズム",   # A67 MST
    "tessoku_book_bp": "グラフアルゴリズム",   # A68 Maximum Flow
    "tessoku_book_bq": "グラフアルゴリズム",   # A69 Bipartite Matching
    "tessoku_book_br": "グラフアルゴリズム",   # A70 Lanterns

    # A71-A77: 総合問題
    "tessoku_book_bs": "総合問題",   # A71 Homework
    "tessoku_book_bt": "総合問題",   # A72 Tile Painting
    "tessoku_book_bu": "総合問題",   # A73 Marathon Route
    "tessoku_book_bv": "総合問題",   # A74 Board Game
    "tessoku_book_bw": "総合問題",   # A75 Examination
    "tessoku_book_bx": "総合問題",   # A76 River Crossing
    "tessoku_book_by": "総合問題",   # A77 Yokan Party（DB未収録）

    # B01-B04: アルゴリズムと計算量
    "tessoku_book_bz": "アルゴリズムと計算量",   # B01 A+B Problem
    "tessoku_book_ca": "アルゴリズムと計算量",   # B02 Divisor Check
    "tessoku_book_cb": "アルゴリズムと計算量",   # B03 Supermarket 1
    "tessoku_book_cc": "アルゴリズムと計算量",   # B04 Binary Representation 2

    # B06-B09: 累積和
    "tessoku_book_ce": "累積和",   # B06 Lottery
    "tessoku_book_cf": "累積和",   # B07 Convenience Store 2（DB未収録）
    "tessoku_book_cg": "累積和",   # B08 Counting Points
    "tessoku_book_ch": "累積和",   # B09 Papers

    # B11-B14: 二分探索
    "tessoku_book_cj": "二分探索",   # B11 Binary Search 2
    "tessoku_book_ck": "二分探索",   # B12 Equation
    "tessoku_book_cl": "二分探索",   # B13 Supermarket 2
    "tessoku_book_cm": "二分探索",   # B14 Another Subset Sum

    # B16-B24: 動的計画法
    "tessoku_book_co": "動的計画法",   # B16 Frog 1（DB未収録）
    "tessoku_book_cp": "動的計画法",   # B17 Frog 1 with Restoration
    "tessoku_book_cq": "動的計画法",   # B18 Subset Sum with Restoration
    "tessoku_book_cr": "動的計画法",   # B19 Knapsack 2
    "tessoku_book_cs": "動的計画法",   # B20 Edit Distance
    "tessoku_book_ct": "動的計画法",   # B21 Longest Subpalindrome
    "tessoku_book_cv": "動的計画法",   # B23 Traveling Salesman Problem
    "tessoku_book_cw": "動的計画法",   # B24 Many Boxes

    # B26-B34: 数学的問題
    "tessoku_book_cy": "数学的問題",   # B26 Output Prime Numbers
    "tessoku_book_cz": "数学的問題",   # B27 Calculate LCM
    "tessoku_book_da": "数学的問題",   # B28 Fibonacci Easy（DB未収録）
    "tessoku_book_db": "数学的問題",   # B29 Power Hard
    "tessoku_book_dc": "数学的問題",   # B30 Combination 2
    "tessoku_book_dd": "数学的問題",   # B31 Divisors Hard
    "tessoku_book_de": "数学的問題",   # B32 Game 5
    "tessoku_book_df": "数学的問題",   # B33 Game 6
    "tessoku_book_dg": "数学的問題",   # B34 Game 7

    # B36-B45: 考察テクニック
    "tessoku_book_di": "考察テクニック",   # B36 Switching Lights
    "tessoku_book_dj": "考察テクニック",   # B37 Sum of Digits
    "tessoku_book_dk": "考察テクニック",   # B38 Heights of Grass
    "tessoku_book_dl": "考察テクニック",   # B39 Taro's Job
    "tessoku_book_dm": "考察テクニック",   # B40 Divide by 100
    "tessoku_book_dn": "考察テクニック",   # B41 Reverse of Euclid
    "tessoku_book_do": "考察テクニック",   # B42 Two Faced Cards
    "tessoku_book_dp": "考察テクニック",   # B43 Quiz Contest
    "tessoku_book_dq": "考察テクニック",   # B44 Grid Operations
    "tessoku_book_dr": "考察テクニック",   # B45 Blackboard 2

    # B51-B59: データ構造とクエリ処理
    "tessoku_book_dx": "データ構造とクエリ処理",   # B51 Bracket
    "tessoku_book_dy": "データ構造とクエリ処理",   # B52 Ball Simulation
    "tessoku_book_ea": "データ構造とクエリ処理",   # B54 Counting Same Values
    "tessoku_book_eb": "データ構造とクエリ処理",   # B55 Difference
    "tessoku_book_ec": "データ構造とクエリ処理",   # B56 Palindrome Queries
    "tessoku_book_ed": "データ構造とクエリ処理",   # B57 Calculator
    "tessoku_book_ee": "データ構造とクエリ処理",   # B58 Jumping
    "tessoku_book_ef": "データ構造とクエリ処理",   # B59 Number of Inversions

    # B61-B69: グラフアルゴリズム
    "tessoku_book_eh": "グラフアルゴリズム",   # B61 Influencer
    "tessoku_book_ei": "グラフアルゴリズム",   # B62 Print a Path
    "tessoku_book_ej": "グラフアルゴリズム",   # B63 幅優先探索（DB未収録）
    "tessoku_book_ek": "グラフアルゴリズム",   # B64 Shortest Path with Restoration
    "tessoku_book_el": "グラフアルゴリズム",   # B65 Road to Promotion Hard
    "tessoku_book_em": "グラフアルゴリズム",   # B66 Typhoon
    "tessoku_book_en": "グラフアルゴリズム",   # B67 Max MST
    "tessoku_book_eo": "グラフアルゴリズム",   # B68 ALGO Express
    "tessoku_book_ep": "グラフアルゴリズム",   # B69 Black Company 2

    # C01-C20: 総合問題
    "tessoku_book_ey": "総合問題",   # C01 Tax Rate
    "tessoku_book_ez": "総合問題",   # C02 Two Balls
    "tessoku_book_fa": "総合問題",   # C03 Stock Queries
    "tessoku_book_fb": "総合問題",   # C04 Divisor Enumeration
    "tessoku_book_fc": "総合問題",   # C05 Lucky Numbers
    "tessoku_book_fd": "総合問題",   # C06 Regular Graph
    "tessoku_book_fe": "総合問題",   # C07 ALGO-MARKET
    "tessoku_book_ff": "総合問題",   # C08 ALGO4
    "tessoku_book_fg": "総合問題",   # C09 Taro's Vacation（DB未収録）
    "tessoku_book_fh": "総合問題",   # C10 A Long Grid
    "tessoku_book_fi": "総合問題",   # C11 Election
    "tessoku_book_fj": "総合問題",   # C12 Taro the Novel Writer
    "tessoku_book_fk": "総合問題",   # C13 Select 2
    "tessoku_book_fl": "総合問題",   # C14 Commute Route
    "tessoku_book_fm": "総合問題",   # C15 Many Meetings
    "tessoku_book_fn": "総合問題",   # C16 Flights
    "tessoku_book_fo": "総合問題",   # C17 Strange Data Structure?
    "tessoku_book_fp": "総合問題",   # C18 Pick Two（DB未収録）
    "tessoku_book_fq": "総合問題",   # C19 Gasoline Optimization Problem
    "tessoku_book_fr": "総合問題",   # C20 Mayor's Challenge
}

class Command(BaseCommand):
    def handle(self, *args, **options):
        problems_to_update = []
        not_found = []

        for pid, category in TESSOKU_CATEGORIES.items():
            try:
                problem = Problem.objects.get(problem_id=pid)
                problem.category = category
                problems_to_update.append(problem)
            except Problem.DoesNotExist:
                not_found.append(pid)

        Problem.objects.bulk_update(problems_to_update, ["category"])

        if not_found:
            self.stderr.write(f"DBに存在しない問題: {len(not_found)}件")
            for pid in not_found:
                self.stderr.write(f"  {pid}")

        self.stdout.write(self.style.SUCCESS(f"完了: {len(problems_to_update)}件にカテゴリを設定"))