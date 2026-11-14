function composer() {
  return document.querySelector("textarea") ||
    document.querySelector('[contenteditable="true"]');
}

chrome.runtime.onMessage.addListener((message) => {
  if (message.type !== "insert") return;
  const target = composer();
  if (!target) return;
  if (target.matches("textarea")) {
    const setter = Object.getOwnPropertyDescriptor(
      HTMLTextAreaElement.prototype, "value"
    ).set;
    setter.call(target, `${target.value}${target.value ? "\n\n" : ""}${message.content}`);
    target.dispatchEvent(new Event("input", { bubbles: true }));
  } else {
    target.focus();
    document.execCommand("insertText", false, message.content);
  }
});
