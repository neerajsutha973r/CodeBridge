
console.log("CodeBridge: Listening for instructions.");

const processedBlocks = new WeakSet();

function parseInstruction(content) {
  const text = content.trim();

  const start = text.indexOf("[CODEBRIDGE]");
  const end = text.lastIndexOf("[/CODEBRIDGE]");

  if (start === -1 || end === -1 || end <= start) {
    return null;
  }

  const instructionText = text.slice(
    start + "[CODEBRIDGE]".length,
    end
  ).trim();

  const codeSeparator = instructionText.indexOf("---CODE---");
  const endSeparator = instructionText.lastIndexOf("---END-CODE---");

  if (codeSeparator === -1 || endSeparator === -1 ||
      endSeparator <= codeSeparator) {
    return null;
  }

  const header = instructionText.slice(0, codeSeparator).trim();
  const code = instructionText.slice(
    codeSeparator + "---CODE---".length,
    endSeparator
  ).trim();

  const headerMatch = header.match(
    /^ACTION:\s*(INSERT|REPLACE|CREATE|DELETE|INSPECT)\s*FILE:\s*([^\r\n]+)\s*TARGET:\s*([^\r\n]+)$/i
  );

  if (!headerMatch || !code) return null;

  return {
    action: headerMatch[1].toUpperCase(),
    file: headerMatch[2].trim(),
    target: headerMatch[3].trim(),
    code
  };
}


function showCodeBridgeStatus(block, result) {
  const success = result?.status === "DONE";

  // Remove any previous CodeBridge notification.
  document.querySelectorAll('[data-codebridge-status="true"]')
    .forEach(el => el.remove());

  const status = document.createElement("div");

  status.setAttribute("data-codebridge-status", "true");

  status.style.cssText = `
    position: fixed;
    right: 20px;
    bottom: 20px;
    z-index: 999999;
    width: 320px;
    padding: 16px;
    border-radius: 10px;
    border: 1px solid ${success ? "#16a34a" : "#dc2626"};
    background: ${success ? "#f0fdf4" : "#fef2f2"};
    color: ${success ? "#166534" : "#991b1b"};
    font-family: Arial, sans-serif;
    font-size: 13px;
    line-height: 1.7;
    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
  `;

  const heading = document.createElement("strong");
  heading.textContent = success
    ? "CodeBridge — DONE"
    : "CodeBridge — ERROR";

  const details = document.createElement("div");
  details.textContent = success
    ? `File: ${result.file || "Unknown"} | Target: ${result.target || "Unknown"}`
    : (result?.error || result?.message || "Unknown error");

  const backup = document.createElement("div");
  backup.textContent = success
    ? `Backup: ${result.backup ? "Created" : "Not required"}`
    : "File modification was not confirmed.";

  status.append(heading, details, backup);
  document.body.appendChild(status);

  console.log(
    "CodeBridge: Status inserted:",
    status.isConnected
  );
  setTimeout(() => {
    status.remove();
  }, 5000);
}

function showDeleteConfirmation(instruction, onConfirm, onCancel) {
  const overlay = document.createElement("div");

  overlay.style.cssText = `
    position: fixed;
    inset: 0;
    z-index: 999999;
    background: rgba(0, 0, 0, 0.55);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: Arial, sans-serif;
  `;

  const popup = document.createElement("div");

  popup.style.cssText = `
    background: white;
    color: #222;
    padding: 24px;
    width: 360px;
    max-width: 90%;
    border-radius: 12px;
    box-shadow: 0 10px 35px rgba(0,0,0,0.3);
  `;

  const heading = document.createElement("h3");
  heading.textContent = "Confirm file deletion";

  const message = document.createElement("p");
  message.textContent =
    `Are you sure you want to delete "${instruction.file}"?`;

  const warning = document.createElement("p");
  warning.textContent = "A backup will be created before deletion.";

  const buttons = document.createElement("div");
  buttons.style.cssText = `
    display: flex;
    justify-content: flex-end;
    gap: 10px;
    margin-top: 24px;
  `;

  const cancelButton = document.createElement("button");
  cancelButton.textContent = "Cancel";

  const confirmButton = document.createElement("button");
  confirmButton.textContent = "Confirm Delete";

  confirmButton.style.cssText = `
    background: #dc2626;
    color: white;
    border: none;
    padding: 10px 14px;
    border-radius: 6px;
    cursor: pointer;
  `;

  cancelButton.style.cssText = `
    padding: 10px 14px;
    border: 1px solid #ccc;
    border-radius: 6px;
    cursor: pointer;
  `;

  function closePopup() {
    overlay.remove();
  }

  cancelButton.addEventListener("click", () => {
    closePopup();
    onCancel();
  });

  confirmButton.addEventListener("click", () => {
    closePopup();
    onConfirm();
  });

  buttons.append(cancelButton, confirmButton);
  popup.append(heading, message, warning, buttons);
  overlay.appendChild(popup);
  document.body.appendChild(overlay);
}


