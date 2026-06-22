function getInvoke() {
  const invoke = window.__TAURI__?.core?.invoke;

  if (!invoke) {
    throw new Error('Tauri API is not available. Please rebuild and open the Tauri app, not index.html in a browser.');
  }

  return invoke;
}

async function invoke(command, args) {
  return getInvoke()(command, args);
}

const inputFolder = document.querySelector('#inputFolder');
const outputFolder = document.querySelector('#outputFolder');
const folderCount = document.querySelector('#folderCount');
const seed = document.querySelector('#seed');
const prefixFiles = document.querySelector('#prefixFiles');
const cleanOutput = document.querySelector('#cleanOutput');
const chooseInput = document.querySelector('#chooseInput');
const chooseOutput = document.querySelector('#chooseOutput');
const generate = document.querySelector('#generate');
const openOutput = document.querySelector('#openOutput');
const copyPaths = document.querySelector('#copyPaths');
const status = document.querySelector('#status');
const paths = document.querySelector('#paths');
const dropZones = document.querySelectorAll('.dropZone');

let generatedFolders = [];
let lastOutputFolder = '';

for (const dropZone of dropZones) {
  dropZone.addEventListener('dragover', (event) => {
    event.preventDefault();
    dropZone.classList.add('dragging');
  });

  dropZone.addEventListener('dragleave', () => {
    dropZone.classList.remove('dragging');
  });

  dropZone.addEventListener('drop', (event) => {
    event.preventDefault();
    dropZone.classList.remove('dragging');

    const droppedPath = getDroppedPath(event);

    if (!droppedPath) {
      setStatus('Could not read dropped folder path.', 'error');
      return;
    }

    const target = dropZone.dataset.dropTarget === 'input' ? inputFolder : outputFolder;
    target.value = droppedPath;
    setStatus('Dropped folder path added.', 'success');
  });
}

function getDroppedPath(event) {
  const item = event.dataTransfer?.items?.[0];

  if (item) {
    const entry = item.webkitGetAsEntry?.();
    if (entry?.isDirectory) {
      return event.dataTransfer.files?.[0]?.path || event.dataTransfer.getData('text/plain');
    }
  }

  return event.dataTransfer?.files?.[0]?.path || event.dataTransfer?.getData('text/plain') || '';
}

chooseInput.addEventListener('click', async () => {
  await chooseFolder(inputFolder, 'Opening source folder picker...');
});

chooseOutput.addEventListener('click', async () => {
  await chooseFolder(outputFolder, 'Opening output folder picker...');
});

async function chooseFolder(targetInput, message) {
  setStatus(message, 'idle');

  try {
    const folder = await invoke('select_folder');

    if (folder) {
      targetInput.value = folder;
      setStatus('Folder selected.', 'success');
    } else {
      setStatus('Folder selection cancelled.', 'idle');
    }
  } catch (error) {
    setStatus(String(error), 'error');
  }
}

generate.addEventListener('click', async () => {
  setBusy(true);
  setStatus('Generating folders...', 'idle');
  renderPaths([]);

  try {
    const result = await invoke('mix_files', {
      options: {
        inputFolder: inputFolder.value,
        outputFolder: outputFolder.value,
        folderCount: Number(folderCount.value),
        prefixFiles: prefixFiles.checked,
        cleanOutput: cleanOutput.checked,
        seed: seed.value || null,
      },
    });

    generatedFolders = result.generatedFolders;
    lastOutputFolder = result.outputFolder;
    renderPaths(generatedFolders);
    setStatus(`Done: created ${generatedFolders.length} folders from ${result.sourceFileCount} MP3 files.`, 'success');
    openOutput.disabled = false;
    copyPaths.disabled = generatedFolders.length === 0;
  } catch (error) {
    setStatus(String(error), 'error');
    openOutput.disabled = true;
    copyPaths.disabled = true;
  } finally {
    setBusy(false);
  }
});

openOutput.addEventListener('click', async () => {
  if (lastOutputFolder) await invoke('open_path', { path: lastOutputFolder });
});

copyPaths.addEventListener('click', async () => {
  await navigator.clipboard.writeText(generatedFolders.join('\n'));
  setStatus('Copied output folder paths to clipboard.', 'success');
});

function setBusy(isBusy) {
  generate.disabled = isBusy;
  chooseInput.disabled = isBusy;
  chooseOutput.disabled = isBusy;
}

function setStatus(message, type) {
  status.textContent = message;
  status.className = `status ${type}`;
}

function renderPaths(folderPaths) {
  paths.innerHTML = '';

  if (folderPaths.length === 0) {
    paths.className = 'paths empty';
    paths.textContent = 'No folders generated yet.';
    return;
  }

  paths.className = 'paths';

  for (const folderPath of folderPaths) {
    const item = document.createElement('div');
    item.className = 'pathItem';

    const code = document.createElement('code');
    code.textContent = folderPath;

    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = 'Open';
    button.addEventListener('click', () => invoke('open_path', { path: folderPath }));

    item.append(code, button);
    paths.append(item);
  }
}
