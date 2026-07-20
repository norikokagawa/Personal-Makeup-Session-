// ===================================================
//  STORES 予約 → 決済案内メール 自動送信
//  Personal Makeup Session Sydney
// ===================================================

// 処理済みメールに付けるGmailラベル名
var PROCESSED_LABEL = 'STORES-送信済み';

// STORESの予約通知メールを検索するクエリ
var SEARCH_QUERY = 'from:hello@stores.jp subject:"予約が入りました" is:unread -label:' + PROCESSED_LABEL;

// ======================
//  メイン処理（自動実行）
// ======================
function processStoresReservations() {
  var label = getOrCreateLabel(PROCESSED_LABEL);
  var threads = GmailApp.search(SEARCH_QUERY);

  if (threads.length === 0) return;

  threads.forEach(function(thread) {
    thread.getMessages().forEach(function(message) {
      if (!message.isUnread()) return;

      var body = message.getPlainBody();

      // シドニーの予約のみ対象（シンガポール・福岡などはスキップ）
      if (body.indexOf('Sydney') === -1) return;

      var name  = extractName(body);
      var email = extractEmail(body);

      if (!email) {
        Logger.log('メールアドレスが見つかりません: ' + message.getSubject());
        return;
      }
      if (!name) {
        Logger.log('名前が見つかりません。メールアドレスのみで送信: ' + email);
        name = 'Guest';
      }

      var firstName = resolveFirstName(name);
      sendPaymentEmail(firstName, email);

      message.markRead();
      thread.addLabel(label);
      Logger.log('送信完了: ' + firstName + ' <' + email + '>');
    });
  });
}

// ========================
//  決済案内メールを送信
// ========================
function sendPaymentEmail(firstName, toEmail) {
  var subject = 'Personal Makeup Session Sydney — Payment Information';
  var body = [
    'Hi ' + firstName + ',',
    '',
    'Thank you for your booking for the Personal Makeup Session in Sydney.',
    '',
    'To confirm your reservation, please complete your payment by 12:00 pm (noon) tomorrow via PAY ID below.',
    '',
    'Amount: AUD 311',
    'PAY ID: 0404485393',
    '',
    'Please note that your reservation will be automatically cancelled if payment is not received by 12:00 pm (noon) tomorrow.',
    '',
    'Once the payment is completed, please reply to this email with a screenshot of the transfer confirmation.',
    '',
    'Looking forward to welcoming you in Sydney ✨',
    '',
    'atelierR'
  ].join('\n');

  GmailApp.sendEmail(toEmail, subject, body);
}

// ========================
//  メールアドレスを抽出
// ========================
function extractEmail(body) {
  var m = body.match(/[\w.+%-]+@[\w.-]+\.[a-zA-Z]{2,}/);
  return m ? m[0].toLowerCase() : null;
}

// ========================
//  名前を抽出
// ========================
function extractName(body) {
  var lines = body.split('\n').map(function(l) { return l.trim(); });

  // STORESメールの「◆予約者:」ラベルを探す
  for (var i = 0; i < lines.length; i++) {
    if (/[◆◇●]?\s*(予約者|お名前|氏名)\s*[：:]/.test(lines[i])) {
      // ラベルと同じ行に名前がある場合
      var inline = lines[i].replace(/.*[：:]/, '').trim();
      if (inline.length > 1) return inline;
      // 次の行に名前がある場合
      if (i + 1 < lines.length && lines[i + 1].length > 1) return lines[i + 1];
    }
  }

  // フォールバック: 人名らしい行を探す
  var namePat = /^[A-Z][a-zA-Z'-]+(\s+[A-Z][a-zA-Z'-]*){0,3}$/;
  var skip = { stores:1, booking:1, personal:1, makeup:1, session:1,
               payment:1, cancel:1, email:1, phone:1, sydney:1,
               singapore:1, atelier:1 };
  for (var j = 0; j < lines.length; j++) {
    var line = lines[j];
    if (namePat.test(line) && !skip[line.split(' ')[0].toLowerCase()]) {
      return line;
    }
  }
  return null;
}

// ================================================
//  ファーストネームを判定（苗字が先か後かを解析）
// ================================================
function resolveFirstName(fullName) {
  // 日本語名（漢字・かな）はそのまま返す
  if (/[ぁ-んァ-ン一-鿿]/.test(fullName)) return fullName;

  var parts = fullName.trim().split(/\s+/).map(function(p) {
    return p.charAt(0).toUpperCase() + p.slice(1).toLowerCase();
  });
  if (parts.length === 1) return parts[0];

  var first  = parts[0].toLowerCase();
  var second = parts[1] ? parts[1].toLowerCase() : '';

  // 苗字リスト（日本・SG/MY/HK中国系）
  var surnames = {
    // 日本
    sato:1,suzuki:1,takahashi:1,tanaka:1,watanabe:1,ito:1,yamamoto:1,
    nakamura:1,kobayashi:1,kato:1,yoshida:1,yamada:1,sasaki:1,
    yamaguchi:1,matsumoto:1,inoue:1,kimura:1,hayashi:1,shimizu:1,
    yamazaki:1,mori:1,abe:1,ikeda:1,hashimoto:1,yamashita:1,
    ishikawa:1,nakajima:1,ogawa:1,maeda:1,fujita:1,okamoto:1,
    matsuda:1,nakagawa:1,fujii:1,nishimura:1,fukuda:1,ota:1,miura:1,
    okada:1,kaneko:1,harada:1,miyazaki:1,sakamoto:1,ishida:1,
    sugiyama:1,ueda:1,goto:1,masuda:1,chiba:1,kubo:1,nishida:1,
    fujiwara:1,hasegawa:1,saito:1,aoki:1,tamura:1,takeuchi:1,
    kawaguchi:1,honda:1,hara:1,
    // SG / MY / HK
    tan:1,lim:1,lee:1,ng:1,chan:1,wong:1,goh:1,ong:1,chua:1,koh:1,
    teo:1,yeo:1,ho:1,lau:1,loh:1,sim:1,ang:1,yap:1,chew:1,chong:1,
    foo:1,heng:1,leong:1,phua:1,seah:1,sng:1,soh:1,tay:1,wee:1,
    yong:1,yuen:1,beh:1,chia:1,cheong:1,fong:1,huang:1,kam:1,
    khoo:1,kwok:1,lai:1,lam:1,low:1,lu:1,mah:1,mok:1,neo:1,
    pang:1,poh:1,quah:1,quek:1,soon:1,tang:1,toh:1,wan:1,wu:1,
    xu:1,yan:1,yang:1,yu:1,zhang:1,zhao:1,zheng:1,zhou:1,lin:1,chen:1
  };

  if (surnames[first] && !surnames[second]) return parts[1]; // 苗字が先
  if (!surnames[first] && surnames[second]) return parts[0]; // 名前が先
  if (surnames[first])                      return parts[1]; // 両方苗字っぽい→2番目を選択
  return parts[0]; // 判定不能→最初のトークン
}

// ========================
//  ラベルを取得または作成
// ========================
function getOrCreateLabel(name) {
  var label = GmailApp.getUserLabelByName(name);
  return label ? label : GmailApp.createLabel(name);
}
