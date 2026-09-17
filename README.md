# AtCoder Tracker

AtCoderの提出履歴とAtCoder Problemsの公開データを取り込み、常設教材と開催コンテストを分けて学習状況を確認するDjangoアプリケーションです。

- デモ（ログイン不要）: https://atcoder-tracker-8ag0.onrender.com/demo/
- トップページ: https://atcoder-tracker-8ag0.onrender.com/

> 無料ホスティングのため、初回アクセス時はサーバー起動に時間がかかる場合があります。

## 主な機能

- AtCoderユーザー名を使った提出履歴の同期
- 分野別・難易度帯別の成績表示
- 常設教材ごとの問題数、着手数、AC数、達成率表示
- 常設教材内の問題検索、状態絞り込み、鉄則A・B・Cの切り替え
- 開催コンテストをアルゴリズム、ヒューリスティック、グランドに分けて表示
- AHC本編とAHC形式（AHC以外）の分離
- コンテスト結果の新しい順・古い順切り替え
- コンテストごとの問題表の折りたたみ
- デイリートレーニング、未AC、後でやる問題の一覧
- 問題単位の「後でやる」登録・解除
- AtCoderの問題ページへの直接リンク
- ログイン不要のデモ画面

## 画面構成

| 画面 | 内容 |
| --- | --- |
| ダッシュボード | 分野別と難易度別の集計をタブで表示。難易度別にはAC率グラフを表示 |
| 常設 | 8種類の常設教材をカード形式で表示 |
| 常設教材詳細 | 検索、状態絞り込み、教材内セクション切り替えができる問題表 |
| コンテスト | アルゴリズム、ヒューリスティック、グランドを切り替えて表示 |
| デイリー | AtCoder Daily Trainingの問題一覧 |
| 未AC | 提出済みでACしていない問題の一覧 |
| 後でやる | ユーザーが登録した問題の一覧 |

問題一覧の表記は次に統一しています。

`問題 / 問題名 / 分野 / 難易度 / 状態 / 後でやる / 開く`

## 技術スタック

| レイヤー | 採用技術 |
| --- | --- |
| バックエンド | Python / Django 6 |
| フロントエンド | React 19 / TypeScript / Vite / Material UI |
| HTMLの入口 | Django Template |
| データベース | PostgreSQL（本番: Neon）/ SQLite（開発・テスト） |
| 外部データ | AtCoder Problems API |
| インフラ | Render + Neon |
| 静的ファイル | WhiteNoise |

## アーキテクチャ

DjangoのURL、認証、View、モデルは維持し、操作性が必要な画面だけをReactで描画する段階的な構成です。SPAにはしていません。

1. Django Viewがユーザー別の集計を行う
2. Django Templateが`json_script`でデータを安全に埋め込む
3. Reactが該当ページのルート要素へ画面を描画する
4. 「後でやる」などの更新は既存のDjango URLへPOSTする

Reactのソースは`frontend/`、Viteの出力先は`logs/static/logs/react/`です。生成物はGit管理せず、ローカルまたはデプロイ時にビルドします。

## データモデルの役割

| モデル | 役割 |
| --- | --- |
| `Problem` | 問題名、代表コンテストID、分野、難易度など問題そのものの情報 |
| `Contest` | 開催枠の名称、日時、シリーズ、形式、常設判定 |
| `ContestProblem` | コンテストと問題の多対多関係。常設教材の掲載問題判定にも使用 |
| `Log` | ユーザーと問題単位の集約済み学習状態 |
| `ContestAttempt` | ユーザーがどの開催枠で提出したかを保持 |
| `DoLater` | ユーザーが後で解く問題として登録した状態 |

同じ問題が複数の教材や開催枠に属する可能性があるため、問題所属は`Problem.contest_id`だけで決めず、`ContestProblem`を使用します。一方、ユーザーが実際に提出した開催枠は`ContestAttempt.submitted_contest_id`で管理します。

## コンテスト分類

### 常設教材

次の8個のIDを明示的に常設として扱います。

| ID | 表示名 |
| --- | --- |
| `practice` | practice contest |
| `APG4b` | C++入門 APG4b |
| `APG4bPython` | Python入門 APG4bPython |
| `abs` | AtCoder Beginners Selection |
| `practice2` | AtCoder Library Practice Contest |
| `typical90` | 競プロ典型90問 |
| `math-and-algorithm` | アルゴリズムと数学 演習問題集 |
| `tessoku-book` | 競技プログラミングの鉄則 |

鉄則は常設教材に含め、問題番号からA・B・Cを別セクションとして判定します。

### 開催コンテスト

- `abcNNN`、`arcNNN`、`agcNNN`、`ahcNNN`は完全一致の正規表現で判定
- AHCは`AHC`シリーズとして扱う
- AtCoder公式データでヒューリスティックと判定され、AHC IDではないものは`AHC形式（AHC以外）`として扱う
- AGCは画面上の「グランド」に表示
- AHCとAHC形式は画面上の「ヒューリスティック」に表示
- それ以外の通常開催枠は「アルゴリズム」に表示
- ADTは専用のデイリー画面に表示

分類ロジックは`logs/contest_classification.py`に集約しています。

## セットアップ

### 必要環境

- Python 3.12以上
- Node.js 20以上
- PostgreSQLまたはSQLite

### Windows

```powershell
git clone https://github.com/shimu2233/atcoder-tracker.git
cd atcoder-tracker

py -m venv atcodervenv
.\atcodervenv\Scripts\Activate.ps1
pip install -r requirements.txt

cd frontend
npm.cmd ci
npm.cmd run build
cd ..

py manage.py migrate
py manage.py fetch_problems
py manage.py runserver
```

ブラウザで`http://127.0.0.1:8000/`を開きます。

### macOS / Linux

```bash
git clone https://github.com/shimu2233/atcoder-tracker.git
cd atcoder-tracker

python -m venv atcodervenv
source atcodervenv/bin/activate
pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..

python manage.py migrate
python manage.py fetch_problems
python manage.py runserver
```

### フロントエンド開発

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

Viteの生成物はDjangoの静的ファイルとして読み込まれます。Reactソースを変更した後は`npm.cmd run build`を再実行してください。

## 管理用コマンド

| コマンド | 説明 |
| --- | --- |
| `py manage.py fetch_problems` | 問題、コンテスト、コンテストと問題の関係を取得・更新 |
| `py manage.py fetch_submissions <username>` | 指定ユーザーの提出履歴を取得・更新 |
| `py manage.py set_categories` | 対象問題へ分野を設定 |
| `py manage.py create_default_tags` | 初期タグを作成 |

## デプロイ

`build.sh`は次の順番で実行します。

1. Python依存関係をインストール
2. `npm ci`でフロントエンド依存関係をインストール
3. ViteでReactをビルド
4. `collectstatic`を実行
5. マイグレーションを適用

## テスト

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
py manage.py test

cd frontend
npm.cmd run typecheck
```

## 外部データについて

本アプリは[AtCoder Problems](https://kenkoooo.com/atcoder/)が公開するAPIとデータを利用します。取得処理ではページネーションとリクエスト間隔を考慮しています。

## 変更内容レポート

現在の構成へ変更した内容は[`docs/implementation-change-report.pdf`](docs/implementation-change-report.pdf)にまとめています。
