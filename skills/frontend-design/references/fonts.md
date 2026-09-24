# Font setup: Gen Interface JP

本文・ボタン・フォームなどの UI は `Gen Interface JP`、ページ見出しや coss の `font-heading` を使う見出しは `Gen Interface JP Display` を標準にする。文字サイズやウェイトはここでは固定しない。

## 1. CDN から読み込む

Vite などの React アプリでは `index.html` の `<head>`、Next.js ではルートの `app/layout.tsx` の `<head>` に次を一度だけ追加する。

```html
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/all.css" />
```

この CSS は本文用と Display 用のフォントフェイスを含む。実際に使うウェイトのみ読み込む構成にする場合は、同じ CDN の個別 CSS（例: `cdn/400.css`、`cdn/display-400.css`）を選び、必要なウェイトを漏れなく読み込む。

## 2. coss / Tailwind のフォントを差し替える

対象プロジェクトのグローバル CSS で、coss の `@theme inline` にある `--font-sans` と `--font-heading` の定義を次に置き換える。定義がない場合は `@theme` に追加する（既存の定義を重複させない）。色や `--font-mono` の設定はそのまま使う。

```css
@theme inline {
  --font-sans: "Gen Interface JP", sans-serif;
  --font-heading: "Gen Interface JP Display", "Gen Interface JP", sans-serif;
}
```

アプリの `body` に `font-sans` を適用する。通常の見出しは `font-heading` を使う。coss が Dialog などのタイトルに使う `font-heading` も上の設定で切り替わる。

```tsx
<body className="font-sans">{children}</body>
```

`@coss/style` で追加された Inter の `next/font` 変数クラス（例: `fontSans.variable`、`fontHeading.variable`）が `html` や `body` に残っている場合は外し、フォント指定が競合しないようにする。モノスペース用の既存設定は必要なら維持する。

## 3. 表示を確認する

日本語と英数字を含む実際の見出し・本文・ボタンで、フォントが読み込まれ、`font-sans` と `font-heading` がそれぞれ意図したファミリーになっているかを確認する。CDN を使えない環境ではフォントをローカル配信し、同じファミリー名とトークンを適用する。
