/**
 * STORES予約 → Googleスプレッドシート 自動同期スクリプト
 *
 * 【関数一覧】
 * - manualSync()             : 現在の正しいデータを直接書き込む（リセット用）
 * - checkBookingsAndUpdate() : 毎朝5時に自動実行
 * - setDailyTrigger()        : 初回のみ手動実行してトリガーを設定
 */

const SESSION_SPREADSHEET_ID = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SPREADSHEET_ID   = '1Ndb9YHiGuWJ9UI_dW9tQ4Cbp8p2PwG-EL3FSdTA97PI';
const EVENT_SHEET_NAME       = 'Japanese Makeup Preview';
const SESSION_KEYWORD        = 'Personal Makeup Session — Singapore';
const EVENT_KEYWORD          = 'Japanese Makeup Preview';

function setDropdown(sheet, startRow, numRows) {
  const rule = SpreadsheetApp.newDataValidation()
    .requireValueInList(['完了', '未確認'], true)
    .setAllowInvalid(false)
    .build();
  sheet.getRange(startRow, 4, numRows, 1).setDataValidation(rule);
}

// 料金決定：2026年8月以降は280 SGD
function getSessionFee(dateStr) {
  if (!dateStr) return 250;
  const m = dateStr.match(/(\d{4})\/(\d+)\//);
  if (!m) return 250;
  const year = parseInt(m[1]);
  const month = parseInt(m[2]);
  if (year > 2026 || (year === 2026 && month >= 8)) return 280;
  return 250;
}

// -------------------------------------------------------
// manualSync — 現在の正しいデータを直接書き込む
// -------------------------------------------------------
function manualSync() {
  const ss = SpreadsheetApp.openById(SESSION_SPREADSHEET_ID);
  const sessionSheet = ss.getActiveSheet();
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
    ['2026/6/21 16:00', '永守 久美子', 250, '完了'],
    ['2026/6/21 17:30', 'Wong Jean',         250, '未確認'],
    ['2026/6/21 18:30', 'Caroline Lin',      250, '完了'],
    ['2026/6/23 11:00', 'Pan Kit mei',       250, '完了'],
    ['2026/6/23 12:00', 'Liu Liling',        250, '未確認'],
    ['2026/6/23 14:00', 'Wong Amanda',       250, '未確認'],
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
    ['2026/6/28 16:00', 'Elisa Montano',     250, '未確認'],
    ['2026/6/30 14:00', 'Tan Michelle',      250, '完了'],
    ['2026/7/2 11:00',  'Iswaran Meena',     250, '未確認'],
  ];
  const lastRow = sessionSheet.getLastRow();
  if (lastRow > 1) sessionSheet.deleteRows(2, lastRow - 1);
  sessionSheet.getRange(2, 1, sessionData.length, 4).setValues(sessionData);
  setDropdown(sessionSheet, 2, sessionData.length);

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
  setDropdown(eventSheet, 2, eventData.length);
  Logger.log('manualSync完了: ' + sessionData.length + '件書き込み完了（プルダウン設定済）');
}

