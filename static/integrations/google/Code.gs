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
  if (!found) {
    doc.addNamedRange("tc-comment", doc.newPosition(doc.getBody(), 0).insertText(""));
    return false;
  }
  // Docs comments require Drive comments API; the sidebar records the
  // comment in TriageCounsel either way. Insert a visible suggestion note.
  found.getElement().asText().appendText(" [TriageCounsel: " + comment.substring(0, 180) + "]");
  return true;
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
