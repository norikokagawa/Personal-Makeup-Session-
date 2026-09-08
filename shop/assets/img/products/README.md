# 商品写真の入れ方 / Product photos

ここにファイルを置くだけで、サイトに自動的に反映されます。
コードを触る必要はありません。

## ファイル名のつけ方

商品ごとに決まった名前があります（`商品ID.jpg`）。
一覧は `shop/README.md` を見てください。

    suqqu-signature-color-eyes.jpg      ← メイン写真
    suqqu-signature-color-eyes-2.jpg    ← 2枚目（任意）
    suqqu-signature-color-eyes-3.jpg    ← 3枚目（任意）

- `.jpg` と `.png` が使えます
- 写真が無い商品は、今までどおりイラストが表示されます
- 1枚だけでも大丈夫です

## 写真の目安

- **縦横比** たて4：よこ5 くらい（例 800×1000px）
- **背景** 白・アイボリー・石のような無地
- **明るさ** 自然光。影はやわらかく
- **顔は写さない**（ブランドの方針）
- **容量** 1枚 300KB 以下が目安。大きすぎると表示が遅くなります

Drop a file named after the product id and it replaces the generated artwork
automatically. Missing photos fall back to the generated art, so photos can be
added a few at a time.
