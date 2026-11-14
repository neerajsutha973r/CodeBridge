chrome.runtime.onInstalled.addListener(() => {
  console.log("CodeBridge installed.");
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

  if (message.type === "SEND_INSTRUCTION") {
    fetch("http://127.0.0.1:8765/instruction", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(message.instruction)
    })
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => {
        sendResponse({
          status: "ERROR",
          message: error.message
        });
      });

    return true;
  }

  if (message.type === "GET_PROJECT_TREE") {
    fetch("http://127.0.0.1:8765/project-tree")
      .then(response => response.json())
      .then(data => sendResponse(data))
      .catch(error => {
        sendResponse({
          status: "ERROR",
          message: error.message
        });
      });

    return true;
  }
});