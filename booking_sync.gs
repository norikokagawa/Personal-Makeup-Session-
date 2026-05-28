/**
 * STORES予約 → Googleスプレッドシート 自動同期スクリプト
 *
 * 【関数一覧】
 * - manualSync()    : 現在の正しいデータを直接書き込む（一回限りのリセット用）
 * - checkBookingsAndUpdate() : 毎朝5時に自動実行（未読メールのみ処理）
 * - setDailyTrigger() : 初回のみ手動実行してトリガーを設定
 */

const SESSION_SPREADSHEET_ID = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SPREADSHEET_ID   = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SHEET_NAME       = 'Japanese Makeup Preview';
const SESSION_KEYWORD        = 'Personal Makeup Session — Singapore';
const EVENT_KEYWORD          = 'Japanese Makeup Preview';

// -------------------------------------------------------
// manualSync — 現在の正しいデータを直接スプレッドシートに書き込む
// スプレッドシートが乱れたときに一回手動で実行する
// -------------------------------------------------------
function manualSync() {
  const ss = SpreadsheetApp.openById(SESSION_SPREADSHEET_ID);
  const sessionSheet = ss.getActiveSheet();

  // セッションデータ（GitHub CSVからの正しいリスト）
  const sessionData = [
    ['2026/6/18 11:00', 'Michelle Poh',      250, '完了'],
    ['2026/6/18 12:00', 'ISHIDA EMIKO',      250, '未確認'],
    ['2026/6/18 13:00', 'Fion Histed',       250, '未確認'],
    ['2026/6/18 14:00', 'Charmaine Low',     250, '未確認'],
    ['2026/6/19 11:00', 'Narissa S',         250, '未確認'],
    ['2026/6/19 12:00', 'Veana Lee',         250, '未確認'],
    ['2026/6/19 13:00', 'Nicole Lu',         250, '未確認'],
    ['2026/6/19 14:00', 'Chan Cheryl',       250, '完了'],
    ['2026/6/20 10:00', 'Jessica Novia',     250, '完了'],
    ['2026/6/20 11:00', 'Lim Gwend',         250, '完了'],
    ['2026/6/20 12:00', 'Kar Enn Ho',        250, '完了'],
    ['2026/6/20 14:00', 'Khoo Emily',        250, '完了'],
    ['2026/6/20 15:00', 'Xie Shermin',       250, '完了'],
    ['2026/6/20 16:00', 'Deng Shirley',      250, '完了'],
    ['2026/6/20 17:30', 'Jennifer Leow',     250, '完了'],
    ['2026/6/20 18:30', 'Serafico Ivy',      250, '完了'],
    ['2026/6/21 10:00', 'Serene Liew',       250, '完了'],
    ['2026/6/21 11:00', 'Sophia Susanto',    250, '未確認'],
    ['2026/6/21 12:00', 'Satomi Fujimoto',   250, '未確認'],
    ['2026/6/21 14:00', 'H Su',              250, '完了'],
    ['2026/6/21 15:00', 'H Su',              250, '完了'],
    ['2026/6/21 16:00', '永守 久美子',      250, '完了'],
    ['2026/6/21 17:30', 'Wong Jean',         250, '未確認'],
    ['2026/6/21 18:30', 'Caroline Lin',      250, '完了'],
    ['2026/6/23 11:00', 'Pan Kit mei',       250, '完了'],
    ['2026/6/24 11:00', 'Voon Taylor',       250, '完了'],
    ['2026/6/25 11:00', 'Pei Lin Chua',      250, '未確認'],
    ['2026/6/25 12:00', 'Leung Erin',        250, '未確認'],
    ['2026/6/25 14:00', 'Tiong Ling',        250, '未確認'],
    ['2026/6/27 10:00', 'Jessica Leong',     250, '完了'],
    ['2026/6/27 11:00', 'Ang Chiean Hong',   250, '完了'],
    ['2026/6/27 12:00', 'Li Shan Tan',       250, '未確認'],
    ['2026/6/27 14:00', 'Lee Rachel',        250, '未確認'],
    ['2026/6/27 17:30', 'Wee Lie Soh',       250, '完了'],
    ['2026/6/28 10:00', 'Elaine Wong',       250, '未確認'],
    ['2026/6/28 11:00', 'Lachman Sweeney',   250, '完了'],
    ['2026/6/28 14:00', 'Ng Amanda',         250, '未確認'],
    ['2026/6/30 14:00', 'Tan Michelle',      250, '完了'],
    ['2026/7/2 11:00',  'Iswaran Meena',     250, '未確認'],
  ];

  // シートをクリアして書き込む
  const lastRow = sessionSheet.getLastRow();
  if (lastRow > 1) sessionSheet.deleteRows(2, lastRow - 1);
  sessionSheet.getRange(2, 1, sessionData.length, 4).setValues(sessionData);

  // イベントシートも同様に書き込む
  const eventSS = SpreadsheetApp.openById(EVENT_SPREADSHEET_ID);
  let eventSheet = eventSS.getSheetByName(EVENT_SHEET_NAME);
  if (!eventSheet) {
    eventSheet = eventSS.insertSheet(EVENT_SHEET_NAME);
    eventSheet.appendRow(['日時', '名前', '料金 (SGD)', '決済完了']);
  } else {
    const eLastRow = eventSheet.getLastRow();
    if (eLastRow > 1) eventSheet.deleteRows(2, eLastRow - 1);
  }
  const eventData = [
    ['2026/7/10 19:00', 'Chung Alice', 88, '未確認'],
    ['2026/7/10 19:00', 'Tan Tong',    88, '未確認'],
  ];
  eventSheet.getRange(2, 1, eventData.length, 4).setValues(eventData);

  Logger.log('manualSync完了: ' + sessionData.length + '件書き込み完了');
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
      const body    = message.getPlainBody();

      const isSession = body.includes(SESSION_KEYWORD) || body.includes('ココにサービス名');
      const isEvent   = body.includes(EVENT_KEYWORD);

      // 新規予約メール
      if (subject.includes('予約が入りました')) {
        const isS = body.includes(SESSION_KEYWORD);
        const isE = body.includes(EVENT_KEYWORD);
        if (isS) { addNewBooking(sessionSheet, body, 250); sessionUpdated = true; }
        if (isE) { addNewBooking(eventSheet,   body, 88);  eventUpdated   = true; }
      }
      // 変更メール
      else if (subject.includes('が変更されました')) {
        if (body.includes(SESSION_KEYWORD)) { updateBooking(sessionSheet, body); sessionUpdated = true; }
        if (body.includes(EVENT_KEYWORD))   { updateBooking(eventSheet,   body); eventUpdated   = true; }
      }
      // キャンセルメール（件名パターンが2種類ある）
      else if (subject.includes('キャンセル') || subject.includes('をキャンセルしました')) {
        if (body.includes(SESSION_KEYWORD)) { cancelBooking(sessionSheet, body, subject); sessionUpdated = true; }
        if (body.includes(EVENT_KEYWORD))   { cancelBooking(eventSheet,   body, subject); eventUpdated   = true; }
      }

      message.markRead();
    }
  }

  if (sessionUpdated) sortByDate(sessionSheet);
  if (eventUpdated)   sortByDate(eventSheet);
}

