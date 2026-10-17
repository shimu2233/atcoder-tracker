# AtCoder Tracker

AtCoderの提出履歴とAtCoder Problemsの公開データを取り込み、学習状況を確認するDjangoアプリケーションです。

- 公開URL: https://atcoder-tracker-8ag0.onrender.com/
- 本番DB: PostgreSQL（Neon）
- 開発・テストDB: SQLite

## 主な機能

- AtCoderユーザー名を使った提出履歴の同期
- 難易度帯別のAC状況表示
- 常設教材ごとの問題数、着手数、AC数、達成率表示
- コンテストをアルゴリズム、ヒューリスティック、グランドに分類
- デイリートレーニング、未AC、後でやる問題の一覧
- 問題検索、状態絞り込み、並べ替え
- 期間・コンテスト種別・難易度・問題数を指定した目標設定
- ログイン後の各画面上部に目標進捗を最大3件表示（ホームを除く）

目標進捗は、目標期間内（日本時間）にACした問題を、目標ごとに1問1件の`GoalAC`として記録して計算します。過去にAC済みの問題でも期間内に再ACすれば対象になり、期間外に再ACしても既存の目標の記録は維持します。進捗を最新にするには、上部の「AtCoderデータを同期」を実行してください。

同期はユーザーごとに1つまで実行でき、開始から5分間は再実行できません。通信失敗時もこの間隔は維持されます。初回は全履歴、以降は取得済みの最新提出時刻の1時間前から取得します。新しい目標がある場合は、その開始日まで範囲を広げて一度確認します。提出履歴・目標のAC記録・取得位置はまとめて保存し、失敗時には更新を取り消します。

この更新を適用する際、既存の初回ACから分かる目標進捗は移行します。取得位置は0から始め、次の同期で全履歴を確認して再ACも反映します。新しい目標を作った直後の進捗は、次の同期で反映されます。

過去の提出を再取得する場合は、次を実行します。5分制限は適用されます。再ジャッジによるAC取り消しの反映は行わず、観測済みのACを維持します。

```powershell
python manage.py fetch_submissions アプリのユーザー名 --full
```

APIに現れた提出の問題情報が未登録の場合は、取得位置を進めず同期を中止します。管理者が`python manage.py fetch_problems`を実行して問題情報を更新した後、再同期してください。取得範囲より古い遅延反映は通常の差分同期では拾えないため、必要な場合は`--full`を使用します。

設定でAtCoderユーザー名を変更すると、古い提出履歴（`Log`・`ContestAttempt`）と目標のAC記録を削除し、取得位置・成功日時・目標の初回確認状態・達成日時をリセットします。目標設定・後でやる問題・5分制限用の開始時刻は維持します。同期実行中は名前を変更できません。

サーバーの強制終了後などに実行中状態が残った場合は、対象の同期プロセスが停止済みであることを確認して、次を実行します。引数はAtCoder名ではなく、このアプリのユーザー名です。開始時刻・提出履歴は変更しません。

```powershell
python manage.py reset_submission_sync アプリのユーザー名 --confirm-stopped
```

同時実行・名前変更との競合を検証するテストはPostgreSQL向けです。SQLiteでテストを実行すると、この2件はスキップされます。

## 画面構成

| 画面 | 内容 |
| --- | --- |
| ホーム | ログイン、新規登録への入口 |
| ダッシュボード | 難易度別の集計とAC率 |
| 常設 | 常設教材の進捗と問題一覧 |
| コンテスト | 種別・シリーズごとのコンテストと問題一覧 |
| デイリー | AtCoder Daily Trainingの問題一覧 |
| 未AC | 提出済みでACしていない問題 |
| 後でやる | 登録した問題の一覧 |
| 目標設定 | 目標の作成、進捗確認、削除 |
| 設定 | AtCoderユーザー名などの変更 |

## 技術構成

- Backend: Python 3.14 / Django 6
- Frontend: React 19 / TypeScript / Vite / Material UI
- Database: PostgreSQL / SQLite
- Static files: WhiteNoise
- Hosting: Render / Neon

Django Templateを入口にし、操作性が必要な画面だけをReactで描画しています。Reactのソースは`frontend/`、ビルド先は`logs/static/logs/react/`です。

## セットアップ

必要なもの:

- Python 3.14
- Node.js 20以上

### Windows

```powershell
py -m venv atcodervenv
.\atcodervenv\Scripts\Activate.ps1
python -m pip install -r requirements.txt

cd frontend
npm.cmd ci
npm.cmd run build
cd ..

python manage.py migrate
python manage.py fetch_problems
$env:DEBUG='True'
python manage.py runserver
```

### macOS / Linux

```bash
python -m venv atcodervenv
source atcodervenv/bin/activate
python -m pip install -r requirements.txt

cd frontend
npm ci
npm run build
cd ..

python manage.py migrate
python manage.py fetch_problems
DEBUG=True python manage.py runserver
```

ブラウザで http://127.0.0.1:8000/ を開きます。

`DEBUG=True`はローカル起動プロセスだけに設定してください。`DEBUG=False`でローカル起動する場合は、先に次を実行します。

```powershell
python manage.py collectstatic --noinput
```

## 環境変数

ローカルでは`.env`を利用できます。秘密情報をGitへコミットしないでください。

| 変数 | 用途 | 本番での扱い |
| --- | --- | --- |
| `SECRET_KEY` | Djangoの署名鍵 | 必須。秘密値を設定 |
| `DEBUG` | デバッグ表示 | `False`または未設定 |
| `ALLOWED_HOSTS` | 許可するホスト名 | カンマ区切りで設定 |
| `DATABASE_URL` | DB接続先 | Neon PostgreSQLのURLを設定 |

`settings.py`の`DEBUG`既定値は`False`です。`DATABASE_URL`が未設定の場合はローカルの`db.sqlite3`を使用します。

## テスト

バックエンド:

```powershell
$env:DATABASE_URL='sqlite:///:memory:'
.\atcodervenv\Scripts\python.exe manage.py test
```

フロントエンド:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

## デプロイ

`build.sh`は次の処理を行います。

1. Python依存関係をインストール
2. Node.js依存関係をインストール
3. Reactをビルド
4. `collectstatic`を実行
5. DBマイグレーションを適用

本番では`DEBUG=False`にし、`SECRET_KEY`、`ALLOWED_HOSTS`、`DATABASE_URL`をホスティング環境の変数として設定してください。

## 外部データ

本アプリは[AtCoder Problems](https://kenkoooo.com/atcoder/)が公開するAPIとデータを利用します。
