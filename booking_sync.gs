/**
 * STORES予約 → Googleスプレッドシート 自動同期スクリプト
 *
 * 【セットアップ手順】
 * 1. Googleスプレッドシートを開く
 * 2. メニュー「拡張機能」→「Apps Script」をクリック
 * 3. このファイルの内容を貼り付けて保存（Ctrl+S）
 * 4. 「初回セットアップ」:
 *    a) 関数選択で「setDailyTrigger」を選び「実行」→毎朝5時自動実行のトリガーを設定
 *    b) 関数選択で「fullRebuild」を選び「実行」→過去の全メールからスプレッドシートを再構築
 * 5. 権限を許可する（Gmailとスプレッドシートへのアクセス）
 * 6. 以降、毎朝5時（日本時間）に自動で実行されます
 */

const SESSION_SPREADSHEET_ID = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SPREADSHEET_ID = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SHEET_NAME = 'Japanese Makeup Preview';

const SESSION_KEYWORD = 'Personal Makeup Session — Singapore';
const EVENT_KEYWORD = 'Japanese Makeup Preview';

// -------------------------------------------------------
// フル再構築（初回セットアップ時やリセット時に手動実行）
// 過去の全STORESメールを順に処理し、スプレッドシートを正しい状態に再構築する
// -------------------------------------------------------
function fullRebuild() {
  const ss = SpreadsheetApp.openById(SESSION_SPREADSHEET_ID);
  const sessionSheet = ss.getActiveSheet();

  const eventSS = SpreadsheetApp.openById(EVENT_SPREADSHEET_ID);
  let eventSheet = eventSS.getSheetByName(EVENT_SHEET_NAME);
  if (!eventSheet) {
    eventSheet = eventSS.insertSheet(EVENT_SHEET_NAME);
  }

  // シートをクリアしてヘッダーを再設定
  clearSheet(sessionSheet);
  clearSheet(eventSheet);

  // 全STORESメールを取得（最大500スレッド）
  const threads = GmailApp.search('from:hello@stores.jp subject:"[STORES 予約]"', 0, 500);

  // メッセージを日付順（古い順）に並び替え
  const messages = [];
  for (const thread of threads) {
    for (const msg of thread.getMessages()) {
      messages.push(msg);
    }
  }
  messages.sort((a, b) => a.getDate() - b.getDate());

  // 時系列順に処理
  for (const message of messages) {
    const subject = message.getSubject();
    const body = message.getPlainBody();

    const isSession = body.includes(SESSION_KEYWORD);
    const isEvent = body.includes(EVENT_KEYWORD);
    if (!isSession && !isEvent) continue;

    const targetSheet = isEvent ? eventSheet : sessionSheet;
    const fee = isEvent ? 88 : 250;

    if (subject.includes('予約が入りました')) {
      addNewBooking(targetSheet, body, fee);
    } else if (subject.includes('が変更されました')) {
      updateBooking(targetSheet, body);
    } else if (subject.includes('キャンセル')) {
      cancelBooking(targetSheet, body);
    }
  }

  sortByDate(sessionSheet);
  sortByDate(eventSheet);

  Logger.log('fullRebuild完了: session=' + (sessionSheet.getLastRow() - 1) + '件, event=' + (eventSheet.getLastRow() - 1) + '件');
}

// -------------------------------------------------------
// メイン処理（毎朝5時に自動実行）— 未読メールのみ処理
// -------------------------------------------------------
function checkBookingsAndUpdate() {
  const sessionSheet = SpreadsheetApp.openById(SESSION_SPREADSHEET_ID).getActiveSheet();
  const eventSS = SpreadsheetApp.openById(EVENT_SPREADSHEET_ID);
  let eventSheet = eventSS.getSheetByName(EVENT_SHEET_NAME);
  if (!eventSheet) {
    eventSheet = eventSS.insertSheet(EVENT_SHEET_NAME);
    eventSheet.appendRow(['日時', '名前', '料金 (SGD)', '決済完了']);
  }

  const threads = GmailApp.search('from:hello@stores.jp is:unread');
  let sessionUpdated = false;
  let eventUpdated = false;

  for (const thread of threads) {
    for (const message of thread.getMessages()) {
      if (!message.isUnread()) continue;

      const subject = message.getSubject();
      const body = message.getPlainBody();

      const isSession = body.includes(SESSION_KEYWORD);
      const isEvent = body.includes(EVENT_KEYWORD);

      if (!isSession && !isEvent) {
        message.markRead();
        continue;
      }

      const targetSheet = isEvent ? eventSheet : sessionSheet;
      const fee = isEvent ? 88 : 250;

      if (subject.includes('予約が入りました')) {
        addNewBooking(targetSheet, body, fee);
        isEvent ? eventUpdated = true : sessionUpdated = true;
      } else if (subject.includes('が変更されました')) {
        updateBooking(targetSheet, body);
        isEvent ? eventUpdated = true : sessionUpdated = true;
      } else if (subject.includes('キャンセル')) {
        cancelBooking(targetSheet, body);
        isEvent ? eventUpdated = true : sessionUpdated = true;
      }

      message.markRead();
    }
  }

  if (sessionUpdated) sortByDate(sessionSheet);
  if (eventUpdated) sortByDate(eventSheet);
}