// -------------------------------------------------------
// 新規予約を追加
// -------------------------------------------------------
function addNewBooking(sheet, body, fee) {
  const nameMatch = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  const dateMatch = body.match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !dateMatch) return;

  const name    = nameMatch[1].trim();
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
  const afterSection  = body.match(/\[ 変更後 \]([\s\S]*?)\[ 変更前 \]/);
  const beforeSection = body.match(/\[ 変更前 \]([\s\S]*)$/);
  if (!afterSection || !beforeSection) return;

  const nameMatch      = beforeSection[1].match(/◆予約者:\s*\r?\n\s*(.+)/);
  const beforeDateMatch = beforeSection[1].match(/◆予約日時:\s*\r?\n\s*(.+)/);
  const afterDateMatch  = afterSection[1].match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !beforeDateMatch || !afterDateMatch) return;

  const name       = nameMatch[1].trim();
  const beforeDate = parseJapaneseDate(beforeDateMatch[1].trim());
  const afterDate  = parseJapaneseDate(afterDateMatch[1].trim());
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
// メール形式1: ◆予約者が本文にある場合（店側キャンセルの場合など）
// メール形式2: 件名に名前がある場合（"XXX 様の予約をキャンセルしました"）
// -------------------------------------------------------
function cancelBooking(sheet, body, subject) {
  let name;

  // 形式1: 本文に ◆予約者 がある
  const nameInBody = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  if (nameInBody) {
    name = nameInBody[1].trim();
  } else {
    // 形式2: 件名から名前を取得 "XXX 様の予約をキャンセルしました"
    const nameInSubject = subject && subject.match(/^(.+?)　?様の予約をキャンセル/);
    if (nameInSubject) name = nameInSubject[1].trim();
  }
  if (!name) return;

  // 日付を取得（両形式共通）
  const dateMatch = body.match(/◆予約日時:\s*\r?\n?\s*(.+)/);
  if (!dateMatch) return;
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
