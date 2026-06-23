#!/usr/bin/env node
import { copyFile, mkdir, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import readline from 'node:readline/promises';
import { fileURLToPath } from 'node:url';
import { stdin as input, stdout as output } from 'node:process';

const HELP = `
Mix MP3 files into many output folders.

Usage:
  mix-files --input <mp3-folder> --output <output-folder> --folders <count> [options]

Run the executable without options to use interactive mode.

Options:
  -i, --input <path>       Folder containing source .mp3 files
  -o, --output <path>      Folder where output folders are created
  -n, --folders <count>    Number of folders to create
  -f, --files <count>      Number of MP3 files per folder, default: all files
  --prefix / --no-prefix   Add order prefix to file names, default: --prefix
  --clean                  Delete output folder before generating
  --seed <text>            Deterministic shuffle seed
  -h, --help               Show help

Example:
  mix-files-windows.exe --input "D:\\music\\source" --output "D:\\music\\mixed" --folders 50 --clean
  ./mix-files-macos --input ./source --output ./mixed --folders 50 --seed batch-1
`;

function parseArgs(argv) {
  const options = {
    prefix: true,
    clean: false,
    seed: undefined,
  };

  for (let index = 0; index < argv.length; index += 1) {
    const arg = argv[index];
    const next = argv[index + 1];

    if (arg === '-h' || arg === '--help') {
      options.help = true;
    } else if (arg === '-i' || arg === '--input') {
      options.input = readValue(arg, next);
      index += 1;
    } else if (arg === '-o' || arg === '--output') {
      options.output = readValue(arg, next);
      index += 1;
    } else if (arg === '-n' || arg === '--folders') {
      options.folders = Number.parseInt(readValue(arg, next), 10);
      index += 1;
    } else if (arg === '-f' || arg === '--files') {
      options.files = Number.parseInt(readValue(arg, next), 10);
      index += 1;
    } else if (arg === '--prefix') {
      options.prefix = true;
    } else if (arg === '--no-prefix') {
      options.prefix = false;
    } else if (arg === '--clean') {
      options.clean = true;
    } else if (arg === '--seed') {
      options.seed = readValue(arg, next);
      index += 1;
    } else {
      throw new Error(`Unknown option: ${arg}`);
    }
  }

  return options;
}

function readValue(option, value) {
  if (!value || value.startsWith('-')) {
    throw new Error(`Missing value for ${option}`);
  }

  return value;
}

function validateOptions(options) {
  if (options.help) {
    return;
  }

  if (!options.input) {
    throw new Error('Missing required option: --input');
  }

  if (!options.output) {
    throw new Error('Missing required option: --output');
  }

  if (!Number.isInteger(options.folders) || options.folders < 1) {
    throw new Error('--folders must be a positive integer');
  }

  if (options.files !== undefined && (!Number.isInteger(options.files) || options.files < 1)) {
    throw new Error('--files must be a positive integer');
  }
}

async function getMp3Files(inputFolder) {
  const entries = await readdir(inputFolder, { withFileTypes: true });
  const files = entries
    .filter((entry) => entry.isFile() && path.extname(entry.name).toLowerCase() === '.mp3')
    .map((entry) => entry.name)
    .sort((left, right) => left.localeCompare(right, undefined, { numeric: true }));

  if (files.length === 0) {
    throw new Error(`No .mp3 files found in ${inputFolder}`);
  }

  return files;
}

function createRandom(seedText) {
  if (!seedText) {
    return Math.random;
  }

  let state = 2166136261;
  for (const char of seedText) {
    state ^= char.codePointAt(0);
    state = Math.imul(state, 16777619);
  }

  return () => {
    state += 0x6D2B79F5;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function shuffleFiles(files, random) {
  const shuffled = [...files];

  for (let index = shuffled.length - 1; index > 0; index -= 1) {
    const targetIndex = Math.floor(random() * (index + 1));
    [shuffled[index], shuffled[targetIndex]] = [shuffled[targetIndex], shuffled[index]];
  }

  return shuffled;
}

function prefixName(index, fileName, totalFiles) {
  const width = String(totalFiles).length;
  const order = String(index + 1).padStart(width, '0');
  return `${order}_${fileName}`;
}

async function generateFolders(options) {
  const inputFolder = path.resolve(options.input);
  const outputFolder = path.resolve(options.output);
  const files = await getMp3Files(inputFolder);
  const filesPerFolder = options.files ?? files.length;
  const random = createRandom(options.seed);
  const generatedFolders = [];

  if (filesPerFolder > files.length) {
    throw new Error(`--files cannot be greater than available MP3 files (${files.length})`);
  }

  if (options.clean) {
    await rm(outputFolder, { recursive: true, force: true });
  }

  await mkdir(outputFolder, { recursive: true });

  for (let folderIndex = 0; folderIndex < options.folders; folderIndex += 1) {
    const folderName = String(folderIndex + 1).padStart(String(options.folders).length, '0');
    const targetFolder = path.join(outputFolder, folderName);
    const shuffledFiles = shuffleFiles(files, random).slice(0, filesPerFolder);
    generatedFolders.push(targetFolder);

    await mkdir(targetFolder, { recursive: true });

    for (let fileIndex = 0; fileIndex < shuffledFiles.length; fileIndex += 1) {
      const fileName = shuffledFiles[fileIndex];
      const targetName = options.prefix ? prefixName(fileIndex, fileName, shuffledFiles.length) : fileName;
      await copyFile(path.join(inputFolder, fileName), path.join(targetFolder, targetName));
    }
  }

  return {
    inputFolder,
    outputFolder,
    sourceFiles: files.length,
    filesPerFolder,
    folders: options.folders,
    generatedFolders,
  };
}

function normalizeDroppedPath(value) {
  let normalized = value.trim();

  if ((normalized.startsWith('"') && normalized.endsWith('"')) || (normalized.startsWith("'") && normalized.endsWith("'"))) {
    normalized = normalized.slice(1, -1);
  }

  return normalized.replace(/\\ /g, ' ');
}

async function promptForOptions() {
  const terminal = readline.createInterface({ input, output });

  try {
    console.log('Mix Files - MP3 folder shuffler');
    console.log('Press Ctrl+C to exit.');

    const sourceFolder = await terminal.question('Source MP3 folder path, drag and drop folder here: ');
    const targetFolder = await terminal.question('Output folder path, drag and drop folder here: ');
    const folderCount = await terminal.question('Number of folders to create: ');
    const fileCount = await terminal.question('Number of MP3 files per folder, empty for all: ');
    const cleanAnswer = await terminal.question('Clean output folder first? (y/N): ');
    const prefixAnswer = await terminal.question('Add order prefixes like 1_song.mp3? (Y/n): ');
    const seed = await terminal.question('Shuffle seed, optional: ');

    return {
      input: normalizeDroppedPath(sourceFolder),
      output: normalizeDroppedPath(targetFolder),
      folders: Number.parseInt(folderCount.trim(), 10),
      files: fileCount.trim() ? Number.parseInt(fileCount.trim(), 10) : undefined,
      clean: cleanAnswer.trim().toLowerCase() === 'y',
      prefix: prefixAnswer.trim().toLowerCase() !== 'n',
      seed: seed.trim() || undefined,
    };
  } finally {
    terminal.close();
  }
}

async function main() {
  const interactive = process.argv.slice(2).length === 0;

  try {
    const argv = process.argv.slice(2);
    const options = interactive ? await promptForOptions() : parseArgs(argv);
    validateOptions(options);

    if (options.help) {
      console.log(HELP.trim());
      return;
    }

    const result = await generateFolders(options);
    console.log(`Done: created ${result.folders} folders with ${result.filesPerFolder} of ${result.sourceFiles} MP3 files each.`);
    console.log(`Input: ${result.inputFolder}`);
    console.log(`Output: ${result.outputFolder}`);
    console.log('Generated folders:');
    for (const folder of result.generatedFolders) {
      console.log(folder);
    }
  } catch (error) {
    console.error(`Error: ${error.message}`);
    console.error('Run with --help for usage.');
    process.exitCode = 1;
  } finally {
    if (interactive) {
      const terminal = readline.createInterface({ input, output });
      await terminal.question('Press Enter to close...');
      terminal.close();
    }
  }
}

const isDirectRun = process.argv[1] && fileURLToPath(import.meta.url) === path.resolve(process.argv[1]);

if (isDirectRun) {
  await main();
}

export { generateFolders, normalizeDroppedPath, parseArgs, shuffleFiles };