// -------------------------------------------------------
// 新規予約を追加
// -------------------------------------------------------
function addNewBooking(sheet, body, fee) {
  const nameMatch = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  const dateMatch = body.match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !dateMatch) return;

  const name = nameMatch[1].trim();
  const dateStr = parseJapaneseDate(dateMatch[1].trim());
  if (!dateStr) return;

  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === dateStr && data[i][1] === name) return;
  }

  sheet.appendRow([dateStr, name, fee, '未確認']);
}

// -------------------------------------------------------
// 予約変更を反映
// -------------------------------------------------------
function updateBooking(sheet, body) {
  const afterSection = body.match(/\[ 変更後 \]([\s\S]*?)\[ 変更前 \]/);
  const beforeSection = body.match(/\[ 変更前 \]([\s\S]*)$/);
  if (!afterSection || !beforeSection) return;

  const nameMatch = beforeSection[1].match(/◆予約者:\s*\r?\n\s*(.+)/);
  const beforeDateMatch = beforeSection[1].match(/◆予約日時:\s*\r?\n\s*(.+)/);
  const afterDateMatch = afterSection[1].match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !beforeDateMatch || !afterDateMatch) return;

  const name = nameMatch[1].trim();
  const beforeDate = parseJapaneseDate(beforeDateMatch[1].trim());
  const afterDate = parseJapaneseDate(afterDateMatch[1].trim());
  if (!beforeDate || !afterDate) return;

  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === beforeDate && data[i][1] === name) {
      sheet.getRange(i + 1, 1).setValue(afterDate);
      return;
    }
  }
}

// -------------------------------------------------------
// キャンセルを削除
// -------------------------------------------------------
function cancelBooking(sheet, body) {
  const nameMatch = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  const dateMatch = body.match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !dateMatch) return;

  const name = nameMatch[1].trim();
  const dateStr = parseJapaneseDate(dateMatch[1].trim());
  if (!dateStr) return;

  const data = sheet.getDataRange().getValues();
  for (let i = data.length - 1; i >= 1; i--) {
    if (String(data[i][0]) === dateStr && data[i][1] === name) {
      sheet.deleteRow(i + 1);
      return;
    }
  }
}

// -------------------------------------------------------
// シートをクリア（ヘッダーは残す）
// -------------------------------------------------------
function clearSheet(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow > 1) {
    sheet.deleteRows(2, lastRow - 1);
  }
  if (lastRow === 0) {
    sheet.appendRow(['日時', '名前', '料金 (SGD)', '決済完了']);
  }
}

// -------------------------------------------------------
// 日付文字列をパース
// "2026年06月18日 (木) 13:00" → "2026/6/18 13:00"
// -------------------------------------------------------
function parseJapaneseDate(dateStr) {
  const match = dateStr.match(/(\d{4})年(\d{2})月(\d{2})日[^)]+\)\s*(\d{2}:\d{2})/);
  if (!match) return null;
  const [, year, month, day, time] = match;
  return `${year}/${parseInt(month)}/${parseInt(day)} ${time}`;
}

// -------------------------------------------------------
// 日時順にソート
// -------------------------------------------------------
function sortByDate(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow <= 2) return;
  sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).sort(1);
}

// -------------------------------------------------------
// 毎朝5時のトリガーを設定（初回のみ手動で実行）
// -------------------------------------------------------
function setDailyTrigger() {
  ScriptApp.getProjectTriggers().forEach(t => {
    if (t.getHandlerFunction() === 'checkBookingsAndUpdate') {
      ScriptApp.deleteTrigger(t);
    }
  });

  ScriptApp.newTrigger('checkBookingsAndUpdate')
    .timeBased()
    .everyDays(1)
    .atHour(5)
    .inTimezone('Asia/Tokyo')
    .create();

  Logger.log('トリガーを設定しました：毎日5:00（日本時間）');
}