function showProjectTree(result) {
  if (result?.status !== "DONE" || !Array.isArray(result.tree)) {
    console.error("CodeBridge: Invalid project tree response", result);
    return;
  }

  document.querySelectorAll('[data-codebridge-explorer="true"]')
    .forEach(el => el.remove());

  const panel = document.createElement("div");
  panel.setAttribute("data-codebridge-explorer", "true");

  panel.style.cssText = `
    position: fixed;
    top: 100px;
    right: 20px;
    z-index: 999999;
    width: 340px;
    max-height: 70vh;
    overflow-y: auto;
    padding: 16px;
    border: 1px solid #64748b;
    border-radius: 12px;
    background: #ffffff;
    color: #222222;
    font: 14px Arial, sans-serif;
    box-shadow: 0 5px 25px rgba(0,0,0,0.25);
  `;

  const heading = document.createElement("h3");
  heading.textContent = "Project Explorer: " + result.project;

  const closeButton = document.createElement("button");
  closeButton.textContent = "Close";
  closeButton.style.cssText = "float:right; cursor:pointer;";
  closeButton.addEventListener("click", () => panel.remove());

  const treeContainer = document.createElement("div");
  treeContainer.style.marginTop = "16px";

  function renderItems(items, parent) {
    items.forEach(item => {
      const row = document.createElement("div");
      row.style.cssText = "padding:5px 0 5px 12px;";

      const label = document.createElement("div");

      if (item.type === "folder") {
        label.textContent = "📁 " + item.name;
        label.style.fontWeight = "bold";
        row.appendChild(label);

        renderItems(item.children || [], row);
      } else {
        label.textContent = "📄 " + item.name;
        row.appendChild(label);
      }

      parent.appendChild(row);
    });
  }

  renderItems(result.tree, treeContainer);

  const copyButton = document.createElement("button");
  copyButton.textContent = "Copy project structure";
  copyButton.style.cssText = `
    margin-top: 16px;
    padding: 9px 12px;
    cursor: pointer;
  `;

  copyButton.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(
        JSON.stringify(result, null, 2)
      );
      copyButton.textContent = "Copied!";
    } catch (error) {
      copyButton.textContent = "Copy failed";
      console.error("CodeBridge clipboard error:", error);
    }
  });

  panel.append(closeButton, heading, treeContainer, copyButton);
  document.body.appendChild(panel);
}

function insertProjectContext(result) {
  if (result?.status !== "DONE" || !Array.isArray(result.tree)) {
    console.error("CodeBridge: Invalid project context", result);
    return;
  }

  const composer = document.querySelector(
    '[contenteditable="true"][data-composer-markdown]'
  );

  if (!composer) {
    console.error("CodeBridge: ChatGPT composer not found.");
    return;
  }

  const context = [
    "Here is my current project structure. Please inspect it before suggesting code changes:",
    "",
    JSON.stringify(result, null, 2)
  ].join("\n");

  composer.focus();

  const inserted = document.execCommand(
    "insertText",
    false,
    context
  );

  if (!inserted) {
    console.error("CodeBridge: Could not insert project context.");
    return;
  }

  console.log("CodeBridge: Project context inserted into ChatGPT.");
}



function inspectResponses() {
  const blocks = document.querySelectorAll(
    '[data-code-block-source="true"] code'
  );

  console.log("CodeBridge scanned blocks:", blocks.length);

  blocks.forEach(block => {
    if (processedBlocks.has(block)) return;

    const instruction = parseInstruction(block.innerText || "");

    if (!instruction) return;

    processedBlocks.add(block);

    console.log("CodeBridge instruction detected:", instruction);

    function sendInstructionToAgent() {
      const message = instruction.action === "INSPECT"
        ? { type: "GET_PROJECT_TREE" }
        : {
            type: "SEND_INSTRUCTION",
            instruction
          };

      chrome.runtime.sendMessage(message, result => {
        if (chrome.runtime.lastError) {
          const errorResult = {
            status: "ERROR",
            message: chrome.runtime.lastError.message
          };

          console.error("CodeBridge connection failed:", errorResult);
          showCodeBridgeStatus(block, errorResult);
          return;
        }

        console.log("CodeBridge agent response:", result);

        if (instruction.action === "INSPECT") {
          console.log("CodeBridge project structure:", result);

          insertProjectContext(result);
          return;
        }

        showCodeBridgeStatus(block, result);
      });
    }

    // DELETE requires explicit user confirmation.
    if (instruction.action === "DELETE") {
      console.log("CodeBridge: Waiting for DELETE confirmation.");

      showDeleteConfirmation(
        instruction,

        // Confirm button
        () => {
          console.log("CodeBridge: DELETE confirmed.");
          sendInstructionToAgent();
        },

        // Cancel button
        () => {
          console.log("CodeBridge: DELETE cancelled. No request sent.");
        }
      );

      return;
    }

    // Other actions continue normally.
    sendInstructionToAgent();
  });
}


const observer = new MutationObserver(inspectResponses);

observer.observe(document.body, {
  childList: true,
  subtree: true,
  characterData: true
});

inspectResponses();
