# Design

洗練された、静かな、編集的な、ポートフォリオ的な、ギャラリー的な、読み物中心の、画像主導の、またはミニマルなフロントエンドへ差し替えるときに使用する。余白、無彩色、繊細な輪郭、控えめなモーションによって、作品や実コンテンツへ視線を導く。

## 原則

1. 罫線や色面ではなく、余白で階層を作る。
2. 無彩色で奥行きを作り、彩度は意味のある合図にだけ使う。
3. 影よりも輪郭を優先し、控えめな角丸と 1px border を使う。
4. 動きは静かにする。fade、blur、緩やかな上昇だけを使う。

## カラートークン

Light と Dark の2モードを使う。純白と純黒は避ける。`primary` は両モードで同じ値にし、唯一の彩度のあるアクセントとして扱う。

| Role | Light | Dark |
| :--- | :--- | :--- |
| `primary` | `#28a8d0` | `#28a8d0` |
| `background` | `#f2f2f2` | `#121212` |
| `surface-muted` | `#f0f0f0` | `#161616` |
| `text` | `#121212` | `#e6e6e6` |
| `text-muted` | `#8f8f8f` | `#727272` |
| `border-strong` | `#cccccc` | `#404040` |
| `border-subtle` | `#e6e6e6` | `#202020` |

### CSS 変数 / Tailwind v4 `@theme` 定義例

```css
@theme {
  --color-primary: var(--primary);
  --color-background: var(--background);
  --color-surface-muted: var(--surface-muted);
  --color-text: var(--text);
  --color-text-muted: var(--text-muted);
  --color-border-strong: var(--border-strong);
  --color-border-subtle: var(--border-subtle);

  --font-sans: 'Gen Interface JP', -apple-system, BlinkMacSystemFont, sans-serif;
  --font-display: 'Gen Interface JP Display', 'Gen Interface JP', sans-serif;
}

:root {
  --primary: #28a8d0;
  --background: #f2f2f2;
  --surface-muted: #f0f0f0;
  --text: #121212;
  --text-muted: #8f8f8f;
  --border-strong: #cccccc;
  --border-subtle: #e6e6e6;

  /* shadcn/ui mapping */
  --foreground: var(--text);
  --card: var(--surface-muted);
  --card-foreground: var(--text);
  --popover: var(--surface-muted);
  --popover-foreground: var(--text);
  --muted: var(--surface-muted);
  --muted-foreground: var(--text-muted);
  --border: var(--border-subtle);
  --input: var(--border-strong);
  --ring: var(--primary);
}

.dark {
  --primary: #28a8d0;
  --background: #121212;
  --surface-muted: #161616;
  --text: #e6e6e6;
  --text-muted: #727272;
  --border-strong: #404040;
  --border-subtle: #202020;
}
```

- アクセントカラーは `primary` だけにする。
- 塗りの面より、1px border を優先する。
- 背景階層は `background` と `surface-muted` までにする。
- Dark では、border を背景より一段だけ明るくする。
- モード切替はユーザーが操作できるボタンで行い、初期状態は `prefers-color-scheme` を基準にする。
- ユーザーが選択したモードは保持し、再訪時にも反映する。

## タイポグラフィ

- 本文とUIテキストには `Gen Interface JP` を使う。
- `h1`、`h2`、`h3` には `Gen Interface JP Display` を使う。
- `Gen Interface JP` と `Gen Interface JP Display` は CDN から取得する。
  - `https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/all.css`
  - `https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/400.css`
  - `https://cdn.jsdelivr.net/npm/gen-interface-jp@0.8.0/cdn/display-400.css`
- サイズトークンは Tailwind の `md` breakpoint、768px で切り替える。
- 中間サイズは追加しない。小さな階層差が必要な場合は weight で調整する。

| Token | SP | PC | Line | Tracking | Weight | Font Family | 用途 |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `text-h1` | 20px | 24px | 1.5 | `0` | 500 | Display | ページまたはヒーロー見出し |
| `text-h2` | 16px | 18px | 1.5 | `0` | 500 | Display | セクション見出し |
| `text-h3` | 14px | 15px | 1.5 | `0` | 500 | Display | 小見出し |
| `text-body1` | 13px | 14px | 1.75 | `0` | 400 | Sans | 読み物本文 |
| `text-body2` | 12px | 13px | 1.75 | `0` | 400 | Sans | UI既定、補助本文 |
| `text-caption` | 10px | 11px | 1.5 | `0` | 400 | Sans | キャプション、ラベル、注釈 |

## コンポーネント

基本的に Tailwind CSS と shadcn/ui を使う。

- shadcn/ui のコンポーネントはそのまま使い、見た目はトークン上書きで変更する。
- 見た目を変える必要がある場合は、まず CSS 変数またはプロジェクトのトークン定義を調整する。
- SVGアイコンは、基本的に `lucide` を使う。
- `lucide` に該当アイコンがない場合だけ、既存のアイコンセットまたは最小限の独自SVGを使う。
- Light / Dark の切り替えボタンを用意し、現在の状態が分かるラベルまたは `aria-label` を付ける。
- カードは、反復項目、モーダル、明確に枠が必要なツールにだけ使う。
- 角丸は `rounded-md` 以下（4px〜6px）を基本にする。
- メディア、カード、ボタンを過度に丸めない。
- hover は色、border、opacity の微差に留める。
- 強い拡大、回転、派手な shadow、派手な transform を hover に使わない。

## レイアウト

- コンテナ幅は Tailwind の breakpoint に合わせる。
- `sm`: 640px、`md`: 768px、`lg`: 1024px、`xl`: 1280px、`2xl`: 1536px を基準にする。
- 通常のページコンテナは `max-w-screen-xl` を基本にする。
- 作品一覧や広い管理画面は `max-w-screen-2xl` まで広げてよい。
- 読み物や設定フォームなどの細い本文領域は `max-w-screen-md` を使う。
- パディングはモバイルで `px-5`、デスクトップで `px-20` を使う。
- 一覧は最大 2 カラムまでにする。
- セクション間には、通常 `gap-20` から `gap-32` の広い余白を使う。
- 線、塗り、装飾を追加する前に、余白で領域を分ける。

## モーション

次の easing トークンを使う。

| Token | Curve | 用途 |
| :--- | :--- | :--- |
| `--ease-in` | `cubic-bezier(0.4, 0, 1, 1)` | 退場、fade-out |
| `--ease-out` | `cubic-bezier(0, 0, 0.2, 1)` | 登場、fade-in、開く、scroll-in |
| `--ease-in-out` | `cubic-bezier(0.4, 0, 0.2, 1)` | 位置と状態の遷移 |

- 退場には 0.2s から 0.4s を使う。
- 登場には 0.6s から 1.5s を使う。
- 状態変化には 0.2s から 0.3s を使う。
- 強い transform は避ける。opacity、軽い blur、緩やかな上昇だけを使う。

## コンテンツ・テキスト

- コピーは簡潔で編集的に保ち、体験の中に説明的なUIテキストを置きすぎない。
- テキストは、ラベル、見出し、短い補足に留める。
- 作品、商品、人物、場所などが主題の場合は、抽象的な装飾ではなく実画像を優先する。
- 具体的な視覚対象を、抽象SVG装飾で置き換えない。

## 避けること

- 強い影とネオモーフィズム。
- グラデーション背景、オーブ背景。
- 1px より太い罫線。
- 3層以上の入れ子カード。
- 複数のアクセントカラー。
- 3カラム以上の一覧。
- 純白 `#ffffff` と純黒 `#000000`。
- 内容のない抽象SVG装飾。
- 操作説明や機能説明の常設。
