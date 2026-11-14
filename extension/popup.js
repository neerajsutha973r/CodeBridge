const API = "http://127.0.0.1:8765";
const status = document.querySelector("#status");
const files = document.querySelector("#files");
const insert = document.querySelector("#insert");
const copy = document.querySelector("#copy");
let selectedContent = "";

async function loadFiles() {
  const response = await fetch(`${API}/files`);
  if (!response.ok) throw new Error("Agent returned an error");
  const data = await response.json();
  files.replaceChildren(...data.files.map((file) => new Option(file, file)));
  insert.disabled = copy.disabled = data.files.length === 0;
  status.textContent = `${data.files.length} file${data.files.length === 1 ? "" : "s"} available`;
}

async function readSelected() {
  const response = await fetch(`${API}/file?path=${encodeURIComponent(files.value)}`);
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Unable to read file");
  selectedContent = `\`\`\`${files.value}\n${data.content}\n\`\`\``;
  return selectedContent;
}

files.addEventListener("change", () => { selectedContent = ""; });
copy.addEventListener("click", async () => {
  await navigator.clipboard.writeText(await readSelected());
  status.textContent = "Copied to clipboard";
});
insert.addEventListener("click", async () => {
  const content = await readSelected();
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  try {
    await chrome.tabs.sendMessage(tab.id, { type: "insert", content });
    status.textContent = "Inserted into ChatGPT";
  } catch {
    await navigator.clipboard.writeText(content);
    status.textContent = "Copied (open a ChatGPT tab to insert)";
  }
});

loadFiles().catch(() => {
  status.textContent = "Start the agent: python agent.py --root /path/to/project";
});
