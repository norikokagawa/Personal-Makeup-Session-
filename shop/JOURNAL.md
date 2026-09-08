# Journal — 記事の書き方

新しい記事を出すのに、レイアウトを触る必要はありません。
**`assets/js/data/articles.js` に1件追加するだけ**です。

## 手順

1. `assets/js/data/articles.js` を開く
2. 一番上の記事をまるごとコピーする
3. 中身を書き換えて、配列の先頭に置く
4. 保存してpushすれば公開されます

日付順に自動で並ぶので、どこに置いても構いません。

## 項目

| 項目 | 内容 |
|---|---|
| `slug` | URLになります。小文字とハイフンのみ（例 `september-edit`） |
| `title` | 記事タイトル |
| `date` | `'2026-09-05'` の形式 |
| `excerpt` | 1〜2文の要約。一覧カードとニュースレターに使われます |
| `category` | 下記のカテゴリーから1つ |
| `art` | 写真が無いときのイラスト。`{ shape, tone }` |
| `body` | 本文。下記のブロックを並べます |
| `todaysPick` | 商品ID。冒頭に「Today's Pick」として大きく出ます |
| `products` | 商品IDの配列。記事末尾の「Products Mentioned」になります |
| `newsletter` | `true` でニュースレターの下書き対象 |
| `published` | `false` にすると非公開 |

## カテゴリー

`makeup-notes` / `product-edit` / `skincare` / `how-to` /
`seasonal-edit` / `atelierr-picks` / `new-arrivals`

## 本文のブロック

`body` は配列です。上から順に表示されます。

```js
{ p: '段落の文章' }
{ h: '小見出し' }
{ quote: '引用として大きく出したい一文' }
{ list: ['項目1', '項目2'] }
{ steps: ['手順1', '手順2'] }          // 番号付き
{ note: '補足。枠付きで静かに出ます' }
{ shop: ['商品ID', '商品ID'], title: 'Shop This Look' }   // 記事の中に商品カード
{ pick: '商品ID' }                     // 商品1つを大きく
{ image: { shape: 'bottle', tone: 'sand' }, caption: '説明' }
```

`shop` の `title` は自由です。よく使うもの：
`Shop This Look` / `Products Mentioned` / `atelierR Recommends` / `Shop the Products`

## 商品の重複は自動で防がれます

同じ商品を `todaysPick` と本文の両方に書いても、**表示は1回だけ**になります。
記事末尾の「Products Mentioned」も、本文で既に出した商品は自動的に除かれます。

見出しも同様です。本文で `Products Mentioned` を使っていれば、末尾は
`Also in this story` に変わります。「Today's Pick」も1記事に1つだけです。

## 写真

`assets/img/journal/` に `slug と同じ名前.jpg` を置くだけです。
無ければイラストが表示されます。

## 公開したあと

**内部用ページ `studio.html`** に、記事から作られた下書きが並びます。

- **ニュースレター下書き** — 件名・要約・Today's Pick・商品一覧・Read More / Shop Now
- **Instagram** — 短いキャプション / 長いキャプション / ストーリー用 / 記事URL

すべて**コピーするだけの下書き**です。
**このページから送信・投稿されることは一切ありません。** 内容を読んでから、
ご自身でメール配信サービスやInstagramに貼り付けてください。

## ニュースレターの購読者

購読フォームはトップページ・フッター・Journal・注文完了ページにあります。
購読者はデータベースに保存され、`studio.html` の「Subscriber list」から
CSVで取り出せます（先に Order Desk でログインしてください）。

CSVの形式は Mailchimp / Klaviyo / Brevo / Resend がそのまま読み込めるものです。
