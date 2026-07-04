---
name: frontend-design
description: 既存の Web サイトやアプリの UI を、機能・情報構造を保ったまま余白・無彩色・1px border・控えめな角丸を基調としたデザインへ差し替えるときに使う。Tailwind CSS と shadcn/ui を前提とする。
---

# Frontend Design

このスキルを使うときは、既存UIの機能、導線、情報構造を保ったまま、視覚表現を `references/design.md` の基準へ差し替える。既存の見た目を微修正するのではなく、色、余白、タイポグラフィ、border、motion、カード表現、画像の扱いを置き換える。

`references/design.md` を必ず読み、そこに書かれたトークン、サイズ、レイアウト、コンポーネント、モーション、避けることを基準に実装する。

基本実装は Tailwind CSS と shadcn/ui を使う。Tailwind CSS の設計・トークン・utility の扱いは `$tailwind-4-docs` を、shadcn/ui の追加・調整・修正は `$shadcn` を併用する。

## 実装前に確認すること

- 既存の機能、導線、表示情報を確認する。
- 置き換える対象の色、余白、タイポグラフィ、border、radius、shadow、背景、motion を確認する。
- 既存の CSS custom properties を `references/design.md` の role に対応づける。
- 既存のページまたはコンポーネントのクラス命名を確認する。
- Tailwind CSS と shadcn/ui の導入状況を確認する。
- Tailwind CSS や shadcn/ui の具体的な使い方が必要な場合は、該当スキルを併用する。
- 使用できる実画像、プロジェクト画像、本文、メタ情報を確認する。

## 実装ルール

- 既存の機能、導線、情報構造は保つ。
- 既存の配色、影、装飾背景、カード表現、強いアクセントは `references/design.md` の内容へ置き換える。
- `references/design.md` にない色、フォントサイズ、line-height、tracking、weight、container 幅、motion 値は追加しない。
- CSS custom properties は、`primary`、`background`、`surface-muted`、`text`、`text-muted`、`border-strong`、`border-subtle` を基準に整理する。
- 追加するスタイルは、ページまたはコンポーネントのクラス名にスコープする。
- タイポグラフィは `references/design.md` の `text-h1`、`text-h2`、`text-h3`、`text-body1`、`text-body2`、`text-caption` に置き換える。
- レイアウトは `references/design.md` の Tailwind 前提に合わせる。
- 色、罫線、装飾を足す前に、余白と無彩色の面で階層を作る。
- 作品画像、実画像、本文、メタ情報を主要なビジュアル素材として使う。

## 禁止

- `references/design.md` にないアクセントカラー。
- `references/design.md` にないフォントサイズ。
- `references/design.md` にない背景階層。
- `references/design.md` の「避けること」に該当する表現。

## Tailwind CSS / shadcn/ui

- Tailwind CSS の設計・トークン・utility の扱いで迷う場合は `$tailwind-4-docs` を使う。
- shadcn/ui の追加・調整・修正で迷う場合は `$shadcn` を使う。
- このスキルには Tailwind CSS や shadcn/ui の細かい使い方を増やさない。

## DESIGN.md

- デザイン差し替え後、作業対象プロジェクトのルートに `DESIGN.md` を作成または更新する。
- 既存の `DESIGN.md` がある場合は新規作成せず、実装後の内容に合わせて更新する。
- `DESIGN.md` には、実際に適用した値とルールだけを書く。
- 見出しは、`色`、`タイポグラフィ`、`レイアウト`、`コンポーネント`、`モーション`、`実装メモ`、`避けること` を基本にする。
- `references/design.md` の内容をそのまま写すのではなく、対象プロジェクトに実際に入れた値とクラスに合わせて書く。
- 実装していないコンポーネント、使っていないトークン、未採用の案は書かない。
- 不必要なキャプションやサブセクションは追加しない。

基本の雛形:

```md
# DESIGN.md

## 色

## タイポグラフィ

## レイアウト

## コンポーネント

## モーション

## 実装メモ

## 避けること
```

## 検証

- 開発サーバーが必要なアプリでは、実装後にローカル開発サーバーを起動し、URLを伝える。
- 静的HTMLだけで動く場合は、ローカルファイルのパスを伝える。
- 重要なフロントエンド変更の後は、ブラウザで確認する。
- デスクトップ幅とモバイル幅を1つ以上ずつ確認する。
- スクリーンショットで、重なり、文字切れ、読みにくい操作部品、欠けた画像、配色の偏りを確認する。

## 完了報告

変更したファイル、実施した検証、残っている制限事項だけを報告する。
