// ===================================================
//  STORES 予約メール 閲覧・整理
//  Personal Makeup Session Sydney
// ===================================================

// 処理済みメールに付けるGmailラベル名
var PROCESSED_LABEL = 'STORES-確認済み';

// STORESの予約通知メールを検索するクエリ
var SEARCH_QUERY = 'subject:"予約が入りました" is:unread -label:' + PROCESSED_LABEL;

// ======================
//  メイン処理（自動実行）
// ======================
function processStoresReservations() {
  var label = getOrCreateLabel(PROCESSED_LABEL);
  var threads = GmailApp.search(SEARCH_QUERY);

  if (threads.length === 0) {
    Logger.log('新しいSTORES予約メールはありません');
    return;
  }

  threads.forEach(function(thread) {
    thread.getMessages().forEach(function(message) {
      if (!message.isUnread()) return;

      var body = message.getPlainBody();
      var name  = extractName(body);
      var email = extractEmail(body);

      Logger.log('予約を検出: ' + (name || '名前不明') + ' <' + (email || 'メール不明') + '>');

      message.markRead();
      thread.addLabel(label);
      Logger.log('処理完了（既読・ラベル付け）: ' + message.getSubject());
    });
  });
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
      var inline = lines[i].replace(/.*[：:]/, '').trim();
      if (inline.length > 1) return inline;
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

// ========================
//  ラベルを取得または作成
// ========================
function getOrCreateLabel(name) {
  var label = GmailApp.getUserLabelByName(name);
  return label ? label : GmailApp.createLabel(name);
}
