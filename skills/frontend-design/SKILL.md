---
name: frontend-design
description: React、Tailwind CSS v4、coss ui、Gen Interface JP で Web サイトやアプリを作成・改修するときに使う。スタックの導入と、coss が定めないページの組版・掲載内容の方針を扱う。
---

# Frontend Design

React + Tailwind CSS v4 + coss ui を使う。作業前にインストール済みの `$tailwind-4-docs` と `$coss` を読み込み、導入やコンポーネントの実装はそれぞれのスキルに従う。shadcn CLI や既存 shadcn/ui の調整には必要に応じて `$shadcn` を使う。

## このスキルで決めること

- **導入方針**: 新規プロジェクトは coss のスタイルプリセットから始める。既存プロジェクトは既存のテーマとコンポーネントを確認し、必要なものだけ追加する。
- **フォント**: 本文・UI は Gen Interface JP、見出しは Gen Interface JP Display。CDN と coss のフォント変数の設定は `references/fonts.md` に従う。coss プリセットの Inter が残って競合しないようにする。
- **ページ設計**: `references/design.md` に従い、画面の用途に必要な内容と優先順位、ページの組版・コンテンツ幅・セクションの配置を決める。操作画面ではキャッチコピーや自明な機能説明を足さない。

coss のテーマやコンポーネントに既定値がある色・角丸・部品内の文字サイズ・余白は、このスキルのトークンで上書きしない。
