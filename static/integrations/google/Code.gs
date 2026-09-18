/**
 * Google Apps Script host for the TriageCounsel Docs sidebar.
 * Deploy as a Docs add-on. The sidebar itself is served by TriageCounsel
 * so the policy engine stays on the server.
 *
 * File > New > Script, paste this, then Extensions > Apps Script:
 *   function onOpen() { TriageCounsel.onOpen(); }
 */
function onOpen() {
  DocumentApp.getUi()
    .createAddonMenu()
    .addItem("Open TriageCounsel", "showTriageCounselSidebar")
    .addToUi();
}

function showTriageCounselSidebar() {
  var url = PropertiesService.getScriptProperties().getProperty("TRIAGECOUNSEL_BASE_URL");
  if (!url) {
    DocumentApp.getUi().alert("Set TRIAGECOUNSEL_BASE_URL in Script Properties.");
    return;
  }
  var html = HtmlService.createHtmlOutput(
    '<iframe src="' + url + '/integrations/google/sidebar" style="width:100%;height:100%;border:0"></iframe>'
  ).setTitle("TriageCounsel").setWidth(360);
  DocumentApp.getUi().showSidebar(html);
}

function getDocumentText() {
  return DocumentApp.getActiveDocument().getBody().getText();
}

function highlightText(excerpt) {
  var body = DocumentApp.getActiveDocument().getBody();
  var found = body.findText(excerpt.substring(0, 250));
  if (!found) return false;
  found.getElement().asText().setBackgroundColor(
    found.getStartOffset(), found.getEndOffsetInclusive(), "#FEF3C7"
  );
  return true;
}

function insertComment(excerpt, comment) {
  var doc = DocumentApp.getActiveDocument();
  var found = doc.getBody().findText((excerpt || "").substring(0, 250));
  if (!found) return false;
  var range = doc.newRange()
    .addElement(found.getElement(), found.getStartOffset(), found.getElement(), found.getEndOffsetInclusive())
    .build();
  doc.addNamedRange("tc-" + new Date().getTime(), range);
  // Native Docs comments require the Drive Comments advanced service.
  // Never append text into the contract body — that would mutate the deal.
  try {
    var payload = { content: String(comment || "").substring(0, 4096) };
    if (typeof Drive !== "undefined" && Drive.Comments) {
      if (Drive.Comments.create) {
        Drive.Comments.create(payload, doc.getId());
        return true;
      }
      if (Drive.Comments.insert) {
        Drive.Comments.insert(payload, doc.getId());
        return true;
      }
    }
  } catch (e) {}
  return false;
}

function suggestReplacement(excerpt, replacement) {
  var body = DocumentApp.getActiveDocument().getBody();
  var found = body.findText(excerpt);
  if (!found) return false;
  var el = found.getElement().asText();
  el.deleteText(found.getStartOffset(), found.getEndOffsetInclusive());
  el.insertText(found.getStartOffset(), replacement);
  return true;
}