// -------------------------------------------------------
// メイン処理（毎朝5時に自動実行）
// -------------------------------------------------------
function checkBookingsAndUpdate() {
  const sessionSheet = SpreadsheetApp.openById(SESSION_SPREADSHEET_ID).getActiveSheet();
  const eventSS = SpreadsheetApp.openById(EVENT_SPREADSHEET_ID);
  let eventSheet = eventSS.getSheetByName(EVENT_SHEET_NAME);
  if (!eventSheet) {
    eventSheet = eventSS.insertSheet(EVENT_SHEET_NAME);
    eventSheet.appendRow(['日時', '名前', '料金 (SGD)', '決済完了']);
  }

  const props = PropertiesService.getScriptProperties();
  const processedKey = 'processedIds';
  const processedIds = new Set(JSON.parse(props.getProperty(processedKey) || '[]'));

  const threads = GmailApp.search('from:hello@stores.jp newer_than:90d');
  let sessionUpdated = false;
  let eventUpdated   = false;

  for (const thread of threads) {
    for (const message of thread.getMessages()) {
      const msgId = message.getId();
      if (processedIds.has(msgId)) continue;

      const subject = message.getSubject();
      const body    = message.getPlainBody();

      if (subject.includes('予約が入りました')) {
        if (body.includes(SESSION_KEYWORD)) { addNewBooking(sessionSheet, body); sessionUpdated = true; }
        if (body.includes(EVENT_KEYWORD))   { addNewBooking(eventSheet,   body, 88); eventUpdated = true; }
      } else if (subject.includes('が変更されました')) {
        if (body.includes(SESSION_KEYWORD)) { updateBooking(sessionSheet, body); sessionUpdated = true; }
        if (body.includes(EVENT_KEYWORD))   { updateBooking(eventSheet,   body); eventUpdated   = true; }
      } else if (subject.includes('キャンセル') || subject.includes('をキャンセルしました')) {
        if (body.includes(SESSION_KEYWORD)) { cancelBooking(sessionSheet, body, subject); sessionUpdated = true; }
        if (body.includes(EVENT_KEYWORD))   { cancelBooking(eventSheet,   body, subject); eventUpdated   = true; }
      }

      processedIds.add(msgId);
    }
  }

  const idsArray = Array.from(processedIds).slice(-1000);
  props.setProperty(processedKey, JSON.stringify(idsArray));

  if (sessionUpdated) sortByDate(sessionSheet);
  if (eventUpdated)   sortByDate(eventSheet);
}

// fixedFeeを指定した場合はそれを使う（イベント用）、そうでなければ日付から自動判定
function addNewBooking(sheet, body, fixedFee) {
  const nameMatch = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  const dateMatch = body.match(/◆予約日時:\s*\r?\n\s*(.+)/);
  if (!nameMatch || !dateMatch) return;
  const name    = nameMatch[1].trim();
  const dateStr = parseJapaneseDate(dateMatch[1].trim());
  if (!dateStr) return;
  const fee = (fixedFee !== undefined) ? fixedFee : getSessionFee(dateStr);
  const data = sheet.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (String(data[i][0]) === dateStr && data[i][1] === name) return;
  }
  const newRow = sheet.getLastRow() + 1;
  sheet.appendRow([dateStr, name, fee, '未確認']);
  setDropdown(sheet, newRow, 1);
}

function updateBooking(sheet, body) {
  const afterSection  = body.match(/\[ 変更後 \]([\s\S]*?)\[ 変更前 \]/);
  const beforeSection = body.match(/\[ 変更前 \]([\s\S]*)$/);
  if (!afterSection || !beforeSection) return;
  const nameMatch       = beforeSection[1].match(/◆予約者:\s*\r?\n\s*(.+)/);
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

function cancelBooking(sheet, body, subject) {
  let name;
  const nameInBody = body.match(/◆予約者:\s*\r?\n\s*(.+)/);
  if (nameInBody) {
    name = nameInBody[1].trim();
  } else {
    const nameInSubject = subject && subject.match(/^(.+?)　?様の予約をキャンセル/);
    if (nameInSubject) name = nameInSubject[1].trim();
  }
  if (!name) return;
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

function parseJapaneseDate(dateStr) {
  const match = dateStr.match(/(\d{4})年(\d{2})月(\d{2})日[^)]+\)\s*(\d{2}:\d{2})/);
  if (!match) return null;
  const [, year, month, day, time] = match;
  return `${year}/${parseInt(month)}/${parseInt(day)} ${time}`;
}

function sortByDate(sheet) {
  const lastRow = sheet.getLastRow();
  if (lastRow <= 2) return;
  sheet.getRange(2, 1, lastRow - 1, sheet.getLastColumn()).sort(1);
}

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
