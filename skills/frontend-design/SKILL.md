---
name: frontend-design
description: 既存の Web サイトやアプリの UI を、機能・情報構造を保ったまま余白・無彩色・1px border・控えめな角丸を基調としたデザインへ差し替えるときに使う。Tailwind CSS と shadcn/ui を前提とする。
---

# Frontend Design

このスキルを使うときは、既存UIの機能、導線、情報構造を保ったまま、視覚表現を `references/design.md` の基準へ差し替える。既存の見た目を微修正するのではなく、色、余白、タイポグラフィ、border、motion、カード表現、画像の扱いを置き換える。

実装前に必ず `references/design.md` を読み、そこに書かれたトークン、サイズ、レイアウト、コンポーネント、モーション、避けることを基準に実装する。Tailwind CSS の設計・トークンは `$tailwind-4-docs` を、shadcn/ui の追加・調整は `$shadcn` を併用する。

## 処理フロー

### 1. 現状分析とトークンマッピング
- 既存の機能、導線、表示テキスト、使用可能な実画像を確認する。
- 既存の CSS custom properties やカラー定義を `references/design.md` のカラートークン（`primary`、`background`、`surface-muted`、`text`、`text-muted`、`border-strong`、`border-subtle`）に対応付ける。
- Tailwind CSS と shadcn/ui の導入状況を確認する。

### 2. トークン・基盤スタイルの適用
- `references/design.md` のカラートークン、フォント、イージングを CSS custom properties または Tailwind v4 `@theme` に定義する。
- フォント CDN（`https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/all.css` 等）を `index.html` または `globals.css` で読み込む。
- Light / Dark モード切替の仕組みと `prefers-color-scheme` 連携を整備する。
- 追加するスタイルは、ページまたはコンポーネントのクラス名にスコープする。

### 3. コンポーネントとレイアウトの段階的差し替え
- **色・面・境界線**: 派手な配色、グラデーション、強い影、太い罫線を排除し、余白・無彩色・1px border・控えめな角丸（`rounded-md` 以下）へ置き換える。
- **タイポグラフィ**: `references/design.md` の `text-h1` 〜 `text-caption` のトークンに置き換える。
- **レイアウト**: コンテナ幅を `max-w-screen-*` に合わせ、モバイルは `px-5`、デスクトップは `px-20`、セクション間は `gap-20`〜`gap-32` の広い余白を取る。一覧は最大2カラムとする。
- **コンポーネント**: shadcn/ui コンポーネントはそのまま使い、見た目はトークン上書きで調整する。アイコンは `lucide` を基本とする。
- **ビジュアル素材**: 抽象的な装飾SVGやオーブ背景を排し、実画像、本文、メタデータを主役にする。

### 4. DESIGN.md の作成・更新
- デザイン差し替え後、作業対象プロジェクトのルートに `DESIGN.md` を作成または更新する。
- 既存の `DESIGN.md` がある場合は新規作成せず、実装後の内容に合わせて更新する。
- `DESIGN.md` には、実際に適用した値、クラス、ルールだけを記録する（未採用の案や未使用トークンは書かない）。

### 5. 検証
- 開発サーバーが必要なアプリではローカル開発サーバーを起動し、静的HTMLの場合はファイルパスを確認する。
- デスクトップ幅（PC: 1280px以上）とモバイル幅（SP: 375px前後）の表示を確認する。
- ブラウザやスクリーンショットで、要素の重なり、文字切れ、コントラスト不足、読みにくい操作部品、欠けた画像、過剰な装飾の残存がないか確認する。

### 6. 完了報告
- 変更したファイル一覧、実施した検証内容、残っている制限事項だけを簡潔に報告する。

## 禁止事項

- `references/design.md` に未定義の色、フォントサイズ、line-height、tracking、weight、container 幅、motion 値の追加。
- `references/design.md` の「避けること」に該当する表現全般。

## DESIGN.md テンプレート

作業対象プロジェクトのルートに作成する `DESIGN.md` は、以下の構成を基本とする。

```markdown
# DESIGN.md

## 色
- `primary`: `#28a8d0` (アクセント・フォーカス)
- `background`: Light `#f2f2f2` / Dark `#121212`
- `surface-muted`: Light `#f0f0f0` / Dark `#161616`
- `text`: Light `#121212` / Dark `#e6e6e6`
- `text-muted`: Light `#8f8f8f` / Dark `#727272`
- `border-strong`: Light `#cccccc` / Dark `#404040`
- `border-subtle`: Light `#e6e6e6` / Dark `#202020`

## タイポグラフィ
- Font Family: `Gen Interface JP`, `Gen Interface JP Display` (CDN: `https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/all.css`)
- 見出し: `text-h1` (SP: 20px / PC: 24px), `text-h2` (SP: 16px / PC: 18px), `text-h3` (SP: 14px / PC: 15px)
- 本文: `text-body1` (13px/14px), `text-body2` (12px/13px), `text-caption` (10px/11px)

## レイアウト
- Container: `max-w-screen-xl` (通常), `max-w-screen-md` (本文・フォーム)
- Padding: SP `px-5` / PC `px-20`
- Spacing: `gap-20` 〜 `gap-32`

## コンポーネント
- Border: 1px border (`border-subtle` / `border-strong`)
- Radius: `rounded-md` 以下
- Icons: `lucide-react`

## モーション
- Easing: `--ease-out` (登場: 0.6s〜1.5s), `--ease-in` (退場: 0.2s〜0.4s), `--ease-in-out` (遷移: 0.2s〜0.3s)

## 実装メモ
- (対象プロジェクトで適用した具体的なCSS設計・スコープ・特記事項)

## 避けること
- (プロジェクト固有の禁止事項や遵守事項)
```
