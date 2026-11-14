# CodeBridge

CodeBridge is a Chrome extension and local Python agent for sharing project
files with ChatGPT without uploading the project to a third-party service.

## Run the agent

```bash
python3 agent.py --root /path/to/project
```

The agent listens only on `127.0.0.1:8765` by default. It exposes `/health`,
`/files`, and `/file?path=...`; paths are confined to the configured project
root, hidden files are excluded, and files over 1 MiB are rejected.

## Install the extension

1. Open `chrome://extensions`, enable **Developer mode**, and choose **Load
   unpacked**.
2. Select the `extension` directory.
3. Open ChatGPT, start the agent, then choose a project file from the
   CodeBridge extension popup and insert it into the composer.

Run the agent tests with:

```bash
python3 -m unittest -v
```